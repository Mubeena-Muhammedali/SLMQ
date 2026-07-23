# -*- coding: utf-8 -*-
import base64
import io
from datetime import datetime, date, timedelta
import pytz

from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    import openpyxl
except ImportError:
    openpyxl = None


MONTH_FORMATS = ('%Y-%m', '%Y/%m', '%B-%Y', '%B %Y', '%b-%Y', '%b %Y', '%B %Y')


class OdAttendanceTimeoffImportWizard(models.TransientModel):
    _name = 'od.hr.attendance.timeoff.import.wizard'
    _description = 'Import Attendance / Time Off from Timesheet'

    import_file = fields.Binary(string='Timesheet File')
    import_filename = fields.Char(string='File Name')
    error_log = fields.Text(string='Errors', readonly=True)

    # ------------------------------------------------------------------
    # Template download
    # ------------------------------------------------------------------
    def action_download_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/hr_attendance_timeoff_import/template',
            'target': 'self',
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _parse_month(self, value):
        """Accepts a date/datetime cell, or text like '2025-09', 'September 2025'."""
        if isinstance(value, (datetime, date)):
            return value.year, value.month
        if value in (None, ''):
            raise UserError(_('The Month cell (D1) is empty.'))
        text = str(value).strip()
        cleaned = ' '.join(text.replace('_', ' ').replace('-', ' ').split())
        for fmt in MONTH_FORMATS:
            try:
                dt = datetime.strptime(text, fmt)
                return dt.year, dt.month
            except ValueError:
                pass
            try:
                dt = datetime.strptime(cleaned, fmt.replace('-', ' '))
                return dt.year, dt.month
            except ValueError:
                pass
        raise UserError(_('Could not understand the Month value "%s". '
                           'Use a format like "2025-09" or "September 2025".') % value)

    @staticmethod
    def _cell(values, index):
        if index is None or index >= len(values):
            return None
        return values[index]

    def _local_to_utc(self, dt, employee):
        """Convert employee local datetime to naive UTC datetime."""

        tz_name = (
            employee.resource_calendar_id.tz
            or employee.user_id.tz
            or self.env.user.tz
            or 'UTC'
        )

        tz = pytz.timezone(tz_name)

        if dt.tzinfo:
            local_dt = dt.astimezone(tz)
        else:
            local_dt = tz.localize(dt)

        utc_dt = local_dt.astimezone(pytz.UTC)

        return utc_dt.replace(tzinfo=None)

    # ------------------------------------------------------------------
    # Main import
    # ------------------------------------------------------------------
    def action_import(self):
        self.ensure_one()

        if not self.import_file:
            raise UserError(_('Please select a file to upload first.'))
        if not openpyxl:
            raise UserError(_('The "openpyxl" Python library is not installed on the server. '
                               'Ask your administrator to run: pip install openpyxl'))

        try:
            content = base64.b64decode(self.import_file)
            workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        except Exception as exc:
            raise UserError(_('Could not read the uploaded file. Make sure it is a valid '
                               '.xlsx file. Technical error: %s') % exc)

        sheet = workbook.active

        # --- Row 1: Employee Name | <name> | Month | <YYYY-MM> ---
        header_row = [c.value for c in next(sheet.iter_rows(min_row=1, max_row=1))]
        if len(header_row) < 4:
            raise UserError(_('Row 1 must contain 4 cells: '
                               '"Employee Name" | <name> | "Month" | <YYYY-MM>.'))
        employee_name = header_row[1]
        month_value = header_row[3]
        if not employee_name:
            raise UserError(_('The Employee Name cell (B1) is empty.'))

        year, month = self._parse_month(month_value)

        employee = self.env['hr.employee'].sudo().search(
            [('name', 'ilike', str(employee_name).strip())])
        if not employee:
            raise UserError(_('No employee found matching "%s".') % employee_name)
        if len(employee) > 1:
            raise UserError(_(
                'Multiple employees match "%s": %s. Please use a more specific name in the file.'
            ) % (employee_name, ', '.join(employee.mapped('name'))))

        calendar = employee.resource_calendar_id
        if not calendar:
            raise UserError(_("Employee %s has no working schedule.") % employee.name)


        # --- Row 2: column headers ---
        header_cells = [c.value for c in next(sheet.iter_rows(min_row=2, max_row=2))]
        headers = [str(v).strip().lower() if v else '' for v in header_cells]

        if 'date' not in headers:
            raise UserError(_('Row 2 must contain a "Date" column header.'))
        date_col = headers.index('date')
        hours_col = headers.index('hours') if 'hours' in headers else None
        timeoff_col = headers.index('time off type') if 'time off type' in headers else None
        if hours_col is None and timeoff_col is None:
            raise UserError(_('Row 2 must contain a "Hours" and/or a "Time Off Type" column header.'))

        errors = []
        attendance_vals = []
        leave_vals = []
        leave_type_cache = {}

        for row in sheet.iter_rows(min_row=3):
            row_num = row[0].row
            values = [c.value for c in row]
            if all(v in (None, '') for v in values):
                continue

            day_value = self._cell(values, date_col)
            if day_value in (None, ''):
                continue

            try:
                if isinstance(day_value, (datetime, date)):
                    work_date = date(year, month, day_value.day)
                else:
                    work_date = date(year, month, int(day_value))
            except Exception:
                errors.append(_('Row %s: invalid Date value "%s".') % (row_num, day_value))
                continue

            weekday = str(work_date.weekday())  # Monday=0 ... Sunday=6

            attendance_lines = calendar.attendance_ids.filtered(
                lambda l: l.dayofweek == weekday
            ).sorted(key=lambda l: l.hour_from)

            hours_value = self._cell(values, hours_col)
            timeoff_value = self._cell(values, timeoff_col)
            has_hours = hours_value not in (None, '')
            has_timeoff = timeoff_value not in (None, '')

            if has_hours and has_timeoff:
                errors.append(_(
                    'Row %s (day %s): both "Hours" and "Time Off Type" are filled in. '
                    'Only one should be set per row - skipped.'
                ) % (row_num, work_date.day))
                continue

            if has_hours:
                try:
                    hours = float(hours_value)
                except Exception:
                    errors.append(_('Row %s (day %s): "%s" is not a valid number of hours.')
                                  % (row_num, work_date.day, hours_value))
                    continue
                if hours <= 0:
                    continue
                # Assume the shift starts at 08:00 local/naive time; only the
                # duration matters for the regular/overtime split.
                if attendance_lines:
                    start_hour = attendance_lines[0].hour_from

                    lunch_line = attendance_lines.filtered(
                        lambda l: l.day_period == 'lunch'
                    )

                    lunch_duration = 0.0
                    if lunch_line:
                        lunch_duration = sum(
                            line.hour_to - line.hour_from
                            for line in lunch_line
                        )
                else:
                    start_hour = 8.0
                    lunch_duration = 0.0

                local_check_in = (
                    datetime.combine(work_date, datetime.min.time())
                    + timedelta(hours=start_hour)
                )

                local_check_out = local_check_in + timedelta(
                    hours=hours + lunch_duration
                )

                check_in = self._local_to_utc(local_check_in, employee)
                check_out = self._local_to_utc(local_check_out, employee)

                attendance_vals.append({
                    'employee_id': employee.id,
                    'check_in': check_in,
                    'check_out': check_out,
                })

            elif has_timeoff:
                type_name = str(timeoff_value).strip()
                key = type_name.lower()
                leave_type = leave_type_cache.get(key)
                if leave_type is None:
                    leave_type = self.env['hr.leave.type'].search(
                        [('name', 'ilike', type_name)], limit=1)
                    if not leave_type:
                        errors.append(_(
                            'Row %s (day %s): no Time Off Type found matching "%s".'
                        ) % (row_num, work_date.day, type_name))
                        continue
                    leave_type_cache[key] = leave_type
                if attendance_lines:
                    start_hour = attendance_lines[0].hour_from
                    end_hour = attendance_lines[-1].hour_to

                    local_date_from = (
                        datetime.combine(work_date, datetime.min.time())
                        + timedelta(hours=start_hour)
                    )

                    local_date_to = (
                        datetime.combine(work_date, datetime.min.time())
                        + timedelta(hours=end_hour)
                    )

                    date_from = self._local_to_utc(local_date_from, employee)
                    date_to = self._local_to_utc(local_date_to, employee)


                    leave_vals.append({
                        'employee_id': employee.id,
                        'holiday_status_id': leave_type.id,
                        'request_date_from': work_date,
                        'request_date_to': work_date,
                        'date_from': date_from,
                        'date_to': date_to,
                    })

        created_attendances = self.env['hr.attendance']
        if attendance_vals:
            try:
                created_attendances = self.env['hr.attendance'].sudo().create(attendance_vals)
            except Exception as exc:
                errors.append(_("Could not create attendance records: %s") % exc)

        created_leaves = self.env['hr.leave']

        for vals in leave_vals:
            try:
                leave = self.env['hr.leave'].sudo().create(vals)
                leave.action_approve()

                created_leaves |= leave

            except Exception as exc:
                errors.append(
                    _("Could not create time off for day %s: %s")
                    % (vals.get('request_date_from'), exc)
                )

        self.write({
            'error_log': '\n'.join(errors) if errors else False,
        })
        if errors:

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'od.hr.attendance.timeoff.import.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
        else:
            return True