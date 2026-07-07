# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import calendar


class AccountInvoice(models.Model):
	_inherit = "account.move"

	od_exchange_rate = fields.Float(digits=0, default=3.68,string="Exchange Rate")
	od_contact_id = fields.Many2one('res.partner', string="Contact Person", ondelete='restrict', domain="[('parent_id','=',partner_id)]", help="Partner contact person")
	# od_sam_id = fields.Many2one('res.users', string="SAM")
	od_contract_id = fields.Many2one('od.asp.contract', string="Contract")
	od_contract_name = fields.Char('Contract Name', readonly=True)

	# od_cc = fields.Char(string="CC")

	# @api.model_create_multi
	# def create(self, vals_list):
	# 	for vals in vals_list:
	# 		if vals['move_type'] in ('out_invoice','out_refund'):
	# 			if not vals['od_contract_id']:
	# 				raise UserError(_("Contract is not set !!!!"))
	# 	return super(AccountInvoice, self).create(vals_list)

	@api.depends('bank_partner_id')
	def _compute_partner_bank_id(self):
		for move in self:
			bank_ids = move.bank_partner_id.bank_ids.filtered(lambda bank: bank.company_id is False or bank.company_id == move.company_id)
			# move.partner_bank_id = bank_ids and bank_ids[0]
			if len(bank_ids)>1:
				move.partner_bank_id = bank_ids and bank_ids[1]
			else:
				move.partner_bank_id = bank_ids and bank_ids[0]

	@api.onchange('od_exchange_rate','currency_id','invoice_date')
	def od_onchange_exchange_rate(self):
		for line in self:
			if self.od_exchange_rate not in [0,1] and self.currency_id.id!=self.company_id.currency_id.id:
				date = self.invoice_date if self.invoice_date else datetime.today().date()
				currency_rate_id = self.env['res.currency.rate'].search([('currency_id','=',self.currency_id.id),('name','<=',date)],limit=1, order='name desc')
				inv_rate = self.od_exchange_rate
				if currency_rate_id:
					if currency_rate_id.rate != (1/inv_rate):
						if currency_rate_id.name!=date:
							vals={
							'currency_id':self.currency_id.id,
							'name':date,
							'rate':(1/inv_rate),
							}
							c=self.env['res.currency.rate'].create(vals)
						else:
							currency_rate_id.rate=(1/inv_rate)
						line._onchange_currency()
				else:
					vals={
					'currency_id':self.currency_id.id,
					'name':date,
					'rate':(1/inv_rate),
					}
					c=self.env['res.currency.rate'].create(vals)
					line._onchange_currency()

	# def action_post(self):
	# 	res = super(AccountInvoice, self).action_post()
	# 	print("iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii")
	# 	if self.move_type == 'out_refund':
	# 		print("uuuuuuuuuuuuujjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj")
	# 		contract_id = self.od_contract_id
	# 		if contract_id:
	# 			print("yessssssssssssssssssssssssscccccccccccc")
	# 			for line in self.invoice_line_ids:
	# 				# print("lineeeeeeddddddddd",line.od_contract_line_id,line.od_contract_line_id[0].id)
	# 				# A)Based on contractline
	# 				if line.od_contract_line_id:
	# 					domain = [('contract_line_id','=',line.od_contract_line_id[0].id),('states','=','active')]
	# 					pre_payment_id = self.env['od.contract.payment'].search(domain)
	# 					# print("kjnnnnnnnn",pre_payment_id)
	# 					if pre_payment_id:
	# 						if pre_payment_id.billing_cycle == 'monthly':
	# 							# check if the revenue line or the period id posted or not
	# 							end_date_day=calendar.monthrange(line.od_period_from.year, line.od_period_from.month)[1]
	# 							period_to=line.od_period_from.replace(day=end_date_day)
	# 							r_domain = [('service_id','=',pre_payment_id.id),('period_from','=',line.od_period_from),('period_to','=',period_to)]
	# 							revenue_line_id = self.env['od.contract.monthly.line'].search(r_domain)
	# 							# print("oooooooo",revenue_line_id,line.od_period_from,period_to,line.name)
	# 							# if posted generate a revenue line with the credit note period
	# 							if revenue_line_id.invoiced:
	# 								print("hereeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeinvoicedddddddd")
	# 								period_from = self.invoice_date.replace(day=1)
	# 								end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
	# 								period_to=period_from.replace(day=end_date_day)
									
	# 								revenue_line_vals = {
	# 								'service_id':pre_payment_id.id,
	# 								'period_from':period_from,
	# 								'period_to':period_to,
	# 								'amount':-line.debit,
	# 								}
	# 								# print("revnnnnn vlll",revenue_line_vals)
	# 								# print(s)
	# 								line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id

	# 							# if not posted generate a revenue line with the same period
	# 							else:
	# 								revenue_line_vals = {
	# 								'service_id':pre_payment_id.id,
	# 								'period_from':revenue_line_id.period_from,
	# 								'period_to':revenue_line_id.period_to,
	# 								'amount':-line.debit,
	# 								'due':revenue_line_id.due,
	# 								}
	# 								# print("revnnnnn vlll elssssssssss",revenue_line_vals)
	# 								# print(b)
	# 								line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id
						
	# 						# if pre_payment_id.billing_cycle == 'quarterly':
	# 						# 	# check if the revenue line or the period id posted or not
	# 						# 	r_domain = [('service_id','=',pre_payment_id.id),('period_from','>=',line.od_period_from),('period_to','<=',line.od_period_to)]
	# 						# 	revenue_line_ids = self.env['od.contract.monthly.line'].search(r_domain)
	# 						# 	# if posted generate a revenue line with the credit note period

	# 						# 	if all(revenue_line_id.invoiced for revenue_line_id in revenue_line_ids):
	# 						# 		period_from = self.invoice_date.replace(day=1)
	# 						# 		end_date_day=calendar.monthrange(od_period_from.year, od_period_from.month)[1]
	# 						# 		period_to=od_period_from.replace(day=end_date_day)
									
	# 						# 		revenue_line_vals = {
	# 						# 		'service_id':pre_payment_id.id,
	# 						# 		'period_from':period_from,
	# 						# 		'period_to':period_to,
	# 						# 		'amount':-line.price_subtotal
	# 						# 		}
	# 						# 		line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id

	# 						# 	# if not posted generate a revenue line with the same period
	# 						# 	else:
	# 						# 		revenue_line_id = revenue_line_ids.filtered(lambda x:not x.invoiced)
	# 						# 		if revenue_line_id:
	# 						# 			revenue_line_id = revenue_line_id[0]
	# 						# 			revenue_line_vals = {
	# 						# 			'service_id':pre_payment_id.id,
	# 						# 			'period_from':revenue_line_id.period_from,
	# 						# 			'period_to':revenue_line_id.period_to,
	# 						# 			'amount':-line.price_subtotal
	# 						# 			}
	# 						# 			line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id

	# 						if pre_payment_id.billing_cycle == 'quarterly':
	# 							# check if the revenue line or the period id posted or not
	# 							r_domain = [('service_id','=',pre_payment_id.id),('period_from','>=',line.od_period_from),('period_to','<=',line.od_period_to)]
	# 							r_domain.append(('due','=',True)) #????????
	# 							revenue_line_ids = self.env['od.contract.monthly.line'].search(r_domain)
	# 							# if posted generate a revenue line with the credit note period

	# 							# print("rrrrrrrrrrrwwww",revenue_line_ids,pre_payment_id)
	# 							# print(s)

	# 							if all(revenue_line_id.invoiced for revenue_line_id in revenue_line_ids):
	# 								print("????????????????????/")
	# 								period_from = self.invoice_date.replace(day=1)
	# 								end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
	# 								period_to=period_from.replace(day=end_date_day)
									
	# 								revenue_line_vals = {
	# 								'service_id':pre_payment_id.id,
	# 								'period_from':period_from,
	# 								'period_to':period_to,
	# 								'amount':-line.debit,
	# 								# 'due':True,??????
	# 								}
	# 								line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id

	# 							# if not posted generate a revenue line with the same period
	# 							else:
	# 								revenue_line_ids = revenue_line_ids.filtered(lambda x:not x.invoiced)
	# 								remaining_amount = line.debit
	# 								each_month = line.debit/line.frequency
									
	# 								for revenue_line_id in revenue_line_ids:
	# 									# revenue_line_id = revenue_line_id[0]
	# 									# print("revenue_line_id",revenue_line_id)
	# 									revenue_line_vals = {
	# 									'service_id':pre_payment_id.id,
	# 									'period_from':revenue_line_id.period_from,
	# 									'period_to':revenue_line_id.period_to,
	# 									'amount':-each_month,
	# 									'due':revenue_line_id.due,
	# 									}
	# 									# print("vvvvvvvvvddd",revenue_line_vals)
	# 									line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id
	# 									remaining_amount = remaining_amount - each_month
	# 								if remaining_amount:
	# 									period_from = self.invoice_date.replace(day=1)
	# 									end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
	# 									period_to=period_from.replace(day=end_date_day)
										
	# 									revenue_line_vals = {
	# 									'service_id':pre_payment_id.id,
	# 									'period_from':period_from,
	# 									'period_to':period_to,
	# 									'amount':-remaining_amount,
	# 									# 'due':True,??????
	# 									}
	# 									line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id

	# 						# halfyrly
	# 						if pre_payment_id.billing_cycle == 'half':
	# 							# check if the revenue line or the period id posted or not
	# 							r_domain = [('service_id','=',pre_payment_id.id),('period_from','>=',line.od_period_from),('period_to','<=',line.od_period_to)]
	# 							r_domain.append(('due','=',True)) #????????
	# 							revenue_line_ids = self.env['od.contract.monthly.line'].search(r_domain)
	# 							# if posted generate a revenue line with the credit note period

	# 							# print("rrrrrrrrrrrwwww",revenue_line_ids,pre_payment_id)
	# 							# print(s)

	# 							if all(revenue_line_id.invoiced for revenue_line_id in revenue_line_ids):
	# 								print("????????????????????/")
	# 								period_from = self.invoice_date.replace(day=1)
	# 								end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
	# 								period_to=period_from.replace(day=end_date_day)
									
	# 								revenue_line_vals = {
	# 								'service_id':pre_payment_id.id,
	# 								'period_from':period_from,
	# 								'period_to':period_to,
	# 								'amount':-line.debit,
	# 								# 'due':True,??????
	# 								}
	# 								line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id

	# 							# if not posted generate a revenue line with the same period
	# 							else:
	# 								revenue_line_ids = revenue_line_ids.filtered(lambda x:not x.invoiced)
									
	# 								remaining_amount = line.debit
	# 								each_month = line.debit/line.frequency
									
	# 								for revenue_line_id in revenue_line_ids:
	# 									# revenue_line_id = revenue_line_id[0]
	# 									# print("revenue_line_id",revenue_line_id)
	# 									revenue_line_vals = {
	# 									'service_id':pre_payment_id.id,
	# 									'period_from':revenue_line_id.period_from,
	# 									'period_to':revenue_line_id.period_to,
	# 									'amount':-each_month,
	# 									'due':revenue_line_id.due,
	# 									}
	# 									# print("vvvvvvvvvddd",revenue_line_vals)
	# 									line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id
	# 									remaining_amount = remaining_amount - each_month
	# 								if remaining_amount:
	# 									period_from = self.invoice_date.replace(day=1)
	# 									end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
	# 									period_to=period_from.replace(day=end_date_day)
										
	# 									revenue_line_vals = {
	# 									'service_id':pre_payment_id.id,
	# 									'period_from':period_from,
	# 									'period_to':period_to,
	# 									'amount':-remaining_amount,
	# 									# 'due':True,??????
	# 									}
	# 									line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id

					
	# 				# B) Based on Invoice
	# 				else:
	# 					domain = [('contract_id','=',contract_id.id),('states','=','active')]
	# 					pre_payment_id = self.env['od.contract.payment'].search(domain, limit=1)
	# 					if pre_payment_id:
	# 						if pre_payment_id.billing_cycle == 'monthly':
	# 							period_from = self.invoice_date.replace(day=1)
	# 							end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
	# 							period_to=period_from.replace(day=end_date_day)
								
	# 							revenue_line_vals = {
	# 							'service_id':pre_payment_id.id,
	# 							'period_from':period_from,
	# 							'period_to':period_to,
	# 							'amount':-line.debit
	# 							}
	# 							line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id

	# 						if pre_payment_id.billing_cycle == 'quarterly':
	# 							period_from = self.invoice_date.replace(day=1)
	# 							end_date_day=calendar.monthrange(period_from.year, period_from.month)[1]
	# 							period_to=period_from.replace(day=end_date_day)
								
	# 							revenue_line_vals = {
	# 							'service_id':pre_payment_id.id,
	# 							'period_from':period_from,
	# 							'period_to':period_to,
	# 							'amount':-line.debit
	# 							}
	# 							line.od_revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals).id

	# 	# print(s)
	# 	return res


	def od_reverse_revenue(self):
		if self.move_type == 'out_refund':
			print("uuuuuuuuuuuuujjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj")
			contract_id = self.od_contract_id
			if contract_id:
				print("yessssssssssssssssssssssssscccccccccccc")
				for line in self.invoice_line_ids:
					reversed_revenue_line_ids = []
					# A)Based on contractline
					if line.od_contract_line_id:
						# domain = [('contract_line_id','=',line.od_contract_line_id[0].id),('states','=','active')]
						domain = [('contract_line_id','=',line.od_contract_line_id[0].id)]
						pre_payment_id = self.env['od.contract.payment'].search(domain)
						# print('bnnnnnnnnn',pre_payment_id,pre_payment_id.billing_cycle)
						# print(p)
						if pre_payment_id:
							if pre_payment_id.billing_cycle == 'monthly':
								# check if the revenue line or the period id posted or not
								end_date_day=calendar.monthrange(line.od_period_from.year, line.od_period_from.month)[1]
								period_to=line.od_period_from.replace(day=end_date_day)
								r_domain = [('service_id','=',pre_payment_id.id),('period_from','=',line.od_period_from),('period_to','=',period_to),('amount','>',0)]
								revenue_line_id = self.env['od.contract.monthly.line'].search(r_domain)
								# # if posted generate a revenue line with the credit note period
								if revenue_line_id.invoiced:
									print("hereeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeinvoicedddddddd")
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
									# revenue_line_vals = {
									# 'service_id':pre_payment_id.id,
									# 'period_from':revenue_line_id.period_from,
									# 'period_to':revenue_line_id.period_to,
									# 'amount':-line.debit,
									# 'due':revenue_line_id.due,
									# }
									# get the revenue line based on invoice date
									r_domain = [('service_id','=',pre_payment_id.id),('period_from','<=',self.invoice_date),
									('period_to','>=',self.invoice_date),('amount','>',0)]
									revenue_line_id = self.env['od.contract.monthly.line'].search(r_domain)
									print("kfffdd",revenue_line_id)
									for r in revenue_line_id:
										print("rrr",r.period_from,r.period_to,r.service_id,pre_payment_id,r.id)
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

								# print("rrrrrrrrrrrwwww",revenue_line_ids,pre_payment_id)
								# print(s)

								if all(revenue_line_id.invoiced for revenue_line_id in revenue_line_ids):
									print("????????????????????/")
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
									print("alll",revenue_line_ids,r_domain)
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

									# print("hhhhhgggggg",revenue_line_ids_posted,revenue_line_ids,remaining_amount,posted_amt)
									# print(s)
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
											# print("revenue_line_idammm",remaining_amount,each_month)
											if remaining_amount:
												if remaining_amount>=each_month:
													each_month=each_month
												if remaining_amount<each_month:
													each_month=remaining_amount
												# print("rrrrrrrrrrrr111",revenue_line_id,remaining_amount,each_month)
												revenue_line_vals = {
												'service_id':pre_payment_id.id,
												'period_from':revenue_line_id.period_from,
												'period_to':revenue_line_id.period_to,
												'amount':-each_month,
												'due':revenue_line_id.due,
												}
												# print("vvvvvvvvvddd",revenue_line_vals)
												revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
												revenue_line_id.reverse_date = self.invoice_date
												revenue_line_id.reverse_line_id = line.id
												reversed_revenue_line_ids.append(revenue_line_id.id)
												remaining_amount -= each_month
												# print("rrrrrrlll",remaining_amount)
									
										


							# halfyrly
							if pre_payment_id.billing_cycle == 'half':
								# check if the revenue line or the period id posted or not
								r_domain = [('service_id','=',pre_payment_id.id),('period_from','>=',line.od_period_from),('period_to','<=',line.od_period_to)]
								r_domain.append(('due','=',True)) #????????
								revenue_line_ids = self.env['od.contract.monthly.line'].search(r_domain)
								# if posted generate a revenue line with the credit note period

								# print("rrrrrrrrrrrwwww",revenue_line_ids,pre_payment_id)
								# print(s)

								if all(revenue_line_id.invoiced for revenue_line_id in revenue_line_ids):
									print("????????????????????/")
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
											# print("revenue_line_id",revenue_line_id)
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
												# print("vvvvvvvvvddd",revenue_line_vals)
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

								# print("rrrrrrrrrrrwwww",revenue_line_ids,pre_payment_id)
								# print(s)

								if all(revenue_line_id.invoiced for revenue_line_id in revenue_line_ids):
									print("????????????????????/")
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
											# print("revenue_line_id",revenue_line_id)
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
												# print("vvvvvvvvvddd",revenue_line_vals)
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
								print("hereeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeinvoicedddddddd")
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
								# else:
								# 	# revenue_line_vals = {
								# 	# 'service_id':pre_payment_id.id,
								# 	# 'period_from':revenue_line_id.period_from,
								# 	# 'period_to':revenue_line_id.period_to,
								# 	# 'amount':-line.debit,
								# 	# 'due':revenue_line_id.due,
								# 	# }
								# 	# get the revenue line based on invoice date
								# 	# r_domain = [('service_id','=',pre_payment_id.id),('period_from','<=',self.invoice_date),
								# 	# ('period_to','>=',self.invoice_date),('amount','>',0)]
								# 	# revenue_line_id = self.env['od.contract.monthly.line'].search(r_domain)
								# 	# print("kfffdd",revenue_line_id)
								# 	# for r in revenue_line_id:
								# 	# 	print("rrr",r.period_from,r.period_to,r.service_id,pre_payment_id,r.id)
								# 	revenue_line_vals = {
								# 	'service_id':pre_payment_id.id,
								# 	'period_from':revenue_line_id.period_from,
								# 	'period_to':revenue_line_id.period_to,
								# 	'amount':-line.debit,
								# 	'due':revenue_line_id.due,
								# 	}
								# 	revenue_line_id = self.env['od.contract.monthly.line'].create(revenue_line_vals)
								# 	revenue_line_id.reverse_date = self.invoice_date
								# 	revenue_line_id.reverse_line_id = line.id
								# 	reversed_revenue_line_ids.append(revenue_line_id.id)
					
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
		res = super(AccountInvoice, self)._post(soft)
		# print("jjjjjjjbbbbbbbbbbbbb")
		for move in res:
			if move.move_type == 'out_refund':
				move.od_reverse_revenue()
		return res

	def button_draft(self):
		res = super(AccountInvoice, self).button_draft()
		if self.move_type == 'out_refund':
			for line in self.invoice_line_ids:
				if line.od_reversed_revenue_line_ids:
					line.od_reversed_revenue_line_ids.unlink()
	

class AccountInvoiceLine(models.Model):
	_inherit = "account.move.line"

	od_frequency = fields.Integer(string="Frequency", default=1)

	od_period_from = fields.Date(string="Period From")#contract purpose
	od_period_to = fields.Date(string="Period To")#contract purpose
	od_contract_line_id = fields.Many2many('od.asp.contract.line', string="Contract Line")
	purchase_line_id = fields.Many2one('purchase.order.line', 'Purchase Order Line', ondelete='set null', index=True, copy=False)
	purchase_order_id = fields.Many2one('purchase.order', 'Purchase Order', related='purchase_line_id.order_id', readonly=True, copy=False)



	@api.onchange('od_frequency')
	def od_onchange_freq(self):
		for line in self:
			line._onchange_price_subtotal()

	@api.onchange('quantity', 'discount', 'price_unit', 'tax_ids','od_frequency')
	def od_onchange_line_exchange_rate(self):
		for line in self:
			line.move_id.od_onchange_exchange_rate()




