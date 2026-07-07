# -*- coding: utf-8 -*-

from odoo import fields,models,api,_
from odoo import tools
from copy import copy
from odoo.exceptions import UserError, ValidationError


# Modifications in account.payment lines
class AccountPayment(models.Model):
	_inherit = "account.payment"

	od_reconciled_line_ids = fields.One2many('od.account.reconciled.line','payment_id', string="Reconciled Lines", copy=False)

	def button_od_open_reconciled_line(self):
		self.ensure_one()
		line_ids = self.env['od.account.reconciled.line'].search([('payment_id','=',self.id)])
		action = {
			'name': _("Reconciled Lines"),
			'type': 'ir.actions.act_window',
			'res_model': 'od.account.reconciled.line',
			'context': {'create': False},
		}
		if len(line_ids) == 1:
			action.update({
				'view_mode': 'form',
				'res_id': line_ids.id,
			})
		else:
			action.update({
				'view_mode': 'list,form',
				'domain': [('id', 'in', line_ids.ids)],
			})
		return action

	def action_draft(self):
		''' posted -> draft '''
		result = super(AccountPayment,self).action_draft()
		if self.od_reconciled_line_ids:
			self.od_reconciled_line_ids.unlink()
		return result

	# @api.onchange('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency')
	# def od_onchange_reconcile(self):
	# 	print("afrrrrr",self.is_reconciled)
	# 	if self.is_reconciled:
	# 		print("yesssss")
	# @api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency')
	# def _compute_reconciliation_status(self):
	# 	res = super(AccountPayment, self)._compute_reconciliation_status()
	# 	line_ids= self.move_id.line_ids._reconciled_lines()
	# 	# print("yessssssss",line_ids,self.reconciled_invoices_count)
	# 	if line_ids and (self.reconciled_invoices_count>0 or self.reconciled_bills_count>0):
	# 		print("linnnnn",line_ids)
	# 		line_ids=list(set(line_ids))
	# 		for line in line_ids:
	# 			line_id=self.env['account.move.line'].browse(line)
	# 			print("lineeeeeeee",line_id,line_id.debit,line_id.credit)
	# 			amount_residual = 0
	# 			amount_residual_currency = 0
	# 			amount = 0
	# 			if self.payment_type=='outbound':
	# 				if line_id.debit>0:
	# 					amount_residual = line_id.amount_residual
	# 					amount_residual_currency = line_id.amount_residual_currency
	# 					amount = line_id.amount_currency
	# 				else:
	# 					payment_amt=0
	# 					payments=line_id.move_id._get_reconciled_info_JSON_values()
	# 					# print("paymentssssssss",payments,self.id,self.date,amount_residual)
	# 					for pay in payments:
	# 						if pay['account_payment_id']!=self.id and pay['date']<self.date:
	# 							# print("gggggggg",pay['payment_id'],pay['date'],pay['payment_id']!=self.id,pay['date']<self.date)
	# 							payment_amt+=pay['amount']
	# 						# if pay['payment_id']==self.id :
	# 							# print("gggggggg",pay['payment_id'],pay['date'],pay['payment_id']!=self.id,pay['date']<self.date)
	# 							# amount=pay['amount']
	# 					amount_residual_currency = line_id.move_id.amount_total - payment_amt
	# 			if self.payment_type=='inbound':
	# 				# print("hereeeeeeinvoundddd",line_id.credit,line_id.name)
	# 				if line_id.credit>0:
	# 					amount_residual_currency = line_id.amount_residual_currency
	# 					# amount = line_id.amount_currency
	# 					# amount_residual_currency = line_id.amount_residual_currency
	# 					# print("kkkkkkkkkkmmmmm",line_id,amount_residual)
	# 				else:
	# 					payment_amt=0
	# 					payments=line_id.move_id._get_reconciled_info_JSON_values()
	# 					print("paymentssssssss",payments,self.id,self.date,amount_residual)
	# 					for pay in payments:
	# 						if pay['account_payment_id']!=self.id and pay['date']<self.date:
	# 							print("gggggggg",pay['payment_id'],pay['account_payment_id'],pay['date'],pay['payment_id']!=self.id,pay['date']<self.date)
	# 							payment_amt+=pay['amount']
	# 						# if pay['payment_id']==self.id :
	# 						# 	# print("gggggggg",pay['payment_id'],pay['date'],pay['payment_id']!=self.id,pay['date']<self.date)
	# 						# 	amount=pay['amount']
	# 					amount_residual_currency = line_id.move_id.amount_total - payment_amt
	# 					# print("kkkkk",line_id.move_id.amount_total,payment_amt,amount_residual)

	# 			print("hhhhhh",line)
	# 			od_reconcile_line_vals = {
	# 			'move_id':line_id.move_id.id,
	# 			'amount_residual_currency':amount_residual_currency,
	# 			# 'amount_residual_currency':line_id.amount_residual_currency,
	# 			'debit':line_id.debit,# doing just for first creation of debit and credit
	# 			'credit':line_id.credit,# doing just for first creation of debit and credit
	# 			'date_maturity':line_id.date_maturity,
	# 			# 'amount_currency':amount,
	# 			'account_id':line_id.account_id.id,
	# 			'name':line_id.name,
	# 			'currency_id':line_id.currency_id.id,
	# 			'payment_id':self.id,
	# 			'move_line_id':line_id.id,
	# 			'partner_id':line_id.partner_id.id,
	# 			}
	# 			self.env['od.account.reconciled.line'].create(od_reconcile_line_vals)
	# 	return res
	# clean code

	@api.depends('move_id.line_ids.amount_residual', 'move_id.line_ids.amount_residual_currency')
	def _compute_reconciliation_status(self):
		res = super(AccountPayment, self)._compute_reconciliation_status()
		for rec in self:
			line_ids= rec.move_id.line_ids._reconciled_lines()
			if line_ids and (rec.reconciled_invoices_count>0 or rec.reconciled_bills_count>0):#generate only if the payment is reconciled with any of the invoices or bills
				line_ids=list(set(line_ids))
				if rec.od_reconciled_line_ids:
					rec.od_reconciled_line_ids.unlink()
				for line in line_ids:
					line_id=rec.env['account.move.line'].browse(line)
					invoice_amount_balance_fc = 0
					amount = 0
					allocation_amount_credit = 0
					allocation_amount_debit = 0
					allocation_amount_fc = 0
					amount_residual_currency = 0
					amount_residual = 0
					if rec.payment_type=='outbound':
						if line_id.debit>0:#paymentline
							amount_residual_currency = line_id.amount_residual_currency
							amount_residual = line_id.amount_residual
							for partial in line_id.matched_credit_ids:
								allocation_amount_debit=allocation_amount_debit+partial.amount
								allocation_amount_fc=allocation_amount_fc+partial.debit_amount_currency
					
							
						else:
							# calulating all oither payment total paid before current payment to find the current residual amount before this payment
							payment_amt=0
							payment_amt_company=0
							# payments=line_id.move_id._get_reconciled_info_JSON_values()
							# for pay in payments:
							# 	if pay['account_payment_id']!=rec.id and pay['date']<rec.date:
							# 		payment_amt+=pay['amount']
							# amount_residual_currency = line_id.move_id.amount_total - payment_amt

							for partial in line_id.matched_debit_ids.filtered(lambda line:line.debit_move_id.payment_id.id!=rec.id and line.debit_move_id.date<rec.date):
								payment_amt_company=payment_amt_company+partial.amount
								payment_amt=payment_amt+partial.credit_amount_currency
							amount_residual = abs(line_id.move_id.amount_total_signed) - payment_amt_company
							amount_residual_currency = line_id.move_id.amount_total - payment_amt

							# currentpayment allocation to this invoice in company currency and fc
							for partial in line_id.matched_debit_ids.filtered(lambda line:line.debit_move_id.payment_id.id==rec.id):
								allocation_amount_credit=allocation_amount_credit+partial.amount
								allocation_amount_fc=allocation_amount_fc+partial.credit_amount_currency
					
					if rec.payment_type=='inbound':
						if line_id.credit>0:#paymentline
							amount_residual_currency = line_id.amount_residual_currency
							for partial in line_id.matched_debit_ids:
								allocation_amount_credit=allocation_amount_credit+partial.amount
								allocation_amount_fc=allocation_amount_fc+partial.credit_amount_currency
						else:#invoiceline
							# calulating all oither payment total paid before current payment to find the current residual amount before this payment
							payment_amt=0
							payment_amt_company=0
							for partial in line_id.matched_credit_ids.filtered(lambda line:line.credit_move_id.payment_id.id!=rec.id and line.credit_move_id.date<rec.date):
								payment_amt_company=payment_amt_company+partial.amount
								payment_amt=payment_amt+partial.debit_amount_currency
							amount_residual = abs(line_id.move_id.amount_total_signed) - payment_amt_company
							amount_residual_currency = line_id.move_id.amount_total - payment_amt

							# payments=line_id.move_id._get_reconciled_info_JSON_values()
							# for pay in payments:
							# 	if pay['account_payment_id']!=rec.id and pay['date']<rec.date:
							# 		payment_amt+=pay['amount']
							# amount_residual_currency = line_id.move_id.amount_total - payment_amt
							# ----
							# currentpayment allocation to this invoice in company currency and fc
							for partial in line_id.matched_credit_ids.filtered(lambda line:line.credit_move_id.payment_id.id==rec.id):
								allocation_amount_debit=allocation_amount_debit+partial.amount
								allocation_amount_fc=allocation_amount_fc+partial.debit_amount_currency
					
					od_reconcile_line_vals = {
					'move_id':line_id.move_id.id,
					'amount_residual_currency':amount_residual_currency,
					'amount_residual':amount_residual,
					'debit':allocation_amount_debit,
					'credit':allocation_amount_credit,
					'date_maturity':line_id.date_maturity,
					'amount_currency':allocation_amount_fc,
					'account_id':line_id.account_id.id,
					'name':line_id.name,
					'currency_id':line_id.currency_id.id,
					'payment_id':rec.id,
					'move_line_id':line_id.id,
					'partner_id':line_id.partner_id.id,
					}
					rec.env['od.account.reconciled.line'].create(od_reconcile_line_vals)
		return res

