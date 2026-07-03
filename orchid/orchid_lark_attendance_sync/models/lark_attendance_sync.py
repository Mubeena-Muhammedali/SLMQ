# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from collections import defaultdict

import requests

from odoo import fields, models, _
from odoo.exceptions import UserError

TOKEN_ENDPOINT = '/open-apis/auth/v3/tenant_access_token/internal'
USER_FLOW_ENDPOINT = '/open-apis/attendance/v1/user_flows/query'
BATCH_SIZE = 50  # Lark API accepts a limited number of user_ids per call
TIMEOUT = 20


class OdLarkAttendanceSync(models.AbstractModel):
    _name = 'od.lark.attendance.sync'
    _description = 'Lark Attendance Sync Engine'

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _get_config(self):
        icp = self.env['ir.config_parameter'].sudo()
        domain = icp.get_param('lark_attendance_sync.domain') or 'https://open.larksuite.com'
        app_id = icp.get_param('lark_attendance_sync.app_id')
        app_secret = icp.get_param('lark_attendance_sync.app_secret')
        days_back = int(icp.get_param('lark_attendance_sync.days_back') or 1)
        if not app_id or not app_secret:
            raise UserError(_(
                'Lark App ID / App Secret are not configured. '
                'Go to Settings > General Settings > Lark Attendance Sync.'
            ))
        return domain, app_id, app_secret, days_back

    def _get_access_token(self, domain, app_id, app_secret):
        try:
            resp = requests.post(
                domain + TOKEN_ENDPOINT,
                json={'app_id': app_id, 'app_secret': app_secret},
                timeout=TIMEOUT,
            )
            data = resp.json()
        except requests.RequestException as exc:
            raise UserError(_('Could not reach Lark API: %s') % exc)

        if data.get('code') != 0:
            raise UserError(_('Lark authentication failed: %s') % data.get('msg'))
        return data.get('tenant_access_token')

    # ------------------------------------------------------------------
    # API call
    # ------------------------------------------------------------------
    def _fetch_user_flow(self, domain, token, user_ids, ts_from, ts_to):
        """Fetch attendance punch records from Lark"""

        headers = {
            "Authorization": "Bearer %s" % token,
            "Content-Type": "application/json",
        }

        params = {
            "employee_type": "employee_id",
        }

        body = {
            "user_ids": user_ids,
            "check_time_from": str(ts_from),
            "check_time_to": str(ts_to),
        }

        try:
            response = requests.post(
                domain + USER_FLOW_ENDPOINT,
                headers=headers,
                params=params,
                json=body,
                timeout=TIMEOUT,
            )

        except requests.RequestException as exc:
            raise UserError(_("Unable to connect to Lark.\n%s") % exc)

        try:
            data = response.json()
        except Exception:
            raise UserError(_("Invalid JSON returned by Lark.\n%s") % response.text)

        if data.get("code") != 0:
            raise UserError(
                _(
                    "Lark API Error\n\n"
                    "Code : %s\n"
                    "Message : %s\n"
                    "Response : %s"
                )
                % (
                    data.get("code"),
                    data.get("msg"),
                    data,
                )
            )

        return data.get("data", {}).get("user_flow_results", [])

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def sync_attendance(self, employees=None):
        """Pull punch records from Lark and create/update hr.attendance.
        If `employees` is not given, every hr.employee with a od_lark_user_id
        set is synced."""
        Employee = self.env['hr.employee'].sudo()
        Attendance = self.env['hr.attendance'].sudo()
        SyncLog = self.env['od.lark.sync.log'].sudo()

        created = updated = 0
        try:
            domain, app_id, app_secret, days_back = self._get_config()

            if employees is None:
                employees = Employee.search([('od_lark_user_id', '!=', False)])
            else:
                employees = employees.filtered('od_lark_user_id')

            if not employees:
                SyncLog.create({
                    'state': 'success',
                    'employees_processed': 0,
                    'message': _('No employees with a Lark User ID were found. Nothing to sync.'),
                })
                return

            token = self._get_access_token(domain, app_id, app_secret)

            now = fields.Datetime.now()
            ts_to = int(now.timestamp())
            ts_from = int((now - timedelta(days=days_back)).timestamp())

            lark_to_employee = {emp.od_lark_user_id: emp for emp in employees}
            all_ids = list(lark_to_employee.keys())

            # Bucket punches by (employee, date) -> sorted list of datetimes
            punches = defaultdict(list)

            for i in range(0, len(all_ids), BATCH_SIZE):
                chunk = all_ids[i:i + BATCH_SIZE]
                records = self._fetch_user_flow(domain, token, chunk, ts_from, ts_to)
                for rec in records:
                    od_lark_user_id = rec.get('user_id')
                    check_time = rec.get('check_time')
                    employee = lark_to_employee.get(od_lark_user_id)
                    if not employee or not check_time:
                        continue
                    check_dt = self._epoch_to_datetime(check_time)
                    punches[(employee.id, check_dt.date())].append(check_dt)

            for (employee_id, day), times in punches.items():
                times.sort()
                check_in = times[0]
                check_out = times[-1] if len(times) > 1 else False

                existing = Attendance.search([
                    ('employee_id', '=', employee_id),
                    ('check_in', '>=', '%s 00:00:00' % day),
                    ('check_in', '<=', '%s 23:59:59' % day),
                ], limit=1)

                if existing:
                    vals = {}
                    if check_out and (not existing.check_out or check_out > existing.check_out):
                        vals['check_out'] = check_out
                    if check_in < existing.check_in:
                        vals['check_in'] = check_in
                    if vals:
                        existing.write(vals)
                        updated += 1
                else:
                    Attendance.create({
                        'employee_id': employee_id,
                        'check_in': check_in,
                        'check_out': check_out,
                    })
                    created += 1

            SyncLog.create({
                'state': 'success',
                'employees_processed': len(employees),
                'attendances_created': created,
                'attendances_updated': updated,
                'message': _('Sync completed successfully.'),
            })

        except UserError as exc:
            SyncLog.create({
                'state': 'error',
                'attendances_created': created,
                'attendances_updated': updated,
                'message': str(exc),
            })
            raise
        except Exception as exc:
            SyncLog.create({
                'state': 'error',
                'attendances_created': created,
                'attendances_updated': updated,
                'message': str(exc),
            })

    @staticmethod
    def _epoch_to_datetime(epoch_seconds):
        import datetime
        return datetime.datetime.utcfromtimestamp(int(epoch_seconds))

    def od_cron_sync_attendance(self):
        self.sync_attendance()
