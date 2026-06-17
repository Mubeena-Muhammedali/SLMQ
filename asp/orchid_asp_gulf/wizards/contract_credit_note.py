# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidContractCreditNote(models.TransientModel):
	_name = 'od.contract.credit.note.wiz.all'
	_description = "Create Credit Note"

	date = fields.Date(string="Credit Note Date", default=fields.Date.context_today)
	invoice_date = fields.Date(string="Invoice Date")
	partner_id = fields.Many2one('res.partner', string="Customer")
	contract_id = fields.Many2one('od.asp.contract', string="Contract")
	contract_name = fields.Char(related='contract_id.contract_code', string="Contract Name")
	invoice_line = fields.One2many('od.contract.credit.note.wiz.line.all','wiz_id', string="Lines")

	def search_lines(self):
		if self.invoice_line:
			self.invoice_line.unlink()
		wiz_lines=[]
		invoices = self.contract_id.invoice_ids
		if self.invoice_date:
			invoices = self.contract_id.invoice_ids.filtered(lambda x:x.date_invoice <= self.invoice_date)

		for inv in invoices:
			wiz_line_vals = {
			'wiz_id':self.id,
			'invoice_id':inv.id,
			'currency_id':inv.currency_id.id,
			'amount':inv.amount_total,
			'refund_amount':inv.amount_total,
			}
			wiz_lines.append((0,0,wiz_line_vals))
		self.invoice_line = wiz_lines

		if not self.invoice_line:
				raise UserError(_("No Invoices !!!"))
		return {
		'view_type': 'form',
		"view_mode": 'form',
		'res_model': 'od.contract.credit.note.wiz.all',
		'res_id': self.id,
		'type': 'ir.actions.act_window',
		'target': 'new'
		}


	@api.onchange('partner_id')
	def onchange_refund_amt(self):
		for wiz in self:
			wiz.contract_id = False





class OrchidContractCreditNoteLine(models.TransientModel):
	_name = 'od.contract.credit.note.wiz.line.all'
	_description = "Multiple Contracts Credit Note Wiz Lines"
	_order = 'invoice_date'

	wiz_id=fields.Many2one('od.contract.credit.note.wiz.all', string="Wizard", ondelete='cascade')
	invoice_id = fields.Many2one('account.move', string="Contract")
	invoice_date = fields.Date(related='invoice_id.invoice_date', string="Invoice Date")
	currency_id = fields.Many2one('res.currency', string="Currency")
	amount = fields.Float(string="Total Invoiced Amount")
	refund_method = fields.Selection(selection=[
			('refund', 'Partial Refund'),
			('cancel', 'Full Refund'),
			('modify', 'Full refund and new draft invoice')
		], string='Credit Method',default='cancel',
		help='Choose how you want to credit this invoice. You cannot "modify" nor "cancel" if the invoice is already reconciled.')
	refund_amount = fields.Float(string="Refund Amount")

	@api.onchange('refund_method')
	def onchange_refund_amt(self):
		for line in self:
			if line.refund_method == 'cancel':
				line.refund_amount = line.amount