class OdAccountReconciledLine(models.Model):
	_name = 'od.account.reconciled.line'
	description = "Orchid Reconciled Lines"

	payment_id = fields.Many2one('account.payment',string="Payment Ref", ondelete="cascade", check_company=True)
	move_id = fields.Many2one('account.move', string='Journal Entry',
		 required=True, readonly=True,
		check_company=True,
		help="The move of this entry line.")
	date = fields.Date(related='move_id.date', store=True, readonly=True, index=True, copy=False, group_operator='min')
	company_id = fields.Many2one(related='move_id.company_id', store=True, readonly=True, default=lambda self: self.env.company)
	account_id = fields.Many2one('account.account', string='Account',
		index=True, ondelete="cascade",
		domain="[('deprecated', '=', False), ('company_id', '=', 'company_id'),('is_off_balance', '=', False)]",
		check_company=True,
		tracking=True)
	partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
	ref = fields.Char(related='move_id.ref', store=True, copy=False, index=True, readonly=False)
	name = fields.Char(string='Label', tracking=True)
	company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
		readonly=True, store=True,
		help='Utility field to express amount currency')
	debit = fields.Monetary(string='Debit', default=0.0, currency_field='company_currency_id')
	credit = fields.Monetary(string='Credit', default=0.0, currency_field='company_currency_id')
	balance = fields.Monetary(string='Balance', store=True,
		currency_field='company_currency_id',
		compute='_compute_balance',
		help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
	amount_currency = fields.Monetary(string='Allocation Amount in FC', store=True, copy=True, compute='_compute_balance',
		help="The Allocation Amount")
	date_maturity = fields.Date(string='Due Date', index=True, tracking=True,
		help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
	currency_id = fields.Many2one('res.currency', string='Currency', required=True)
	amount_residual = fields.Monetary(string='Inv Balance Amt', store=True,
		currency_field='company_currency_id',
		help="The invoice balance amount before this payment. in the company currency.")
	move_line_id = fields.Many2one('account.move.line', string="Move Line")
	amount_residual_currency = fields.Monetary(string='Inv Balance Amt in FC', store=True,
		help="The invoice balance amount before this payment in fc .")

	@api.depends('debit', 'credit')
	def _compute_balance(self):
		for line in self:
			# # checking
			# pay_term_lines = line.move_line_id
			# invoice_partials = []
			# for partial in pay_term_lines.matched_debit_ids:
			# 	invoice_partials.append((partial,partial.amount, partial.credit_amount_currency, partial.debit_move_id))
			# 	print("vemdorrrrmatcjhed debitttttttttttttttttt",invoice_partials,line.name)
			# for partial in pay_term_lines.matched_credit_ids:
			# 	invoice_partials.append((partial,partial.amount, partial.debit_amount_currency, partial.credit_move_id))
			# 	print("vemdorrrrmatcjhed credittttttttt",invoice_partials,line.name)
			line.balance = line.debit - line.credit
			# amount=0
			# if line.payment_id.payment_type=='outbound':
			# 	if line.move_line_id.debit>0:
			# 		amount = abs(line.move_line_id.amount_currency)
			# 	else:
			# 		payments=line.move_id._get_reconciled_info_JSON_values()
			# 		for pay in payments:
			# 			if pay['account_payment_id']==line.payment_id.id:
			# 				amount=pay['amount']
			# if line.payment_id.payment_type=='inbound':
			# 	if line.move_line_id.credit>0:
			# 		amount = abs(line.move_line_id.amount_currency)
			# 	else:
			# 		payments=line.move_id._get_reconciled_info_JSON_values()
			# 		for pay in payments:
			# 			if pay['account_payment_id']==line.payment_id.id:
			# 				amount=pay['amount']
			# line.amount_currency=amount
			# # updating credit and debit correctly with allocation amount in company currency
			# currency_amount = line.currency_id._convert(amount,line.company_currency_id,line.payment_id.company_id,line.payment_id.date or fields.Date.context_today(self))
			# # if line.move_id.type
			# if line.debit>0:
			# 	line.debit=currency_amount
			# if line.credit>0:
			# 	line.credit=currency_amount

