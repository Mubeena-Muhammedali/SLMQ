# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import calendar


class AccountMove(models.Model):
	_inherit = "account.move"

	od_exchange_rate = fields.Float(digits=0, default=3.68,string="Exchange Rate")
	od_contact_id = fields.Many2one('res.partner', string="Contact Person", ondelete='restrict', domain="[('parent_id','=',partner_id)]", help="Partner contact person")
	od_contract_id = fields.Many2one('od.asp.contract', string="Contract")
	od_contract_name = fields.Char('Contract Name', readonly=True)
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
	od_is_bank_voucher = fields.Boolean(string="Is a Bank Voucher?", help="To determine the domain for journal")

	# def od_button_submit(self):
	# 	self.state = 'submit'

	@api.depends('bank_partner_id')
	def _compute_partner_bank_id(self):
		for move in self:
			bank_ids = move.bank_partner_id.bank_ids.filtered(lambda bank: bank.company_id is False or bank.company_id == move.company_id)
			if len(bank_ids)>1:
				move.partner_bank_id = bank_ids and bank_ids[1]
			else:
				move.partner_bank_id = bank_ids and bank_ids[0]

	@api.onchange('od_exchange_rate','currency_id','invoice_date')
	def od_onchange_exchange_rate(self):
		for move in self:
			if (
				move.od_exchange_rate not in [0, 1]
				and move.currency_id
				and move.company_id
				and move.currency_id != move.company_id.currency_id
			):
				move.invoice_currency_rate = 1 / move.od_exchange_rate
				move._inverse_currency_id()


	def od_reverse_revenue(self):
		if self.move_type == 'out_refund':
			contract_id = self.od_contract_id
			if contract_id:
				for line in self.invoice_line_ids:
					reversed_revenue_line_ids = []
					# A)Based on contractline
					if line.od_contract_line_id:
						domain = [('contract_line_id','=',line.od_contract_line_id[0].id)]
						pre_payment_id = self.env['od.contract.payment'].search(domain)
						if pre_payment_id:
							if pre_payment_id.billing_cycle == 'monthly':
								# check if the revenue line or the period id posted or not
								end_date_day=calendar.monthrange(line.od_period_from.year, line.od_period_from.month)[1]
								period_to=line.od_period_from.replace(day=end_date_day)
								r_domain = [('service_id','=',pre_payment_id.id),('period_from','=',line.od_period_from),('period_to','=',period_to),('amount','>',0)]
								revenue_line_id = self.env['od.contract.monthly.line'].search(r_domain)
								# # if posted generate a revenue line with the credit note period
								if revenue_line_id.invoiced:
									period_from = self.invoice_date.replace(day=1)
									end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
									period_to=period_from.replace(day=end_date_day)
									
									revenue_line_vals = {
									'service_id':pre_payment_id.id,
									'period_from':period_from,
									'period_to':period_to,
									'amount':-line.debit,
									'due':True,
									}
									revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
									revenue_line_id.reverse_date = self.invoice_date
									revenue_line_id.reverse_line_id = line.id
									reversed_revenue_line_ids.append(revenue_line_id.id)

								# if not posted generate a revenue line with the same period
								else:
									# get the revenue line based on invoice date
									r_domain = [('service_id','=',pre_payment_id.id),('period_from','<=',self.invoice_date),
									('period_to','>=',self.invoice_date),('amount','>',0)]
									revenue_line_id = self.env['od.contract.monthly.line'].search(r_domain)
									revenue_line_vals = {
									'service_id':pre_payment_id.id,
									'period_from':revenue_line_id.period_from,
									'period_to':revenue_line_id.period_to,
									'amount':-line.debit,
									'due':revenue_line_id.due,
									}
									revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
									revenue_line_id.reverse_date = self.invoice_date
									revenue_line_id.reverse_line_id = line.id
									reversed_revenue_line_ids.append(revenue_line_id.id)


								# @28 dec 2022 in every case create reverse revenue line in i
						
							

							if pre_payment_id.billing_cycle == 'quarterly':
								# check if the revenue line or the period id posted or not
								r_domain = [('service_id','=',pre_payment_id.id),('period_from','>=',line.od_period_from),('period_to','<=',line.od_period_to)]
								r_domain.append(('due','=',True)) #????????
								revenue_line_ids = self.env['od.contract.monthly.line'].search(r_domain)
								# if posted generate a revenue line with the credit note period


								if all(revenue_line_id.invoiced for revenue_line_id in revenue_line_ids):
									period_from = self.invoice_date.replace(day=1)
									end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
									period_to=period_from.replace(day=end_date_day)
									
									revenue_line_vals = {
									'service_id':pre_payment_id.id,
									'period_from':period_from,
									'period_to':period_to,
									'amount':-line.debit,
									'due':True,
									}
									revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
									revenue_line_id.reverse_date = self.invoice_date
									revenue_line_id.reverse_line_id = line.id
									reversed_revenue_line_ids.append(revenue_line_id.id)

								# if not posted generate a revenue line with the same period
								else:
									revenue_line_ids_posted = revenue_line_ids.filtered(lambda x: x.invoiced)
									revenue_line_ids = revenue_line_ids.filtered(lambda x:not x.invoiced)
									
									remaining_amount = line.debit
									each_month = line.debit/line.od_frequency

									posted_amt=0
									for posted_l in revenue_line_ids_posted:
										posted_amt+=posted_l.amount
									if posted_amt<=remaining_amount:
										remaining_amount = remaining_amount - posted_amt
									else:
										posted_amt=remaining_amount
										remaining_amount=0

									period_from = self.invoice_date.replace(day=1)
									end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
									period_to=period_from.replace(day=end_date_day)
									
									revenue_line_vals = {
									'service_id':pre_payment_id.id,
									'period_from':period_from,
									'period_to':period_to,
									'amount':-posted_amt,
									'due':True,
									}
									revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
									revenue_line_id.reverse_date = self.invoice_date
									revenue_line_id.reverse_line_id = line.id
									reversed_revenue_line_ids.append(revenue_line_id.id)
									
									if remaining_amount:
										for revenue_line_id in revenue_line_ids:
											# revenue_line_id = revenue_line_id[0]
											if remaining_amount:
												if remaining_amount>=each_month:
													each_month=each_month
												if remaining_amount<each_month:
													each_month=remaining_amount
												revenue_line_vals = {
												'service_id':pre_payment_id.id,
												'period_from':revenue_line_id.period_from,
												'period_to':revenue_line_id.period_to,
												'amount':-each_month,
												'due':revenue_line_id.due,
												}
												revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
												revenue_line_id.reverse_date = self.invoice_date
												revenue_line_id.reverse_line_id = line.id
												reversed_revenue_line_ids.append(revenue_line_id.id)
												remaining_amount -= each_month
									
										


							# halfyrly
							if pre_payment_id.billing_cycle == 'half':
								# check if the revenue line or the period id posted or not
								r_domain = [('service_id','=',pre_payment_id.id),('period_from','>=',line.od_period_from),('period_to','<=',line.od_period_to)]
								r_domain.append(('due','=',True)) #????????
								revenue_line_ids = self.env['od.contract.monthly.line'].search(r_domain)
								# if posted generate a revenue line with the credit note period


								if all(revenue_line_id.invoiced for revenue_line_id in revenue_line_ids):
									period_from = self.invoice_date.replace(day=1)
									end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
									period_to=period_from.replace(day=end_date_day)
									
									revenue_line_vals = {
									'service_id':pre_payment_id.id,
									'period_from':period_from,
									'period_to':period_to,
									'amount':-line.debit,
									'due':True,
									}
									revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
									revenue_line_id.reverse_date = self.invoice_date
									revenue_line_id.reverse_line_id = line.id
									reversed_revenue_line_ids.append(revenue_line_id.id)

								# if not posted generate a revenue line with the same period
								else:
									revenue_line_ids_posted = revenue_line_ids.filtered(lambda x: x.invoiced)
									revenue_line_ids = revenue_line_ids.filtered(lambda x:not x.invoiced)
									
									remaining_amount = line.debit
									each_month = line.debit/line.od_frequency

									posted_amt=0
									for posted_l in revenue_line_ids_posted:
										posted_amt+=posted_l.amount
									if posted_amt<=remaining_amount:
										remaining_amount = remaining_amount - posted_amt
									else:
										posted_amt=remaining_amount
										remaining_amount=0

									period_from = self.invoice_date.replace(day=1)
									end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
									period_to=period_from.replace(day=end_date_day)
									
									revenue_line_vals = {
									'service_id':pre_payment_id.id,
									'period_from':period_from,
									'period_to':period_to,
									'amount':-posted_amt,
									'due':True,
									}
									revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
									revenue_line_id.reverse_date = self.invoice_date
									revenue_line_id.reverse_line_id = line.id
									reversed_revenue_line_ids.append(revenue_line_id.id)
									if remaining_amount:
										for revenue_line_id in revenue_line_ids:
											if remaining_amount:
												if remaining_amount>=each_month:
													each_month=each_month
												if remaining_amount<each_month:
													each_month=remaining_amount
												revenue_line_vals = {
												'service_id':pre_payment_id.id,
												'period_from':revenue_line_id.period_from,
												'period_to':revenue_line_id.period_to,
												'amount':-each_month,
												'due':revenue_line_id.due,
												}
												revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
												revenue_line_id.reverse_date = self.invoice_date
												revenue_line_id.reverse_line_id = line.id
												reversed_revenue_line_ids.append(revenue_line_id.id)
												remaining_amount -= each_month
										

							# yrly
							if pre_payment_id.billing_cycle in ('yearly','annually'):
								# check if the revenue line or the period id posted or not
								r_domain = [('service_id','=',pre_payment_id.id),('period_from','>=',line.od_period_from),('period_to','<=',line.od_period_to)]
								r_domain.append(('due','=',True)) #????????
								revenue_line_ids = self.env['od.contract.monthly.line'].search(r_domain)
								# if posted generate a revenue line with the credit note period


								if all(revenue_line_id.invoiced for revenue_line_id in revenue_line_ids):
									period_from = self.invoice_date.replace(day=1)
									end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
									period_to=period_from.replace(day=end_date_day)
									
									revenue_line_vals = {
									'service_id':pre_payment_id.id,
									'period_from':period_from,
									'period_to':period_to,
									'amount':-line.debit,
									'due':True,
									}
									revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
									revenue_line_id.reverse_date = self.invoice_date
									revenue_line_id.reverse_line_id = line.id
									reversed_revenue_line_ids.append(revenue_line_id.id)

								# if not posted generate a revenue line with the same period
								else:
									revenue_line_ids_posted = revenue_line_ids.filtered(lambda x: x.invoiced)
									revenue_line_ids = revenue_line_ids.filtered(lambda x:not x.invoiced)
									
									remaining_amount = line.debit
									each_month = line.debit/line.od_frequency

									posted_amt=0
									for posted_l in revenue_line_ids_posted:
										posted_amt+=posted_l.amount
									if posted_amt<=remaining_amount:
										remaining_amount = remaining_amount - posted_amt
									else:
										posted_amt=remaining_amount
										remaining_amount=0
									
									period_from = self.invoice_date.replace(day=1)
									end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
									period_to=period_from.replace(day=end_date_day)
									
									revenue_line_vals = {
									'service_id':pre_payment_id.id,
									'period_from':period_from,
									'period_to':period_to,
									'amount':-posted_amt,
									'due':True,
									}
									revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
									revenue_line_id.reverse_date = self.invoice_date
									revenue_line_id.reverse_line_id = line.id
									reversed_revenue_line_ids.append(revenue_line_id.id)
									if remaining_amount:
										for revenue_line_id in revenue_line_ids:
											# revenue_line_id = revenue_line_id[0]
											if remaining_amount:
												if remaining_amount>=each_month:
													each_month=each_month
												if remaining_amount<each_month:
													each_month=remaining_amount
												revenue_line_vals = {
												'service_id':pre_payment_id.id,
												'period_from':revenue_line_id.period_from,
												'period_to':revenue_line_id.period_to,
												'amount':-each_month,
												'due':revenue_line_id.due,
												}
												revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
												revenue_line_id.reverse_date = self.invoice_date
												revenue_line_id.reverse_line_id = line.id
												reversed_revenue_line_ids.append(revenue_line_id.id)
												remaining_amount-=each_month


							if pre_payment_id.billing_cycle == 'one_time':
								r_domain = [('service_id','=',pre_payment_id.id),('period_from','>=',line.od_period_from),('period_to','<=',line.od_period_to)]
								r_domain.append(('due','=',True)) #????????
								revenue_line_id = self.env['od.contract.monthly.line'].search(r_domain)
								# # if posted generate a revenue line with the credit note period
								# if revenue_line_id.invoiced:
								period_from = self.invoice_date.replace(day=1)
								end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
								period_to=period_from.replace(day=end_date_day)
								
								revenue_line_vals = {
								'service_id':pre_payment_id.id,
								'period_from':period_from,
								'period_to':period_to,
								'amount':-line.debit,
								'due':True,
								}
								revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
								revenue_line_id.reverse_date = self.invoice_date
								revenue_line_id.reverse_line_id = line.id
								reversed_revenue_line_ids.append(revenue_line_id.id)
					
					# B) Based on Invoice, THis case will not arise
					else:
						domain = [('contract_id','=',contract_id.id),('states','=','active')]
						pre_payment_id = self.env['od.contract.payment'].search(domain, limit=1)
						if pre_payment_id:
							if pre_payment_id.billing_cycle == 'monthly':
								period_from = self.invoice_date.replace(day=1)
								end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
								period_to=period_from.replace(day=end_date_day)
								
								revenue_line_vals = {
								'service_id':pre_payment_id.id,
								'period_from':period_from,
								'period_to':period_to,
								'amount':-line.debit
								}
								revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id
								reversed_revenue_line_ids.append(revenue_line_id.id)

							if pre_payment_id.billing_cycle == 'quarterly':
								period_from = self.invoice_date.replace(day=1)
								end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
								period_to=period_from.replace(day=end_date_day)
								
								revenue_line_vals = {
								'service_id':pre_payment_id.id,
								'period_from':period_from,
								'period_to':period_to,
								'amount':-line.debit
								}
								revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id
								reversed_revenue_line_ids.append(revenue_line_id.id)
					line.od_reversed_revenue_line_ids = [(6,0,reversed_revenue_line_ids)]



	def _post(self, soft=True):
		res = super(AccountMove, self)._post(soft)
		for move in res:
			if move.move_type == 'out_refund':
				move.od_reverse_revenue()
		return res


	def button_cancel(self):
		res = super(AccountMove, self).button_cancel()
		# overridden to update the posted(invoiced) field of revenue line. if the entry is not in posted state , the field is set to false
		revenue_line_ids = self.env['od.contract.monthly.line'].search([('move_id','=',self.id)])
		for line in revenue_line_ids:
			line.invoiced=False
		return res
	
	def button_draft(self):
		res = super(AccountMove, self).button_draft()
		# overridden to update the posted(invoiced) field of revenue line. if the entry is not in posted state , the field is set to false
		revenue_line_ids = self.env['od.contract.monthly.line'].search([('move_id','=',self.id)])
		for line in revenue_line_ids:
			line.invoiced=False
		if self.move_type == 'out_refund':
				for line in self.invoice_line_ids:
					if line.od_reversed_revenue_line_ids:
						line.od_reversed_revenue_line_ids.unlink()
		return res

	def action_post(self):
		res = super(AccountMove, self).action_post()

		# if self.state == 'draft' and self.od_is_bank_voucher and self.od_reveiew:
		# 	raise UserError(_("Please Submit the record!!!"))
		# if self.od_is_bank_voucher and self.env.user.id == self.create_uid.id and self.od_reveiew:
		# 	raise UserError(_("You are not allowed to post this record!!!"))

		# overridden to update the posted(invoiced) field of revenue line. if the entry is reposted , the field is set to true
		revenue_line_ids = self.env['od.contract.monthly.line'].search([('move_id','=',self.id)])
		for line in revenue_line_ids:
			line.invoiced=True
		return res
	

class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	od_frequency = fields.Integer(string="Frequency", default=1)

	od_period_from = fields.Date(string="Period From")#contract purpose
	od_period_to = fields.Date(string="Period To")#contract purpose
	od_contract_line_id = fields.Many2many('od.asp.contract.line', string="Contract Line")
	purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', index=True, copy=False)
	purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order', related='purchase_line_id.order_id', readonly=True, copy=False)
	od_revenue_line_id = fields.Many2one('od.contract.monthly.line', string="Revenue Line")
	od_reversed_revenue_line_ids = fields.Many2many('od.contract.monthly.line', string="Reversed Revenue Line")



	@api.onchange('od_frequency')
	def od_onchange_freq(self):
		for line in self:
			line._compute_totals()

	@api.onchange('quantity', 'discount', 'price_unit', 'tax_ids','od_frequency')
	def od_onchange_line_exchange_rate(self):
		for line in self:
			line.move_id.od_onchange_exchange_rate()




