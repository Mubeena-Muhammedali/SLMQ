from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError
from datetime import datetime
import calendar


class OdExpenseBatch(models.Model):
	_name = 'od.expense.batch'
	_description = 'OD Expense Batch'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_order = 'date desc'

	name = fields.Char(string="Batch Reference", readonly=True, copy=False, default="New")
	date = fields.Date(required=True, tracking=True)

	state = fields.Selection([
		('draft', 'Draft'),
		('confirm', 'Confirmed'),
		('provision', 'Provision Created'),
		('paid', 'Paid'),
	], default='draft', tracking=True)

	line_ids = fields.One2many(
		'od.expense.batch.line',
		'batch_id',
		string="Expense Sheets"
	)

	provision_move_id = fields.Many2one('account.move', readonly=True)
	payment_move_id = fields.Many2one('account.move', readonly=True)
	company_id = fields.Many2one('res.company', string="Company", default=lambda self:self.env.company)
	posting_date = fields.Date(string="Provision Date", tracking=True)
	payment_date = fields.Date(string="Payment Date", tracking=True)


	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			if vals.get('name', _('New')) == _('New'):

				vals['name'] = self.env['ir.sequence'].next_by_code(
					'od.expense.batch') or _('New')

		return super().create(vals_list)


	def action_search_sheets(self):
		self.ensure_one()

		if self.state != 'draft':
			raise UserError(_("Search allowed only in Draft."))

		if not self.date:
			raise UserError(_("Please select a date."))

		start_date = self.date.replace(day=1)
		last_day = calendar.monthrange(self.date.year, self.date.month)[1]
		end_date = self.date.replace(day=last_day)

		sheet_lines = self.env['hr.expense'].search([
			('sheet_id.state', '=', 'approve'),
			('date', '>=', start_date),
			('date', '<=', end_date),
			('company_id','=',self.company_id.id)
		])

		lines = []
		sheets = sheet_lines.mapped('sheet_id')
		for sheet in sheets:
			lines.append((0, 0, {
				'expense_sheet_id': sheet.id,
			}))

		self.line_ids = [(5, 0, 0)] + lines



	def action_confirm(self):
		self.ensure_one()

		if self.state != 'draft':
			return
		if not self.line_ids:
			raise UserError(_("No expenses to confirm!!"))

		self.state = 'confirm'


	def action_create_provision(self):
		self.ensure_one()

		if self.state != 'confirm':
			raise UserError(_("Batch must be confirmed first."))

		if not self.line_ids:
			raise UserError(_("No expense sheets found."))

		company = self.company_id
		clearing_account = company.od_expense_account_id
		if not clearing_account:
			raise UserError(_("Configure OD Expense Account."))

		journal = company.expense_journal_id
		if not journal:
			raise UserError(_("Configure OD Expense Journal on company."))

		grouped_data = {}

		# Group by employee + expense account
		for line in self.line_ids:
			for expense in line.expense_sheet_id.expense_line_ids:

				account = (
					expense.product_id.property_account_expense_id
					or expense.product_id.categ_id.property_account_expense_categ_id
				)

				key = (expense.employee_id.id, account.id)

				grouped_data.setdefault(key, 0.0)
				grouped_data[key] += expense.total_amount_company

		move_lines = []
		total_credit = 0.0

		for (employee_id, account_id), amount in grouped_data.items():
			emp_id = self.env['hr.employee'].browse(employee_id)
			move_lines.append((0, 0, {
				'name': 'Provision',
				'account_id': account_id,
				'debit': amount,
				'credit': 0.0,
				'partner_id':emp_id.address_home_id.id,
			}))
			total_credit += amount

		# Clearing credit
		move_lines.append((0, 0, {
			'name': 'Expense Provision',
			'account_id': clearing_account.id,
			'debit': 0.0,
			'credit': total_credit,
		}))

		move = self.env['account.move'].create({
			'date': self.posting_date,
			'journal_id': journal.id,
			'ref': self.name,
			'line_ids': move_lines,
		})

		move.action_post()

		self.provision_move_id = move.id
		self.state = 'provision'

	def reset_to_draft(self):
		self.state='draft'

	def unlink(self):
		for rec in self:
			if rec.state != 'draft':
				raise UserError(_("Only Draft records can be deleted!!"))
		return super(OdExpenseBatch, self).unlink()



	def action_create_payment(self):
		self.ensure_one()

		if self.state != 'provision':
			raise UserError(_("Provision must be created first."))

		company = self.company_id
		clearing_account = company.od_expense_account_id
		bank_journal = self.env.company.company_expense_journal_id
		if not bank_journal:
			bank_journal = self.env['account.journal'].search([('type', 'in', ['cash', 'bank']), ('company_id', '=', self.company_id.id)], limit=1)

		if not bank_journal:
			raise UserError(_("Configure OD Bank Journal on company."))

		total_amount = sum(
			self.line_ids.mapped(
				lambda l: sum(l.expense_sheet_id.expense_line_ids.mapped('total_amount_company'))
			)
		)

		bank_account = (
			bank_journal.outbound_payment_method_line_ids[0].payment_account_id
			or bank_journal.company_id.account_journal_payment_credit_account_id
		)

		sheets = self.line_ids.mapped('expense_sheet_id')
		move = self.env['account.move'].create({
			'date': self.payment_date,
			'journal_id': bank_journal.id,
			'ref': self.name,
			# 'expense_sheet_id': [Command.set(sheets.ids)],
			'line_ids': [
				(0, 0, {
					'name': 'Expense Provision',
					'account_id': clearing_account.id,
					'debit': total_amount,
					'credit': 0.0,
				}),
				(0, 0, {
					'name': 'Bank',
					'account_id': bank_account.id,
					'debit': 0.0,
					'credit': total_amount,
				}),
			]
		})

		move.action_post()

		sheets.write({
			'state': 'done',
			'payment_state': 'paid',
			'amount_residual': 0.0,
			})

		self.payment_move_id = move.id
		self.state = 'paid'












class OdExpenseBatchLine(models.Model):
	_name = 'od.expense.batch.line'
	_description = 'OD Expense Batch Line'

	batch_id = fields.Many2one('od.expense.batch', required=True, ondelete='cascade')

	expense_sheet_id = fields.Many2one(
		'hr.expense.sheet',
		required=True
	)

	employee_id = fields.Many2one(
		related='expense_sheet_id.employee_id',
		store=True
	)

	sheet_state = fields.Selection(
		related='expense_sheet_id.state',
		string="Sheet State",
		store=True
	)

	currency_id  = fields.Many2one('res.currency', related="expense_sheet_id.currency_id")
	
	amount = fields.Monetary(string="Amount", currency_field='currency_id', related="expense_sheet_id.total_amount")

	company_id = fields.Many2one('res.company', string="Company", related="batch_id.company_id", store=True)

	def action_view_sheet(self):
		return {
			'type': 'ir.actions.act_window',
			'name': 'Expense Sheet',
			'view_mode': 'form',
			'res_model': 'hr.expense.sheet',
			'res_id': self.expense_sheet_id.id,
		}