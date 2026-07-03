from odoo import http
from odoo.http import request

class ExternalExpenseApproval(http.Controller):

    @http.route('/external/expense/<string:action>', type='http', auth='public', website=True)
    def external_expense_action(self, action=None, token=None, **kwargs):

        sheet = request.env['hr.expense.sheet'].sudo().search([
            ('od_external_approval_token', '=', token),
            ('od_external_approval_done', '=', False),
            ('state', '=', 'submit')
        ], limit=1)

        if not sheet:
            return "This approval link is invalid or already used."

        if action == 'approve':
            sheet.approve_expense_sheets()
        elif action == 'refuse':
            sheet.refuse_sheet("Manager Refused")
        elif action == 'reset':
            sheet.reset_expense_sheets()

        sheet.od_external_approval_done = True

        return "Action completed successfully."
