from odoo import api, models, fields
from datetime import datetime, time
import pytz


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def cron_send_daily_attendance_report(self):

        company = self.env.company

        recipients = [
            'samer.el.ismail@somfy.com',
            'sathyajith.menon@somfy.com',
            'venil.kiran.vaz@somfy.com'
        ]

        recipient = ",".join(recipients)

        if not recipient:
            return

        today = fields.Date.context_today(self)

        # --------------------------------------------------
        # Company/User Timezone
        # --------------------------------------------------
        tz_name = self.env.user.tz or "Asia/Dubai"
        tz = pytz.timezone(tz_name)

        # Beginning and end of local day
        start_local = tz.localize(datetime.combine(today, time.min))
        end_local = tz.localize(datetime.combine(today, time.max))

        # Convert to UTC for database search
        start_dt = start_local.astimezone(pytz.UTC).replace(tzinfo=None)
        end_dt = end_local.astimezone(pytz.UTC).replace(tzinfo=None)


        weekday = str(today.weekday())

        employees = self.search([
            ('active', '=', True),
            ('company_id', '=', company.id),
        ])

        proper_records = []
        missing_records = []
        no_attendance_records = []

        for employee in employees:

            contract = employee.contract_id
            if not contract:
                continue

            calendar = contract.resource_calendar_id
            if not calendar:
                continue

            # -------------------------
            # Weekend
            # -------------------------
            working_days = set(calendar.attendance_ids.mapped('dayofweek'))

            if weekday not in working_days:
                continue

            # -------------------------
            # Public Holiday
            # -------------------------
            public_holiday = calendar.global_leave_ids.filtered(
                lambda l:
                    l.date_from
                    and l.date_to
                    and l.date_from.date() <= today <= l.date_to.date()
            )

            if public_holiday:
                continue

            # -------------------------
            # Attendance
            # -------------------------
            attendance = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_dt),
                ('check_in', '<=', end_dt),
            ], limit=1)

            vals = {
                'emp_code': employee.x_studio_ihris or '',
                'emp_name': employee.name or '',
                'check_in': '',
                'check_out': '',
            }

            if not attendance:

                vals.update({
                    'check_in': 'No Record',
                    'check_out': 'No Record',
                })

                no_attendance_records.append(vals)
                continue

            # --------------------------------------------
            # Convert UTC -> Local Time
            # --------------------------------------------
            check_in = attendance.check_in
            check_out = attendance.check_out

            if check_in:
                check_in = pytz.UTC.localize(check_in).astimezone(tz)

            if check_out:
                check_out = pytz.UTC.localize(check_out).astimezone(tz)

            vals.update({
                'check_in': check_in.strftime('%Y-%m-%d %H:%M:%S') if check_in else 'No Record',
                'check_out': check_out.strftime('%Y-%m-%d %H:%M:%S') if check_out else 'No Record',
            })

            if attendance.check_in and attendance.check_out:
                proper_records.append(vals)
            else:
                missing_records.append(vals)

        # ---------------------------------
        # SKIP EMAIL IF NO RECORDS
        # ---------------------------------

        if (
            not proper_records
            and not missing_records
            and not no_attendance_records
        ):
            return

        html = self._prepare_daily_attendance_email(
            today,
            proper_records,
            missing_records,
            no_attendance_records,
        )

        mail_values = {
            'subject': f'Daily Attendance Report - {today}',
            'body_html': html,
            'email_to': recipient,
        }

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

    def _prepare_daily_attendance_email(
        self,
        today,
        proper_records,
        missing_records,
        no_attendance_records,
    ):

        html = f"""
        <h2>Daily Attendance Report</h2>

        <p>
            <strong>Date:</strong> {today}
        </p>
        """

        # ---------------------------------
        # PROPER
        # ---------------------------------

        html += """
        <h3>Employees With Proper Login/Logout</h3>

        <table border="1" cellpadding="5" cellspacing="0"
               style="border-collapse: collapse; width:100%;">

            <tr style="background-color:#D3D3D3;">
                <th>Employee Code</th>
                <th>Employee Name</th>
                <th>Login Time</th>
                <th>Logout Time</th>
            </tr>
        """

        for line in proper_records:
            html += f"""
            <tr>
                <td>{line['emp_code']}</td>
                <td>{line['emp_name']}</td>
                <td>{line['check_in']}</td>
                <td>{line['check_out']}</td>
            </tr>
            """

        html += "</table><br/><br/>"

        # ---------------------------------
        # MISSING
        # ---------------------------------

        html += """
        <h3>Employees With Missing Login/Logout</h3>

        <table border="1" cellpadding="5" cellspacing="0"
               style="border-collapse: collapse; width:100%;">

            <tr style="background-color:#FFB6B6;">
                <th>Employee Code</th>
                <th>Employee Name</th>
                <th>Login Time</th>
                <th>Logout Time</th>
            </tr>
        """

        for line in missing_records:

            login_style = ''
            logout_style = ''

            if line['check_in'] == 'No Record':
                login_style = 'color:red;font-weight:bold;'

            if line['check_out'] == 'No Record':
                logout_style = 'color:red;font-weight:bold;'

            html += f"""
            <tr>
                <td>{line['emp_code']}</td>
                <td>{line['emp_name']}</td>
                <td style="{login_style}">
                    {line['check_in']}
                </td>
                <td style="{logout_style}">
                    {line['check_out']}
                </td>
            </tr>
            """

        html += "</table><br/><br/>"

        # ---------------------------------
        # NO ATTENDANCE
        # ---------------------------------

        html += """
        <h3>Employees Without Attendance</h3>

        <table border="1" cellpadding="5" cellspacing="0"
               style="border-collapse: collapse; width:100%;">

            <tr style="background-color:#FF7F7F;">
                <th>Employee Code</th>
                <th>Employee Name</th>
                <th>Status</th>
            </tr>
        """

        for line in no_attendance_records:
            html += f"""
            <tr>
                <td>{line['emp_code']}</td>
                <td>{line['emp_name']}</td>
                <td style="color:red;font-weight:bold;">
                    No Attendance
                </td>
            </tr>
            """

        html += "</table>"

        return html