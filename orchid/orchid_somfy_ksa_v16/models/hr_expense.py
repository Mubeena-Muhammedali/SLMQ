# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, Command, models, _
import secrets
import base64
from odoo.exceptions import UserError, ValidationError


class ResCompany(models.Model):
	_inherit = "res.company"

	od_expense_account_id = fields.Many2one(
		"account.account",
		string="Default Expense Income Account",
		check_company=True,
		help="The company's default income account used when an employee expense is posted.",
	)
	

class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'

	od_expense_account_id = fields.Many2one('account.account', related='company_id.od_expense_account_id', readonly=False)



class HrExpense(models.Model):
	_inherit = 'hr.expense'

	od_name = fields.Char(string="Name", default="NEW")
	od_tax_apply = fields.Boolean(string="Apply Tax", default=True)
	payment_mode = fields.Selection([
		("own_account", "Employee (to reimburse)"),
		("company_account", "Company")
	], default='company_account', tracking=True, states={'done': [('readonly', True)], 'approved': [('readonly', True)], 'reported': [('readonly', True)]}, string="Paid By")

	payment_state = fields.Selection(
		lambda self: self.env["account.move"]._fields["payment_state"]._description_selection(self.env),
		string="Payment Status",
		store=True, readonly=True, copy=False, tracking=True)

	@api.onchange('od_tax_apply','product_id')
	def od_tax_change(self):
		for expense in self:
			if expense.od_tax_apply and expense.product_id:
				expense._compute_tax_ids()
			else:
				expense.tax_ids = False


	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			vals['od_name'] = self.env['ir.sequence'].next_by_code('od.hr.expense')
			vals['payment_mode'] = 'company_account'
		expenses = super(HrExpense, self).create(vals_list)
		return expenses

class HrExpenseSheet(models.Model):
	_inherit = 'hr.expense.sheet'

	od_external_approval_token = fields.Char(copy=False)
	od_external_approval_done = fields.Boolean(default=False)

	@api.depends_context('uid')
	@api.depends('employee_id')
	def _compute_can_approve(self):
		#ovveride so that the user cannot approve their own expense regardless of the group they belong
		is_approver = self.user_has_groups(
			'hr_expense.group_hr_expense_team_approver,hr_expense.group_hr_expense_user'
		)
		is_manager = self.user_has_groups(
			'hr_expense.group_hr_expense_manager'
		)

		for sheet in self:
			sheet.can_approve = (
				sheet.employee_id.user_id != self.env.user
				and (is_manager or is_approver)
			)

	def _prepare_bills_vals(self):
		self.ensure_one()

		return {
			**self._prepare_move_vals(),
			'journal_id': self.journal_id.id,
			'ref': self.name,
			'move_type': 'in_invoice',
			'partner_id': self.employee_id.sudo().work_contact_id.id,
			'currency_id': self.currency_id.id,
			'line_ids': [Command.create(expense._prepare_move_lines_vals()) for expense in self.expense_line_ids],
			'attachment_ids': [
				Command.create(attachment.sudo().copy_data({'res_model': 'account.move', 'res_id': False, 'raw': attachment.sudo().raw})[0])
				for attachment in self.expense_line_ids.message_main_attachment_id
			],
		}

	def action_submit_sheet(self):
		res = super().action_submit_sheet()

		for sheet in self:
			if sheet.employee_id.x_studio_external_approver:
				sheet.od_external_approval_token = secrets.token_urlsafe(32)
				sheet.od_external_approval_done = False
				sheet.od_send_external_expense_email()

		return res



	def od_send_external_expense_email(self):
		self.ensure_one()

		base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

		approve_url = f"{base_url}/external/expense/approve?token={self.od_external_approval_token}"
		refuse_url = f"{base_url}/external/expense/refuse?token={self.od_external_approval_token}"
		reset_url = f"{base_url}/external/expense/reset?token={self.od_external_approval_token}"

		manager_email = self.employee_id.x_studio_external_approver.login
		if not manager_email:
			return

		# ✅ Generate Expense Sheet PDF
		pdf_content, content_type = self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf('orchid_somfy_ksa_v16.action_report_report_od_hr_expense', res_ids=self.id)

		attachment = self.env['ir.attachment'].sudo().create({
			'name': f'Expense_{self.name}.pdf',
			'type': 'binary',
			'datas': base64.b64encode(pdf_content),
			'res_model': 'hr.expense.sheet',
			'res_id': self.id,
			'mimetype': 'application/pdf',
		})

		# ✅ Email Body
		html_body = f"""
			<p>Dear {self.employee_id.x_studio_external_approver.name},</p>

			<p>{self.employee_id.name} has submitted an expense report requiring your approval.</p>

			<p><strong>Total Amount:</strong> {self.total_amount}</p>

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
			'subject': f"Expense Approval Request - {self.employee_id.name}",
			'body_html': html_body,
			'email_to': manager_email,
			'email_from': self.env.user.email or '',
			'attachment_ids': [(4, attachment.id)],
		}
		# &nbsp;

		#   <a href="{reset_url}" 
		#      style="padding:10px 15px; background-color:gray; color:white; text-decoration:none;">
		#      Mark as Draft
		#   </a>

		self.env['mail.mail'].sudo().create(mail_values).send()

	def reset_expense_sheets(self):
		res = super(HrExpenseSheet, self).reset_expense_sheets()
		self.od_external_approval_done =False
		return res
