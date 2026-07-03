# -*- coding: utf-8 -*-

from odoo import api, fields, Command, models, tools,_
import secrets


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    od_external_approval_token = fields.Char(copy=False)
    od_external_approval_done = fields.Boolean(default=False)

    @api.model_create_multi
    def create(self, vals_list):
        results = super(HrLeave, self).create(vals_list)
        for res in results:
            res.od_external_email()
        return results

    def od_external_email(self):
        for leave in self:
            if leave.employee_id.x_studio_external_approver:
                leave.od_external_approval_token = secrets.token_urlsafe(32)
                leave.od_send_external_approval_email()


    def action_confirm(self):
        res = super().action_confirm()

        for leave in self:
            if leave.employee_id.x_studio_external_approver:
                leave.od_external_approval_token = secrets.token_urlsafe(32)
                leave.od_external_approval_done = False
                leave.od_send_external_approval_email()


    def od_send_external_approval_email(self):
        self.ensure_one()

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        approve_url = f"{base_url}/external/leave/approve?token={self.od_external_approval_token}"
        refuse_url = f"{base_url}/external/leave/refuse?token={self.od_external_approval_token}"
        reset_url = f"{base_url}/external/leave/reset?token={self.od_external_approval_token}"

        manager_email = self.employee_id.x_studio_external_approver.login

        if not manager_email:
            return

        duration = self.number_of_days
        start_date = self.request_date_from
        end_date = self.request_date_to
        reason = self.name or ''

        html_body = f"""
            <p>Dear {self.employee_id.x_studio_external_approver.name},</p>

            <p>{self.employee_id.name} has submitted a leave request requiring your approval.</p>

            <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
                <tr>
                    <td><strong>Employee</strong></td>
                    <td>{self.employee_id.name}</td>
                </tr>
                <tr>
                    <td><strong>Leave Type</strong></td>
                    <td>{self.holiday_status_id.name}</td>
                </tr>
                <tr>
                    <td><strong>Duration</strong></td>
                    <td>{duration} days</td>
                </tr>
                <tr>
                    <td><strong>Start Date</strong></td>
                    <td>{start_date}</td>
                </tr>
                <tr>
                    <td><strong>End Date</strong></td>
                    <td>{end_date}</td>
                </tr>
                <tr>
                    <td><strong>Reason</strong></td>
                    <td>{reason}</td>
                </tr>
            </table>

            <br/>

            <a href="{approve_url}" 
               style="padding:10px 15px; background-color:green; color:white; text-decoration:none;">
               Approve
            </a>

            &nbsp;

            <a href="{refuse_url}" 
               style="padding:10px 15px; background-color:red; color:white; text-decoration:none;">
               Refuse
            </a>

            <br/><br/>
            <p>This link can only be used once.</p>
        """

        mail_values = {
            'subject': f"Leave Approval Request - {self.employee_id.name}",
            'body_html': html_body,
            'email_to': manager_email,
            'email_from': self.env.user.email or '',
        }
        # &nbsp;

        #     <a href="{reset_url}" 
        #        style="padding:10px 15px; background-color:gray; color:white; text-decoration:none;">
        #        Mark as Draft
        #     </a>

        self.env['mail.mail'].sudo().create(mail_values).send()
