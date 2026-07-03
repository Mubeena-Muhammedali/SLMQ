from odoo import http
from odoo.http import request

class ExternalLeaveApproval(http.Controller):

    @http.route('/external/leave/<string:action>', type='http', auth='public', website=True)
    def external_leave_action(self, action=None, token=None, **kwargs):

        leave = request.env['hr.leave'].sudo().search([
            ('od_external_approval_token', '=', token),
            ('od_external_approval_done', '=', False)
        ], limit=1)

        if not leave:
            return "This approval link is invalid or already used."

        if action == 'approve':
            leave.action_approve()
        elif action == 'refuse':
            leave.action_refuse()
        elif action == 'reset':
            leave.action_draft()

        leave.od_external_approval_done = True

        return "Action completed successfully."
