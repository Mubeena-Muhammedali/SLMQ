# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
	_inherit = "account.payment"
	od_check_date = fields.Date(string="Check Date",default=fields.Date.context_today)
	od_check_to = fields.Char(string="Cheque To")
	od_acc_payee= fields.Boolean(string='A/c Payee', default=True)

class AccountMove(models.Model):
	_inherit = "account.move"

	state = fields.Selection(selection=[
			('draft', 'Draft'),
			('submit','Submitted'),
			('posted', 'Posted'),
			('cancel', 'Cancelled'),
		], string='Status', required=True, readonly=True, copy=False, tracking=True,
		default='draft')
	od_reveiew = fields.Boolean(string="Reveiew by Manager", default=False)
	od_check_date = fields.Date(string="Check Date",default=fields.Date.context_today)
	od_check_to = fields.Char(string="Cheque To")
	od_acc_payee= fields.Boolean(string='A/c Payee', default=True)

	def od_button_submit(self):
		self.state = 'submit'

	def action_post(self):
		if self.state == 'draft' and self.od_is_bank_voucher and self.od_reveiew:
			raise UserError(_("Please Submit the record!!!"))
		if self.od_is_bank_voucher and self.env.user.id == self.create_uid.id and self.od_reveiew:
			raise UserError(_("You are not allowed to post this record!!!"))
		return super(AccountMove, self).action_post()
