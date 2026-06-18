# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidAdvanceInvoice(models.TransientModel):
	_name = 'od.contract.invoice.wiz'
	_description = "Create Advance Invoice From Contract"

	@api.model
	def default_get(self, fields):
		result = super(OrchidAdvanceInvoice, self).default_get(fields)
		if not result.get('contract_id') and self.env.context.get('active_id'):
			result['contract_id'] = self.env.context.get('active_id')
		return result

	contract_id = fields.Many2one('od.asp.contract', string="Contract")
	date = fields.Date(string="Due Date")
	invoice_line = fields.One2many('od.contract.invoice.wiz.line','wiz_id', string="Lines")
	invoice_date = fields.Date(string="Invoice Date")

	@api.onchange('date')
	def onchange_date(self):
		if self.date:
			self.invoice_date = self.date

	def search_lines(self):
		if self.contract_id and self.date:
			if self.invoice_line:
				self.invoice_line.unlink()
			wiz_lines=[]
			for line in self.contract_id.contract_line_ids.filtered(lambda r: r.next_invoice_date <=self.date):
				tax_ls=[t.id for t in line.tax_id]
				if line.state=='0_draft' and not line.effective_date:
					
					#special case ---invoice before activation
					if (line.frequency==1 and not line.invoice_line_ids) or line.frequency!=1:
						vals = {
								'wiz_id':self.id,
								'contract_line_id':line.id,
								'invoice_date':line.next_invoice_date,
								'amount_to_invoice':0,
								'amount':line.price_total,
								'per_month':line.price_unit*line.product_uom_qty,
								'tax_id':[(6,0,tax_ls)],
								}
						self.env['od.contract.invoice.wiz.line'].create(vals)
			if not self.invoice_line:
				raise UserError(_("No Invoiceable Lines !!!"))
			return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.contract.invoice.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }

	
	def create_invoice(self):
		user_id=self.contract_id.sam_id.id if self.contract_id.sam_id else self.env.user.id
		journal_id_rec = self.env['account.move'].with_context(default_move_type='out_invoice').new({'move_type': 'out_invoice'})
		invoice_vals={
		'od_contract_id': self.contract_id.id,
		'partner_id': self.contract_id.partner_id.id,
		'journal_id': journal_id_rec._search_default_journal().id,
		'invoice_payment_term_id': self.contract_id.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
		'invoice_origin': self.contract_id.name,
		'invoice_user_id': self.contract_id.partner_id.user_id and self.contract_id.partner_id.user_id.id or user_id,
		'move_type':'out_invoice',
		'invoice_date':self.invoice_date,
		'currency_id':self.contract_id.currency_id.id,
		'invoice_payment_term_id':self.contract_id.payment_term_id and self.contract_id.payment_term_id.id,
		'od_exchange_rate':self.contract_id.od_exchange_rate,
		'date':self.invoice_date,
		# 'partner_bank_id':3, code from odoo 14
		'partner_bank_id':self.contract_id.partner_id.bank_ids and self.contract_id.partner_id.bank_ids[0].id or False,
		'ref':self.contract_id.client_order_ref,
		'payment_reference':self.contract_id.client_order_ref,
		'od_contact_id':self.contract_id.contact_id and self.contract_id.contact_id.id,
		}
		invoice_id = self.env['account.move'].create(invoice_vals)
		invoice_id.od_onchange_exchange_rate()
		invoice_lines=[]
		pdt_lines=[]
		for line in self.invoice_line:
			tax_ls=[t.id for t in line.tax_id]
			no_freq_months=1
			vals={
			'product_id':line.contract_line_id.product_id.id,
			'quantity':1,
			'move_id':invoice_id.id,
			# 'display_type':False,
			'name':line.name,
			'price_unit':(line.amount_to_invoice),
			'od_contract_line_id':[(6,0,[line.contract_line_id.id])],
			'tax_ids':[(6,0,tax_ls)],
			'name':line.contract_line_id.name,
			'analytic_distribution': {
						str(self.contract_id.analytic_account_id.id): 100
					} if self.contract_id.analytic_account_id else {},
			'od_frequency':line.contract_line_id.frequency,
			}
			if vals['price_unit']==0:
				raise UserError(_("The Price Unit should be non-zero!! Refer the line for contract '%s' ")%(self.contract_id.name))
			w_line=(0,0,vals)
			invoice_lines.append(w_line)
		invoice_id.invoice_line_ids = invoice_lines
		invoice_id.action_post()
		for line in self.invoice_line:
			inv_line_id = invoice_id.invoice_line_ids.search([('od_contract_line_id','=',line.contract_line_id.id)])
			c_line_inv_ids=[ivl.id for ivl in line.contract_line_id.invoice_line_ids]
			c_line_inv_ids.append(inv_line_id.id)
			c_line_inv_ids = list(set(c_line_inv_ids))
			line.contract_line_id.invoice_line_ids = [(6,0,c_line_inv_ids)]#linking invoice line to contract line
			
		return self.contract_id.action_view_invoice()

class OrchidAdvanceInvoiceLine(models.TransientModel):
	_name = 'od.contract.invoice.wiz.line'
	_description = "Invoice Wiz Lines"

	wiz_id=fields.Many2one('od.contract.invoice.wiz', string="Wizard", ondelete='cascade')
	contract_line_id = fields.Many2one('od.asp.contract.line', string="Service Line")
	invoice_date = fields.Date(string="Due Date")
	amount_to_invoice = fields.Float(digits='Product Price', string="Invoice Amount")
	per_month = fields.Float(digits='Product Price', string="Per Month Amount")
	amount = fields.Float(digits='Product Price', string="Total Amount")
	name=fields.Char(string="Description")
	tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])

