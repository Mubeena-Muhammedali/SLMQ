# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def get_kiosk_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = self.env.ref('hr_attendance.hr_attendance_action_my_attendances')
        menu = self.env.ref('hr_attendance.menu_hr_attendance_my_attendances')

        return f"{base_url}/web#action={action.id}&menu_id={menu.id}"

    def od_login_reminder_email(self):
        schedule_action_id = self.env.ref('orchid_somfy_ksa_v16.od_attendance_login_reminder')
        today_date = schedule_action_id.nextcall
        if datetime.strptime(str(today_date), '%Y-%m-%d %H:%M:%S').strftime('%A') not in ('Friday,Saturday'):
            self.od_attendance_mail('login')

    def od_logout_reminder_email(self):
        schedule_action_id = self.env.ref('orchid_somfy_ksa_v16.od_attendance_logout_reminder')
        today_date = schedule_action_id.nextcall
        if datetime.strptime(str(today_date), '%Y-%m-%d %H:%M:%S').strftime('%A') not in ('Friday,Saturday'):
            self.od_attendance_mail('logout')

    def od_attendance_mail(self, status):
        # reporting_office = self.env['od.reporting.office'].search([('enable_attendance_email', '=', True)])
        # if reporting_office:
        # employees = self.env['hr.employee'].search([('company_id', '=', 2),('active','=',True), ('employee_type','=','employee')])
        employees = self.env['hr.employee'].search([('active','=',True), ('employee_type','=','employee')])
        if employees:
            generate = self.env.ref('orchid_somfy_ksa_v16.od_attendance_mail_template')
            ctx = self.env.context.copy()
            recipients = []
            for emp in employees:
                recipients.append(emp.work_email)
            recipients = list(filter(None, recipients))
            recipient_name = ""
            mail_content = ""
            button_name = ""
            if status == 'login':
                recipient_name = "Good Morning,"
                button_name = "Login"
                mail_content = "Please click on the following link to mark your attendance."
            if status == 'logout':
                recipient_name = "Good Evening,"
                button_name = "Logout"
                mail_content = "Please click on the following link to logout."


            ctx['email_to'] = ','.join(recipients)
            ctx['email_cc'] = ''
            ctx['content'] = mail_content
            ctx['recipient_name'] = recipient_name
            ctx['button_name'] = button_name
            ctx['url'] = self.get_kiosk_url()
            generate.sudo().with_context(ctx).send_mail(self.id, force_send=True)
