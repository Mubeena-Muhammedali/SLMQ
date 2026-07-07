
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta
import pandas as pd
import math
from odoo.tools import float_compare, float_is_zero

class OrchidContractPayment(models.Model):
	_name = "od.contract.payment"
	_description = "Contract Line Payments"
	_inherit = ['mail.thread']

	name = fields.Char(string="Contract ID", tracking=True)
	contract_line_id = fields.Many2one('od.asp.contract.line', string='Service',ondelete='restrict')  # Unrequired company
	contract_id = fields.Many2one('od.asp.contract', string="Contract")
	payment_line = fields.One2many('od.contract.payment.line','service_id', string="Payment Lines")
	start_date = fields.Date(string="Start Date")
	end_date = fields.Date(string="End Date")
	billing_cycle = fields.Selection([('monthly','Monthly'), ('quarterly','Quarterly'), ('half','Half yearly'), ('yearly','Yearly'), ('one_time','One Time'), ('annually','Annually')], string="Billing Cycle")
	total_amount = fields.Float(digits='Product Price', string="Total Amount")
	per_month = fields.Float(digits=(16,3), string="Per Month Amount")
	states=fields.Selection(related="contract_line_id.state", string="State",store=True)
	partner_id = fields.Many2one('res.partner', string="Customer")
	monthly_line_ids = fields.One2many('od.contract.monthly.line','service_id', string="Payment Lines")
	fluctuating_contract=fields.Boolean(string="Fluctuating Service", help="returns true if this prepayment is associated with a fluctuating contractline", default=False, copy=False)
	contract_name = fields.Char('Contract Name', related="contract_id.contract_code", store=True)
	
	costing_line_ids = fields.One2many('od.direct.costing.line','service_id', string="Direct Costing Line")


	def link_monthly_lines(self):
		for line in self. monthly_line_ids:
			if not line.reverse_line_id:
				# print("lineeeeee",line)
				for pl in self.payment_line:
					# print("payment linneee",pl.period_from,pl.period_to)
					if (pl.period_from<=line.period_to) and (pl.period_to>=line.period_to):
						# print("yessss",line.period_to)
						m_ls = pl.monthly_line_ids.ids
						m_ls.append(line.id)
						m_ls = list(set(m_ls))
						# print("kkkkk",m_ls)
						pl.write({'monthly_line_ids':[(6,0,m_ls)]})
						# print("kkfffff",pl.monthly_line_ids)

	# def close_payment(self):
	# 	for pay in self:
	# 		pay.states='close'

	# def action_close(self):
	# 	payment_ids = self.env['od.contract.payment'].browse().filtered(lambda r:all(r.payment_line.invoiced==True))
	# 	payment_ids.close_payment()
		
	def generate_direct_costing_line(self):
		print("kkkkkkkkkklllllllllllll")
		if self.contract_line_id.total_direct_cost>0:
			if self.costing_line_ids:
				self.costing_line_ids.unlink()
			print('herecccccccccccccccccccccccccc')

			start_date = self.start_date.replace(day=1)
			no_of_months = self.contract_line_id.frequency-1
			end_date = start_date+relativedelta(months=+no_of_months)
			end_date_day=calendar.monthrange(end_date.year, end_date.month)[1]
			end_date=end_date.replace(day=end_date_day)
			print("nnnnnoooo",end_date,start_date)

			month_start_date = start_date
			month_end_date_day = calendar.monthrange(month_start_date.year, month_start_date.month)[1]
			month_end_date=month_start_date.replace(day=month_end_date_day)

			# have to check annual cas, cancelled case

			cost_per_month = self.contract_line_id.total_direct_cost/self.contract_line_id.frequency

			while(month_end_date<=end_date):
				line_vals={
				'service_id':self.id,
				'period_from':month_start_date,
				'period_to':month_end_date,
				'amount':cost_per_month,
				'invoiced':False,
				'product_id':self.contract_line_id.product_id.id,
				# 'purchase_line_id':line.id,
				}
				self.env['od.direct.costing.line'].create(line_vals)
				next_month_start = month_start_date.replace(day=1)
				month_start_date = next_month_start+relativedelta(months=+1)
				month_end_date_day=calendar.monthrange(month_start_date.year, month_start_date.month)[1]
				month_end_date=month_start_date.replace(day=month_end_date_day)

	def generate_lines(self, start_date, end_date, period_start, frequency, months, amount_per_days, total_amount):
		t_amount = 0
		t_amount1 = 0
		period_start = period_start
		if self.contract_line_id.acculde:
			to_date_end_day=calendar.monthrange(period_start.year, period_start.month)[1]
			to_date=period_start.replace(day=to_date_end_day)
			period_end=to_date
			while(period_end<=end_date):
				no_of_month_days = calendar.monthrange(period_start.year, period_start.month)[1]
				no_days = abs((period_end - period_start).days)+1
				# unit_price = self.contract_line_id.price_unit*self.contract_line_id.product_uom_qty
				unit_price = self.per_month
				# if self.contract_line_id.billing_cycle=='yearly':
				# 	no_of_months = len(pd.date_range(start_date, end_date, freq='M'))
				# 	new_no_of_years = no_of_months/12
				# 	# print("jjjjjjjjjj",new_no_of_years,new_no_of_years>int(new_no_of_years))
				# 	if new_no_of_years>int(new_no_of_years):
				# 		new_no_of_years = int(new_no_of_years)+1
				# 	else:
				# 		new_no_of_years = int(new_no_of_years)
				# 	unit_price = (self.contract_line_id.price_unit*self.contract_line_id.product_uom_qty*self.contract_line_id.frequency)/

				# amount_to_invoice = (unit_price/no_of_month_days)*no_days
				amount_to_invoice = (unit_price/no_of_month_days)*no_of_month_days
				amount_to_invoice = amount_to_invoice * self.contract_id.od_exchange_rate #exchnge rate change
				line_vals={
				'service_id':self.id,
				'period_from':period_start,
				'period_to':period_end,
				'amount':amount_to_invoice,
				'invoiced':False,
				}
				# if period_end == end_date and t_amount < total_amount:
				# 	line_vals['amount'] = total_amount-t_amount
				# for special case, we have to update the amount for first period line from already made invoice 
				# if self.contract_line_id.state=='draft' and len(self.contract_line_id.invoice_line_ids)==1 and q==1:
				# 	line_vals['amount'] = self.contract_line_id.invoice_line_ids[0].price_total
				# 	line_vals['invoiced'] = True
				# 	line_vals['invoice_line_id'] = self.contract_line_id.invoice_line_ids[0].id
				
				# line_id=self.env['od.contract.payment.line'].create(line_vals)
				# line_tot=t_amount
				# t_amount+=line_vals['amount']
				if period_end == end_date:
					line_tot1=t_amount1
					t_amount1+=line_vals['amount']
					if self.payment_line:
						total_amount = 0
						for line in self.payment_line:
							total_amount+=line.amount
						total_amount = total_amount * self.contract_id.od_exchange_rate #exchnge rate change
						if period_end == end_date and t_amount1 != total_amount:
							line_vals['amount'] = total_amount-line_tot1
				line_id=self.env['od.contract.monthly.line'].create(line_vals)
				t_amount = t_amount+line_id.amount
				t_amount1 = t_amount1+line_id.amount
				next_month_start = period_start.replace(day=1)
				period_start = next_month_start+relativedelta(months=+1)
				period_start = period_start
				to_date_end_day=calendar.monthrange(period_start.year, period_start.month)[1]
				to_date=period_start.replace(day=to_date_end_day)
				period_end=to_date
			#check if the last line's period_to ==end_date, if not repeat once	
			if (line_id.period_to!=end_date):
				print("hereeeeeeeeeee",self.payment_line)
				period_end=end_date
				if period_start > end_date:
					period_start = next_month_start
				no_of_month_days = calendar.monthrange(period_start.year, period_start.month)[1]
				no_days = abs((period_end - period_start).days)+1
				# unit_price = self.contract_line_id.price_unit*self.contract_line_id.product_uom_qty
				unit_price = self.per_month

				# amount_to_invoice = (unit_price/no_of_month_days)*no_days
				amount_to_invoice = (unit_price/no_of_month_days)*no_of_month_days
				amount_to_invoice = amount_to_invoice * self.contract_id.od_exchange_rate #exchnge rate change

				line_vals={
				'service_id':self.id,
				'period_from':period_start,
				'period_to':period_end,
				'amount':amount_to_invoice,
				'invoiced':False,
				}
				line_tot=t_amount
				t_amount+=line_vals['amount']
				if self.payment_line:
					total_amount = 0
					for line in self.payment_line:
						total_amount+=line.amount
					total_amount = total_amount * self.contract_id.od_exchange_rate #exchnge rate change
					if period_end == end_date and t_amount != total_amount:
						line_vals['amount'] = total_amount-line_tot
				line_id=self.env['od.contract.monthly.line'].create(line_vals)
		else:
			if self.billing_cycle=='one_time':

				# commented on jan 24 2022, revenue lines need to be generated according to payments line
				# line_vals={
				# 'service_id':self.id,
				# 'period_from':period_start,
				# 'period_to':end_date,
				# 'amount':self.total_amount,
				# 'invoiced':False,
				# }
				# ~~~~ new changed added on jan 24 2022~~~~~~
				if len(self.payment_line)>1:
					to_date_end_day=calendar.monthrange(period_start.year, period_start.month)[1]
					to_date=period_start.replace(day=to_date_end_day)
					period_end=to_date
					while(period_end<=end_date):
						no_of_month_days = calendar.monthrange(period_start.year, period_start.month)[1]
						no_days = abs((period_end - period_start).days)+1
						unit_price = self.per_month
						# amount_to_invoice = (unit_price/no_of_month_days)*no_days
						amount_to_invoice = (unit_price/no_of_month_days)*no_of_month_days
						amount_to_invoice = amount_to_invoice * self.contract_id.od_exchange_rate #exchnge rate change

						line_vals={
						'service_id':self.id,
						'period_from':period_start,
						'period_to':period_end,
						'amount':amount_to_invoice,
						'invoiced':False,
						}
						if period_end == end_date:
							line_tot1=t_amount1
							t_amount1+=line_vals['amount']
							if self.payment_line:
								total_amount = 0
								for line in self.payment_line:
									total_amount+=line.amount
								total_amount = total_amount * self.contract_id.od_exchange_rate #exchnge rate change
								if period_end == end_date and t_amount1 != total_amount:
									line_vals['amount'] = total_amount-line_tot1
						line_id=self.env['od.contract.monthly.line'].create(line_vals)
						t_amount = t_amount+line_id.amount
						t_amount1 = t_amount1+line_id.amount
						next_month_start = period_start.replace(day=1)
						period_start = next_month_start+relativedelta(months=+1)
						period_start = period_start
						to_date_end_day=calendar.monthrange(period_start.year, period_start.month)[1]
						to_date=period_start.replace(day=to_date_end_day)
						period_end=to_date
					#check if the last line's period_to ==end_date, if not repeat once	
					if (line_id.period_to!=end_date):
						period_end=end_date
						if period_start > end_date:
							period_start = next_month_start
						no_of_month_days = calendar.monthrange(period_start.year, period_start.month)[1]
						no_days = abs((period_end - period_start).days)+1
						# unit_price = self.contract_line_id.price_unit*self.contract_line_id.product_uom_qty
						unit_price = self.per_month
						# amount_to_invoice = (unit_price/no_of_month_days)*no_days
						amount_to_invoice = (unit_price/no_of_month_days)*no_of_month_days
						amount_to_invoice = amount_to_invoice * self.contract_id.od_exchange_rate #exchnge rate change
						
						line_vals={
						'service_id':self.id,
						'period_from':period_start,
						'period_to':period_end,
						'amount':amount_to_invoice,
						'invoiced':False,
						}
						line_tot=t_amount
						t_amount+=line_vals['amount']
						if self.payment_line:
							total_amount = 0
							for line in self.payment_line:
								total_amount+=line.amount
							total_amount = total_amount * self.contract_id.od_exchange_rate #exchnge rate change
							if period_end == end_date and t_amount != total_amount:
								line_vals['amount'] = total_amount-line_tot
						line_id=self.env['od.contract.monthly.line'].create(line_vals)
				else:
					line_vals={
					'service_id':self.id,
					'period_from':period_start,
					'period_to':end_date,
					'amount':self.total_amount * self.contract_id.od_exchange_rate,#exchange rate change
					'invoiced':False,
					}
					line_id=self.env['od.contract.monthly.line'].create(line_vals)
				# ~~~~ new changed added end~~~~~~
			else:
				# generate revenue in firstmonth
				to_date_end_day=calendar.monthrange(period_start.year, period_start.month)[1]
				to_date=period_start.replace(day=to_date_end_day)
				period_end=to_date
				line_vals={
				'service_id':self.id,
				'period_from':period_start,
				'period_to':period_end,
				'amount':self.total_amount * self.contract_id.od_exchange_rate,#exchange rate change
				'invoiced':False,
				}
				# new change jan 24 2022 shifted tab in
				line_id=self.env['od.contract.monthly.line'].create(line_vals)
			# line_id=self.env['od.contract.monthly.line'].create(line_vals)
		
	# def generate_linesnew(self, start_date, end_date, period_start, frequency, months, amount_per_days, total_amount):
	# 	t_amount = 0
	# 	no_of_months = len(pd.date_range(start_date, end_date, freq='M'))
	# 	no_of_years = pd.date_range(start_date, end_date, freq='Y')
	# 	line_periods=[]
	# 	start_period = period_start
	# 	if frequency == 'Q':
	# 		quarters = pd.date_range(start_date, end_date, freq='Q')
	# 		no_of_quarters = len(quarters)
	# 		extra_months = abs((no_of_quarters*3)-no_of_months)
	# 		r_start_period=end_date
	# 		q_count=0
	# 		for qm in quarters:
	# 			q_count+=1
	# 			# print("starttttquarter",end_date,start_period.day!=1 and end_date.day not in (30,31,28,29))
	# 			# new code added for amount computation start
	# 			new_amount_to_invoice = 0
	# 			unit_price = self.contract_line_id.price_unit
	# 			# new code added for amount computation end

	# 			if start_period.day!=1 and end_date.day not in (30,31,28,29):
	# 				r_half_end = r_start_period+relativedelta(months=-3)
	# 				start_day=start_period.day
	# 				s_day=r_half_end.day+1
	# 				# print("sssssss",s_day,r_half_end)
	# 				# r_half_to_date=r_half_end.replace(day=(s_day))
	# 				try:
	# 					r_half_to_date=r_half_end.replace(day=(s_day))
	# 				except:
	# 					s_day=s_day-1
	# 					r_half_to_date=r_half_end.replace(day=(s_day))
	# 					r_half_to_date=r_half_end+relativedelta(day=+1)


	# 				if q_count == no_of_quarters:
	# 					# print("starttttttttttt",start_period)
	# 					r_half_to_date =start_period
	# 					# print("jjjjjjjjjkkkkkk",r_half_to_date)


	# 				# code added for amount computation
	# 				month_end_period = r_start_period
	# 				month_start_period = r_start_period+relativedelta(months=-1)
	# 				month_start_period = month_start_period + relativedelta(days=+1)
	# 				# print("b4 loop",month_start_period,month_end_period,r_start_period)
	# 				i = 0
	# 				condition=True
	# 				while (month_end_period <=r_start_period):
	# 					# i=i+1
	# 					# print("iiiiiii",i)
	# 					# print("month_start_period loopstart",month_start_period,month_end_period,r_start_period,r_half_to_date)
	# 					if month_start_period >= r_half_to_date:
	# 						# real_month_start = month_end_period- timedelta(days=month_end_period.day)+relativedelta(days=+1)
	# 						real_month_start = month_end_period+relativedelta(months=-1)
	# 						# print("mmmmmmmmmmm",real_month_start)
	# 						no_of_month_days = (month_end_period-real_month_start).days
	# 						# print("hhhhhhhhh",month_end_period,month_start_period,(month_end_period-month_start_period).days)
	# 						no_of_days_service_period = (month_end_period-month_start_period).days+1
	# 						new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 						# print("numberrrr",no_of_days_service_period,no_of_month_days,unit_price)
	# 						# print("per month",(unit_price/no_of_month_days)*no_of_days_service_period)
	# 						month_end_period = month_start_period+relativedelta(days=-1)
	# 						month_start_period = month_end_period+relativedelta(months=-1)
	# 						month_start_period = month_start_period+relativedelta(days=+1)
	# 						# print("month_start_period loopend",month_start_period,month_end_period,r_start_period,r_half_to_date)
	# 					elif q_count == no_of_quarters and condition:
	# 						month_start_period =r_half_to_date
	# 						condition=False
	# 					else:
	# 						break;
	# 				# new code added for amount computation end

				
	# 				vals={
	# 					'start_period' : r_half_to_date,
	# 					'end_period' : r_start_period,
	# 					'amount_to_invoice' : new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				# print("gggggggggggg",line_periods)
	# 				next_half_start = r_half_to_date
	# 				r_start_period = next_half_start+relativedelta(days=-1)
	# 				r_start_period = r_start_period

	# 			else:
	# 				r_half_end = r_start_period+relativedelta(months=-2)
	# 				# start_day=start_period.day
	# 				start_day=1
	# 				r_half_to_date=r_half_end.replace(day=start_day)
	# 				# print("hhhhhhhhhhhh",r_half_end,r_start_period,start_day,r_half_to_date)
	# 				if q_count == no_of_quarters:
	# 					# print("starttttttttttt",start_period)
	# 					r_half_to_date =start_period
	# 					# print("jjjjjjjjjkkkkkk",r_half_to_date)

					

	# 				# code added for amount computation
	# 				month_end_period = r_start_period
	# 				month_start_period = month_end_period.replace(day=1)
	# 				i = 0
	# 				condition=True
	# 				while (month_end_period <=r_start_period):
	# 					# i=i+1
	# 					# print("month_start_period loop start",month_start_period,month_end_period,r_start_period,r_half_to_date)
	# 					# print("ii",i)
	# 					if month_start_period >= r_half_to_date:
	# 						no_of_month_days = calendar.monthrange(month_start_period.year, month_start_period.month)[1]
	# 						no_of_days_service_period = (month_end_period-month_start_period).days+1
	# 						new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 						# print("per month",no_of_month_days,no_of_days_service_period,(unit_price/no_of_month_days)*no_of_days_service_period)
	# 						month_end_period = month_start_period+relativedelta(days=-1)
	# 						month_start_period = month_end_period.replace(day=1)
	# 						# print("month_start_period loop end",month_start_period,month_end_period,r_start_period,r_half_to_date)
	# 					elif q_count == no_of_quarters and condition:
	# 						month_start_period =r_half_to_date
	# 						condition=False
	# 					else:
	# 						break;
	# 				# new code added for amount computation end


	# 				vals={
	# 					'start_period' : r_half_to_date,
	# 					'end_period' : r_start_period,
	# 					'amount_to_invoice' : new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				# print("gggggggggggg",line_periods)
	# 				next_half_start = r_half_to_date
	# 				r_start_period = next_half_start+relativedelta(months=-1)
	# 				r_start_period = r_start_period
	# 				r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
	# 				r_start_period=r_start_period.replace(day=r_start_period_to_day)

	# 		# r_last_half_end_period = line_periods[(len(line_periods)-1)]
	# 		# print("extrrrrrrrrrrrr",extra_months,r_last_half_end_period)
	# 		# if extra_months and start_period != r_last_half_end_period['start_period']:
	# 		# 	extra_half_start = r_last_half_end_period['start_period']
	# 		# 	# extra_start_period = extra_half_start+relativedelta(months=-extra_months)
	# 		# 	extra_start_period = extra_half_start+relativedelta(days=-1)
	# 		# 	vals={
	# 		# 		'start_period' : start_period,
	# 		# 		'end_period' : extra_start_period
	# 		# 		}
	# 		# 	line_periods.append(vals)
	# 			# r_last_half_end_period['start_period']=start_period
	# 		line_periods.reverse()

	# 	if frequency == 'M':
	# 		monthly_months = pd.date_range(start_date, end_date, freq='M')
	# 		# print("mmhhhhh",monthly_months)
	# 		len_months = len(monthly_months)
	# 		# extra_months = abs((no_of_quarters*3)-no_of_months)
	# 		# print("kkkkkkkkkkkkkk",len_months)
	# 		m_count=0
	# 		for mm in monthly_months:
	# 			m_count+=1
	# 			# new code added for amount computation start
	# 			new_amount_to_invoice = 0
	# 			unit_price = self.contract_line_id.price_unit
	# 			# new code added for amount computation end

	# 			# print("qmmmmm",m_count)
	# 			no_of_month_days = calendar.monthrange(start_period.year, start_period.month)[1]
	# 			no_of_days_service_period = (mm.date()-start_period).days+1
	# 			new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 			vals={
	# 				'start_period' : start_period,
	# 				'end_period' : mm.date(),
	# 				'amount_to_invoice':new_amount_to_invoice,
	# 				}
	# 			line_periods.append(vals)
	# 			next_month_start = mm.replace(day=1)
	# 			start_period = next_month_start+relativedelta(months=+1)
	# 			start_period = start_period.date()

	# 			# print("starttttt",next_month_start,start_period)
	# 		# print("lennnnnnfff",len(line_periods))
	# 		# print("periooooo",line_periods)
	# 		last_month_end_period = line_periods[(len(line_periods)-1)]['end_period']
	# 		# if extra_months and end_date > last_quarter_end_period:
	# 		if end_date > last_month_end_period:
	# 			# last_quarter_end_period = line_periods[(len(line_periods)-1)]['end_period']
	# 			# print("oooooooo",last_month_end_period)
	# 			extra_month_start = last_month_end_period.replace(day=1)
	# 			extra_start_period = extra_month_start+relativedelta(months=+1)
	# 			no_of_month_days = calendar.monthrange(extra_start_period.year, extra_start_period.month)[1]
	# 			no_of_days_service_period = (end_date-extra_start_period).days+1
	# 			new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 			vals={
	# 				'start_period' : extra_start_period,
	# 				'end_period' : end_date,
	# 				'amount_to_invoice':new_amount_to_invoice,
	# 				}
	# 			line_periods.append(vals)


	# 	if frequency == 'H':
	# 		len_halfyears = len(no_of_years)*2
	# 		# print("noooooooooooooooo",no_of_years)
			
	# 		r_start_period=end_date
	# 		h_count=0
			

	# 		for mm in range(0,len_halfyears):
	# 			h_count+=1
	# 			# print("starttttquarter",end_date,start_period.day!=1 and end_date.day not in (30,31,28,29))
	# 			# new code added for amount computation start
	# 			new_amount_to_invoice = 0
	# 			unit_price = self.contract_line_id.price_unit
	# 			# new code added for amount computation end
	# 			if start_period.day!=1 and end_date.day not in (30,31,28,29):
	# 				r_half_end = r_start_period+relativedelta(months=-6)
	# 				start_day=start_period.day
	# 				s_day=r_half_end.day+1
	# 				# r_half_to_date=r_half_end.replace(day=(s_day))
	# 				try:
	# 					r_half_to_date=r_half_end.replace(day=(s_day))
	# 				except:
	# 					s_day=s_day-1
	# 					r_half_to_date=r_half_end.replace(day=(s_day))
	# 					r_half_to_date=r_half_end+relativedelta(day=+1)

	# 				if h_count==len_halfyears:
	# 					r_half_to_date =start_period

	# 				# code added for amount computation
	# 				month_end_period = r_start_period
	# 				month_start_period = r_start_period+relativedelta(months=-1)
	# 				month_start_period = month_start_period + relativedelta(days=+1)
	# 				# print("b4 loop",month_start_period,month_end_period,r_start_period)
	# 				i = 0
	# 				condition=True
	# 				while (month_end_period <=r_start_period):
	# 					# i=i+1
	# 					# print("iiiiiii",i)
	# 					# print("month_start_period loopstart",month_start_period,month_end_period,r_start_period,r_half_to_date)
	# 					if month_start_period >= r_half_to_date:
	# 						# real_month_start = month_end_period- timedelta(days=month_end_period.day)+relativedelta(days=+1)
	# 						real_month_start = month_end_period+relativedelta(months=-1)
	# 						# print("mmmmmmmmmmm",real_month_start)
	# 						no_of_month_days = (month_end_period-real_month_start).days
	# 						# print("hhhhhhhhh",month_end_period,month_start_period,(month_end_period-month_start_period).days)
	# 						no_of_days_service_period = (month_end_period-month_start_period).days+1
	# 						new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 						# print("numberrrr",no_of_days_service_period,no_of_month_days,unit_price)
	# 						# print("per month",(unit_price/no_of_month_days)*no_of_days_service_period)
	# 						month_end_period = month_start_period+relativedelta(days=-1)
	# 						month_start_period = month_end_period+relativedelta(months=-1)
	# 						month_start_period = month_start_period+relativedelta(days=+1)
	# 						# print("month_start_period loopend",month_start_period,month_end_period,r_start_period,r_half_to_date)
	# 					elif h_count == len_halfyears and condition:
	# 						month_start_period =r_half_to_date
	# 						condition=False
	# 					else:
	# 						break;
	# 				# new code added for amount computation end	
					
	# 				vals={
	# 					'start_period' : r_half_to_date,
	# 					'end_period' : r_start_period,
	# 					'amount_to_invoice' : new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				# print("gggggggggggg",line_periods)
	# 				next_half_start = r_half_to_date
	# 				r_start_period = next_half_start+relativedelta(days=-1)
	# 				r_start_period = r_start_period
	# 			else:
	# 				r_half_end = r_start_period+relativedelta(months=-5)
	# 				# start_day=start_period.day
	# 				start_day=1
	# 				r_half_to_date=r_half_end.replace(day=start_day)
	# 				if h_count == len_halfyears:
	# 					# print("starttttttttttt",start_period)
	# 					r_half_to_date =start_period
	# 					# print("jjjjjjjjjkkkkkk",r_half_to_date)



	# 				# code added for amount computation
	# 				month_end_period = r_start_period
	# 				month_start_period = month_end_period.replace(day=1)
	# 				i = 0
	# 				condition=True
	# 				while (month_end_period <=r_start_period):
	# 					# i=i+1
	# 					# print("month_start_period loop start",month_start_period,month_end_period,r_start_period,r_half_to_date)
	# 					# print("ii",i)
	# 					if month_start_period >= r_half_to_date:
	# 						no_of_month_days = calendar.monthrange(month_start_period.year, month_start_period.month)[1]
	# 						no_of_days_service_period = (month_end_period-month_start_period).days+1
	# 						new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 						# print("per month",no_of_month_days,no_of_days_service_period,(unit_price/no_of_month_days)*no_of_days_service_period)
	# 						month_end_period = month_start_period+relativedelta(days=-1)
	# 						month_start_period = month_end_period.replace(day=1)
	# 						# print("month_start_period loop end",month_start_period,month_end_period,r_start_period,r_half_to_date)
	# 					elif h_count == len_halfyears and condition:
	# 						# print("/eliffffffffff",h_count,len_halfyears)
	# 						month_start_period =r_half_to_date
	# 						condition=False
	# 					else:
	# 						break;
	# 				# new code added for amount computation end

	# 				vals={
	# 					'start_period' : r_half_to_date,
	# 					'end_period' : r_start_period,
	# 					'amount_to_invoice' : new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				# print("gggggggggggg",line_periods)
	# 				next_half_start = r_half_to_date
	# 				r_start_period = next_half_start+relativedelta(months=-1)
	# 				r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
	# 				r_start_period=r_start_period.replace(day=r_start_period_to_day)
	# 				r_start_period = r_start_period
			
	# 		# r_last_half_end_period = line_periods[(len(line_periods)-1)]
	# 		# if start_period > r_last_half_end_period['start_period']:
	# 		# 	# extra_half_start = last_half_end_period.replace(day=1)
	# 		# 	# extra_start_period = extra_half_start+relativedelta(months=+1)
	# 		# 	# vals={
	# 		# 	# 	'start_period' : extra_start_period,
	# 		# 	# 	'end_period' : end_date
	# 		# 	# 	}
	# 		# 	# line_periods.append(vals)
	# 		# 	r_last_half_end_period['start_period']=start_period
	# 		line_periods.reverse()
	# 		# print("plasssss",line_periods)

	# 	if frequency == 'Y':
	# 		# for mm in no_of_years:
	# 		# 	vals={
	# 		# 		'start_period' : start_period,
	# 		# 		'end_period' : mm.date()
	# 		# 		}
	# 		# 	line_periods.append(vals)
	# 		# 	next_year_start = mm.replace(day=1)
	# 		# 	start_period = next_year_start+relativedelta(months=+1)
	# 		# 	start_period = start_period.date()
	# 		# last_year_end_period = line_periods[(len(line_periods)-1)]['end_period']
	# 		# if end_date > last_year_end_period:
	# 		# 	extra_year_start = last_year_end_period.replace(day=1)
	# 		# 	extra_start_period = extra_year_start+relativedelta(months=+1)
	# 		# 	vals={
	# 		# 		'start_period' : extra_start_period,
	# 		# 		'end_period' : end_date
	# 		# 		}
	# 		# 	line_periods.append(vals)
	# 		new_no_of_years = no_of_months/12
	# 		# print("jjjjjjjjjj",new_no_of_years,new_no_of_years>int(new_no_of_years))
	# 		if new_no_of_years>int(new_no_of_years):
	# 			new_no_of_years = int(new_no_of_years)+1
	# 		else:
	# 			new_no_of_years = int(new_no_of_years)


	# 		yr_start_period = start_period

	# 		for mm in range(0,new_no_of_years):
	# 			yr_end_period = yr_start_period+relativedelta(months=+12)
	# 			yr_end_period = yr_end_period+relativedelta(days=-1)
	# 			new_amount_to_invoice =self.contract_line_id.price_unit
	# 			if (mm+1)==new_no_of_years:
	# 				yr_end_period=end_date

	# 			vals={
	# 				'start_period' : yr_start_period,
	# 				'end_period' : yr_end_period,
	# 				'amount_to_invoice' : new_amount_to_invoice,
	# 				}
	# 			line_periods.append(vals)
	# 			next_year_start = yr_end_period+relativedelta(days=+1)
	# 			yr_start_period = next_year_start
	# 			# start_period = next_year_start+relativedelta(months=+1)
	# 			# start_period = start_period.date()
	# 		# last_year_end_period = line_periods[(len(line_periods)-1)]['end_period']
	# 		# if end_date > last_year_end_period:
	# 		# 	extra_year_start = last_year_end_period.replace(day=1)
	# 		# 	extra_start_period = extra_year_start+relativedelta(months=+1)
	# 		# 	vals={
	# 		# 		'start_period' : extra_start_period,
	# 		# 		'end_period' : end_date
	# 		# 		}
	# 		# 	line_periods.append(vals)


	# 	# new
	# 	count=0
	# 	for p in line_periods:
	# 		count=count+1
	# 		# print("counttttttt",count)
	# 		period_start=p['start_period']
	# 		period_end=p['end_period']
	# 		no_days = abs((period_end - period_start).days)+1
	# 		# amount_to_invoice = no_days*amount_per_days
	# 		amount_to_invoice = p['amount_to_invoice']
	# 		line_vals={
	# 		'service_id':self.id,
	# 		'period_from':period_start,
	# 		'period_to':period_end,
	# 		'amount':amount_to_invoice,
	# 		'invoiced':False,
	# 		# 'pending_amount':amount_to_invoice,
	# 		}
	# 		if period_end == end_date and t_amount < total_amount:
	# 			line_vals['amount'] = total_amount-t_amount
	# 		# for special case, we have to update the amount for first period line from already made invoice 
	# 		if self.contract_line_id.state=='0_draft' and len(self.contract_line_id.invoice_line_ids)==1 and count==1:
	# 			line_vals['amount'] = self.contract_line_id.invoice_line_ids[0].price_total
	# 			line_vals['invoiced'] = True
	# 			line_vals['invoice_line_id'] = self.contract_line_id.invoice_line_ids[0].id
			
	# 		line_id=self.env['od.contract.payment.line'].create(line_vals)
	# 		t_amount = t_amount+line_id.amount
	# 		# print("kgffffffffff",t_amount)

	# def find_number_of_months(self,start_date,end_date):
	# 	# start_months=pd.date_range(start_date, end_date, freq='MS')
	# 	# end_months=pd.date_range(start_date, end_date, freq='M')
	# 	# months_all =[]
	# 	# months =[]
	# 	# for date in start_months:
	# 	# 	yr_month=str(date.month)+"-"+str(date.year)
	# 	# 	months_all.append(yr_month)
	# 	# for date in end_months:
	# 	# 	yr_month=str(date.month)+"-"+str(date.year)
	# 	# 	months_all.append(yr_month)
	# 	# 	date=date.date()
	# 	# 	months.append(str(date))
	# 	# months_all = list(set(months_all))


	# 	# newcode
	# 	end_months=pd.date_range(start_date, end_date, freq='M')
	# 	months_all =[]
	# 	for date in end_months:
	# 		date=date.date()
	# 		months_all.append(str(date))
	# 	months_all = list(set(months_all))
	# 	if str(end_date) not in months_all:
	# 		months_all.append(str(end_date))
	# 	print("monmthssss",months_all)

	# 	return len(months_all)

	# def find_number_of_quarters(self,start_date,end_date):
	# 	no_of_months = self.find_number_of_months(start_date,end_date)
	# 	return math.ceil(no_of_months*(1/3))

	# #------ correct as on 4 nov 2021
	# def generate_linesnew(self, start_date, end_date, period_start, frequency, months, amount_per_days, total_amount):
	# 	t_amount = 0
	# 	no_of_months = len(pd.date_range(start_date, end_date, freq='M'))#only take if month end date 30 or 31
	# 	no_of_years = pd.date_range(start_date, end_date, freq='Y')
	# 	line_periods=[]
	# 	start_period = period_start
	# 	if frequency == 'Q':
	# 		no_of_quarters=math.ceil(no_of_months*(1/3))
	# 		extra_months = abs((no_of_quarters*3)-no_of_months)
	# 		r_start_period=end_date
	# 		q_count=0
	# 		real_q_count =0
	# 		for qm in range(0,no_of_quarters):
	# 			real_q_count+=1
	# 			diff_month=3 if not self.contract_line_id.line_regular else 2
	# 			r_end_period = r_start_period-relativedelta(months=diff_month)
	# 			s_day=start_period.day
	# 			if not self.contract_line_id.line_regular:
	# 				s_day=r_end_period.day+1
	# 			try:
	# 				r_next_end_period=r_end_period.replace(day=(s_day))
	# 			except:
	# 				s_day=s_day-1
	# 				r_next_end_period=r_end_period.replace(day=(s_day))
	# 				r_next_end_period=r_end_period+relativedelta(day=+1)

	# 			if real_q_count==no_of_quarters:
	# 				if start_date < r_next_end_period:
	# 					real_q_count+=1
	# 			r_next_start_period = r_next_end_period
	# 			if  not self.contract_line_id.line_regular:
	# 				r_start_period = r_next_start_period+relativedelta(days=-1)
	# 			else:
	# 				r_start_period = r_next_start_period+relativedelta(months=-1)
	# 				r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
	# 				r_start_period=r_start_period.replace(day=r_start_period_to_day)
	# 			r_start_period = r_start_period

	# 		r_start_period = end_date
	# 		month_ls = []

	# 		for qm in range(0,real_q_count):
	# 			q_count+=1
	# 			# new code added for amount computation start
	# 			new_amount_to_invoice = 0
	# 			unit_price = self.per_month
	# 			# new code added for amount computation end
	# 			if not self.contract_line_id.line_regular:#this has been changed since the contract can start from any date including the month end. so had to change this by considering feb month case also
	# 				r_half_end = r_start_period+relativedelta(months=-3)
	# 				start_day=start_period.day
	# 				s_day=r_half_end.day+1
	# 				try:
	# 					r_half_to_date=r_half_end.replace(day=(s_day))
	# 				except:
	# 					s_day=s_day-1
	# 					r_half_to_date=r_half_end.replace(day=(s_day))
	# 					if r_half_end.month!=2:
	# 						r_half_to_date=r_half_end+relativedelta(day=+1)

	# 				if q_count == real_q_count:
	# 					r_half_to_date =start_period
	# 				# code added for amount computation
	# 				month_end_period = r_start_period
	# 				month_start_period = r_start_period+relativedelta(months=-1)
	# 				month_start_period = month_start_period + relativedelta(days=+1)
	# 				i = 0
	# 				condition=True
	# 				while (month_end_period <=r_start_period):
	# 					if month_start_period >= r_half_to_date:
	# 						real_month_start = month_end_period+relativedelta(months=-1)
	# 						no_of_month_days = (month_end_period-real_month_start).days
	# 						no_of_days_service_period = (month_end_period-month_start_period).days+1
	# 						new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 						month_end_period = month_start_period+relativedelta(days=-1)
	# 						month_start_period = month_end_period+relativedelta(months=-1)
	# 						month_start_period = month_start_period+relativedelta(days=+1)
	# 					elif q_count == real_q_count and condition:
	# 						month_start_period =r_half_to_date
	# 						condition=False
	# 					else:
	# 						break;
	# 				# new code added for amount computation end
	# 				vals={
	# 					'start_period' : r_half_to_date,
	# 					'end_period' : r_start_period,
	# 					'amount_to_invoice' : new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				next_half_start = r_half_to_date
	# 				r_start_period = next_half_start+relativedelta(days=-1)
	# 				r_start_period = r_start_period
	# 			else:
	# 				r_half_end = r_start_period+relativedelta(months=-2)
	# 				start_day=1
	# 				r_half_to_date=r_half_end.replace(day=start_day)
	# 				if q_count == real_q_count:
	# 					r_half_to_date =start_period

	# 				# code added for amount computation
	# 				month_end_period = r_start_period
	# 				month_start_period = month_end_period.replace(day=1)
	# 				i = 0
	# 				condition=True
	# 				while (month_end_period <=r_start_period):
	# 					if month_start_period >= r_half_to_date:
	# 						no_of_month_days = calendar.monthrange(month_start_period.year, month_start_period.month)[1]
	# 						no_of_days_service_period = (month_end_period-month_start_period).days+1
	# 						new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 						month_end_period = month_start_period+relativedelta(days=-1)
	# 						month_start_period = month_end_period.replace(day=1)
	# 					elif q_count == real_q_count and condition:
	# 						month_start_period =r_half_to_date
	# 						condition=False
	# 					else:
	# 						break;
	# 				# new code added for amount computation end
	# 				vals={
	# 					'start_period' : r_half_to_date,
	# 					'end_period' : r_start_period,
	# 					'amount_to_invoice' : new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				next_half_start = r_half_to_date
	# 				r_start_period = next_half_start+relativedelta(months=-1)
	# 				r_start_period = r_start_period
	# 				r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
	# 				r_start_period=r_start_period.replace(day=r_start_period_to_day)
	# 		line_periods.reverse()
	# 	#------ correct as on 4 nov 2021
	# 	if frequency == 'M':
	# 		monthly_months = pd.date_range(start_date, end_date, freq='M')
	# 		len_months = len(monthly_months)
	# 		m_count=0
	# 		if not self.contract_line_id.line_regular:
	# 			r_start_period=end_date
	# 			# to get correct count
	# 			real_count=0
	# 			for mm in monthly_months:
	# 				real_count+=1
	# 				r_end_period = r_start_period+relativedelta(months=-1)
	# 				r_end_period = r_end_period + relativedelta(days=+1)
	# 				if real_count==no_of_months:
	# 					if start_period < r_end_period:
	# 						real_count+=1
	# 				r_start_period = r_end_period+relativedelta(days=-1)
	# 			r_start_period=end_date
	# 			for mm in range(0,real_count):
	# 				m_count+=1
	# 				# new code added for amount computation start
	# 				new_amount_to_invoice = 0
	# 				unit_price = self.per_month
	# 				# new code added for amount computation end
	# 				r_end_period = r_start_period+relativedelta(months=-1)
	# 				r_end_period = r_end_period + relativedelta(days=+1)
	# 				if m_count==real_count:
	# 					r_end_period=start_period
	# 				real_month_start = r_start_period+relativedelta(months=-1)
	# 				no_of_month_days = (r_start_period-real_month_start).days
	# 				no_of_days_service_period = (r_start_period-r_end_period).days+1
	# 				new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
					
	# 				vals={
	# 					'start_period' : r_end_period,
	# 					'end_period' : r_start_period,
	# 					'amount_to_invoice':new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				r_start_period = r_end_period+relativedelta(days=-1)
	# 			line_periods.reverse()
	# 		else:
	# 			for mm in monthly_months:
	# 				m_count+=1
	# 				# new code added for amount computation start
	# 				new_amount_to_invoice = 0
	# 				unit_price = self.per_month
	# 				# new code added for amount computation end
	# 				no_of_month_days = calendar.monthrange(start_period.year, start_period.month)[1]
	# 				no_of_days_service_period = (mm.date()-start_period).days+1
	# 				new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 				vals={
	# 					'start_period' : start_period,
	# 					'end_period' : mm.date(),
	# 					'amount_to_invoice':new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				next_month_start = mm.replace(day=1)
	# 				start_period = next_month_start+relativedelta(months=+1)
	# 				start_period = start_period.date()
	# 			last_month_end_period = line_periods[(len(line_periods)-1)]['end_period']
	# 			if end_date > last_month_end_period:
	# 				extra_month_start = last_month_end_period.replace(day=1)
	# 				extra_start_period = extra_month_start+relativedelta(months=+1)
	# 				no_of_month_days = calendar.monthrange(extra_start_period.year, extra_start_period.month)[1]
	# 				no_of_days_service_period = (end_date-extra_start_period).days+1
	# 				new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 				vals={
	# 					'start_period' : extra_start_period,
	# 					'end_period' : end_date,
	# 					'amount_to_invoice':new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)

	# 	#------ correct as on 4 nov 2021
	# 	if frequency == 'H':
	# 		new_no_of_years = no_of_months/6
	# 		if new_no_of_years>int(new_no_of_years):
	# 			new_no_of_years = int(new_no_of_years)+1
	# 		else:
	# 			new_no_of_years = int(new_no_of_years)
			
	# 		len_halfyears = new_no_of_years
	# 		print ("halffffffffffffff",len_halfyears,new_no_of_years)
	# 		# print (s)
	# 		r_start_period=end_date
	# 		h_count=0
	# 		real_h_count =0
	# 		for qm in range(0,len_halfyears):
	# 			real_h_count+=1
	# 			diff_month=6 if not self.contract_line_id.line_regular else 5
	# 			r_end_period = r_start_period-relativedelta(months=diff_month)
	# 			s_day=start_period.day
	# 			if not self.contract_line_id.line_regular:
	# 				s_day=r_end_period.day+1
	# 			try:
	# 				r_next_end_period=r_end_period.replace(day=(s_day))
	# 			except:
	# 				s_day=s_day-1
	# 				r_next_end_period=r_end_period.replace(day=(s_day))
	# 				r_next_end_period=r_end_period+relativedelta(day=+1)

	# 			if real_h_count==len_halfyears:
	# 				if start_date < r_next_end_period:
	# 					real_h_count+=1
	# 			r_next_start_period = r_next_end_period
	# 			if not self.contract_line_id.line_regular:
	# 				r_start_period = r_next_start_period+relativedelta(days=-1)
	# 			else:
	# 				r_start_period = r_next_start_period+relativedelta(months=-1)
	# 				r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
	# 				r_start_period=r_start_period.replace(day=r_start_period_to_day)
	# 			r_start_period = r_start_period

	# 		r_start_period=end_date
	# 		for mm in range(0,real_h_count):
	# 			h_count+=1
	# 			new_amount_to_invoice = 0
	# 			unit_price = self.per_month
	# 			if not self.contract_line_id.line_regular:
	# 				r_half_end = r_start_period+relativedelta(months=-6)
	# 				start_day=start_period.day
	# 				s_day=r_half_end.day+1
	# 				try:
	# 					r_half_to_date=r_half_end.replace(day=(s_day))
	# 				except:
	# 					s_day=s_day-1
	# 					r_half_to_date=r_half_end.replace(day=(s_day))
	# 					if r_half_end.month!=2:
	# 						r_half_to_date=r_half_end+relativedelta(day=+1)

	# 				if h_count==real_h_count:
	# 					r_half_to_date =start_period
	# 				# code added for amount computation
	# 				month_end_period = r_start_period
	# 				month_start_period = r_start_period+relativedelta(months=-1)
	# 				month_start_period = month_start_period + relativedelta(days=+1)
	# 				i = 0
	# 				condition=True
	# 				while (month_end_period <=r_start_period):
	# 					if month_start_period >= r_half_to_date:
	# 						real_month_start = month_end_period+relativedelta(months=-1)
	# 						no_of_month_days = (month_end_period-real_month_start).days
	# 						no_of_days_service_period = (month_end_period-month_start_period).days+1
	# 						new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 						month_end_period = month_start_period+relativedelta(days=-1)
	# 						month_start_period = month_end_period+relativedelta(months=-1)
	# 						month_start_period = month_start_period+relativedelta(days=+1)
	# 					elif h_count == real_h_count and condition:
	# 						month_start_period =r_half_to_date
	# 						condition=False
	# 					else:
	# 						break;
	# 				# new code added for amount computation end	
	# 				vals={
	# 					'start_period' : r_half_to_date,
	# 					'end_period' : r_start_period,
	# 					'amount_to_invoice' : new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				next_half_start = r_half_to_date
	# 				r_start_period = next_half_start+relativedelta(days=-1)
	# 				r_start_period = r_start_period
	# 			else:
	# 				r_half_end = r_start_period+relativedelta(months=-5)
	# 				start_day=1
	# 				r_half_to_date=r_half_end.replace(day=start_day)
	# 				if h_count == real_h_count:
	# 					r_half_to_date =start_period
	# 				# code added for amount computation
	# 				month_end_period = r_start_period
	# 				month_start_period = month_end_period.replace(day=1)
	# 				i = 0
	# 				condition=True
	# 				while (month_end_period <=r_start_period):
	# 					if month_start_period >= r_half_to_date:
	# 						no_of_month_days = calendar.monthrange(month_start_period.year, month_start_period.month)[1]
	# 						no_of_days_service_period = (month_end_period-month_start_period).days+1
	# 						new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
	# 						month_end_period = month_start_period+relativedelta(days=-1)
	# 						month_start_period = month_end_period.replace(day=1)
	# 					elif h_count == real_h_count and condition:
	# 						month_start_period =r_half_to_date
	# 						condition=False
	# 					else:
	# 						break;
	# 				# new code added for amount computation end
	# 				vals={
	# 					'start_period' : r_half_to_date,
	# 					'end_period' : r_start_period,
	# 					'amount_to_invoice' : new_amount_to_invoice,
	# 					}
	# 				line_periods.append(vals)
	# 				next_half_start = r_half_to_date
	# 				r_start_period = next_half_start+relativedelta(months=-1)
	# 				r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
	# 				r_start_period=r_start_period.replace(day=r_start_period_to_day)
	# 				r_start_period = r_start_period
	# 		line_periods.reverse()
	# 	#------ correct as on 4 nov 2021
	# 	if frequency == 'Y':
	# 		new_no_of_years = no_of_months/12
	# 		if new_no_of_years>int(new_no_of_years):
	# 			new_no_of_years = int(new_no_of_years)+1
	# 		else:
	# 			new_no_of_years = int(new_no_of_years)
	# 		yr_start_period = start_period
	# 		for mm in range(0,new_no_of_years):
	# 			yr_end_period = yr_start_period+relativedelta(months=+12)
	# 			yr_end_period = yr_end_period+relativedelta(days=-1)
	# 			new_amount_to_invoice =(self.contract_line_id.price_subtotal)/new_no_of_years
	# 			if (mm+1)==new_no_of_years:
	# 				yr_end_period=end_date
	# 			vals={
	# 				'start_period' : yr_start_period,
	# 				'end_period' : yr_end_period,
	# 				'amount_to_invoice' : new_amount_to_invoice,
	# 				}
	# 			line_periods.append(vals)
	# 			next_year_start = yr_end_period+relativedelta(days=+1)
	# 			yr_start_period = next_year_start
	# 	#------ correct as on 4 nov 2021

	# 	# new
	# 	count=0
	# 	for p in line_periods:
	# 		count=count+1
	# 		# print("counttttttt",count)
	# 		period_start=p['start_period']
	# 		period_end=p['end_period']
	# 		no_days = abs((period_end - period_start).days)+1
	# 		# amount_to_invoice = no_days*amount_per_days
	# 		amount_to_invoice = p['amount_to_invoice']
	# 		line_vals={
	# 		'service_id':self.id,
	# 		'period_from':period_start,
	# 		'period_to':period_end,
	# 		'amount':amount_to_invoice,
	# 		'invoiced':False,
	# 		# 'pending_amount':amount_to_invoice,
	# 		}
	# 		# commented here on oct12 2021 waiting for them to report
	# 		# if period_end == end_date and t_amount < total_amount:
	# 			# line_vals['amount'] = total_amount-t_amount
	# 		# commented here on oct12 2021 waiting for them to report endddd

	# 		# added since if there is minimum 90days for quarter,per month*3 is correct.
	# 		if frequency=='Q':
	# 			q_days=(period_end-period_start).days+1
	# 			print("q_daysssss",q_days)
	# 			if q_days>=89:
	# 				line_vals['amount'] = self.per_month*3
	# 			elif q_days>=58:
	# 				line_vals['amount'] = self.per_month*2
	# 			elif q_days>=28:
	# 				line_vals['amount'] = self.per_month
	# 		if frequency=='M':
	# 			m_days=(period_end-period_start).days+1
	# 			if m_days>=28:
	# 				line_vals['amount'] = self.per_month
	# 		if frequency=='H':
	# 			h_days=(period_end-period_start).days+1
	# 			print("hhhh",h_days)
	# 			if h_days>=180:
	# 				line_vals['amount'] = self.per_month*6
	# 			elif h_days>=150:
	# 				line_vals['amount'] = self.per_month*5
	# 			elif h_days>=120:
	# 				line_vals['amount'] = self.per_month*4
	# 			elif h_days>=90:
	# 				line_vals['amount'] = self.per_month*3
	# 			elif h_days>=58:
	# 				line_vals['amount'] = self.per_month*2
	# 			elif h_days>=28:
	# 				line_vals['amount'] = self.per_month





	# 		# for special case, we have to update the amount for first period line from already made invoice 
	# 		if self.contract_line_id.state=='0_draft' and len(self.contract_line_id.invoice_line_ids)==1 and count==1:
	# 			line_vals['amount'] = self.contract_line_id.invoice_line_ids[0].price_subtotal
	# 			line_vals['invoiced'] = True
	# 			line_vals['invoice_line_id'] = self.contract_line_id.invoice_line_ids[0].id
			
	# 		line_id=self.env['od.contract.payment.line'].create(line_vals)
	# 		t_amount = t_amount+line_id.amount
	# 		# print("kgffffffffff",t_amount)


	# new function as on july 2023

	#------ correct as on 4 nov 2021
	def generate_linesnew(self, start_date, end_date, period_start, frequency, months, amount_per_days, total_amount):
		t_amount = 0
		no_of_months = len(pd.date_range(start_date, end_date, freq='M'))#only take if month end date 30 or 31
		no_of_years = pd.date_range(start_date, end_date, freq='Y')
		line_periods=[]
		start_period = period_start
		if frequency == 'Q':
			no_of_quarters=math.ceil(no_of_months*(1/3))
			extra_months = abs((no_of_quarters*3)-no_of_months)
			r_start_period=end_date
			q_count=0
			real_q_count =0
			for qm in range(0,no_of_quarters):
				real_q_count+=1
				diff_month=3 if not self.contract_line_id.line_regular else 2
				r_end_period = r_start_period-relativedelta(months=diff_month)
				s_day=start_period.day
				if not self.contract_line_id.line_regular:
					s_day=r_end_period.day+1
				try:
					r_next_end_period=r_end_period.replace(day=(s_day))
				except:
					s_day=s_day-1
					r_next_end_period=r_end_period.replace(day=(s_day))
					r_next_end_period=r_end_period+relativedelta(day=+1)

				if real_q_count==no_of_quarters:
					if start_date < r_next_end_period:
						real_q_count+=1
				r_next_start_period = r_next_end_period
				if  not self.contract_line_id.line_regular:
					r_start_period = r_next_start_period+relativedelta(days=-1)
				else:
					r_start_period = r_next_start_period+relativedelta(months=-1)
					r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
					r_start_period=r_start_period.replace(day=r_start_period_to_day)
				r_start_period = r_start_period

			r_start_period = end_date
			month_ls = []

			for qm in range(0,real_q_count):
				q_count+=1
				# new code added for amount computation start
				new_amount_to_invoice = 0
				unit_price = self.per_month
				# new code added for amount computation end
				if not self.contract_line_id.line_regular:#this has been changed since the contract can start from any date including the month end. so had to change this by considering feb month case also
					r_half_end = r_start_period+relativedelta(months=-3)
					start_day=start_period.day
					s_day=r_half_end.day+1
					try:
						r_half_to_date=r_half_end.replace(day=(s_day))
					except:
						s_day=s_day-1
						r_half_to_date=r_half_end.replace(day=(s_day))
						if r_half_end.month!=2:
							r_half_to_date=r_half_end+relativedelta(day=+1)

					if q_count == real_q_count:
						r_half_to_date =start_period
					# code added for amount computation
					month_end_period = r_start_period
					month_start_period = r_start_period+relativedelta(months=-1)
					month_start_period = month_start_period + relativedelta(days=+1)
					i = 0
					condition=True
					while (month_end_period <=r_start_period):
						if month_start_period >= r_half_to_date:
							real_month_start = month_end_period+relativedelta(months=-1)
							no_of_month_days = (month_end_period-real_month_start).days
							no_of_days_service_period = (month_end_period-month_start_period).days+1
							# new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
							new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_month_days
							month_end_period = month_start_period+relativedelta(days=-1)
							month_start_period = month_end_period+relativedelta(months=-1)
							month_start_period = month_start_period+relativedelta(days=+1)
						elif q_count == real_q_count and condition:
							month_start_period =r_half_to_date
							condition=False
						else:
							break;
					# new code added for amount computation end
					vals={
						'start_period' : r_half_to_date,
						'end_period' : r_start_period,
						'amount_to_invoice' : new_amount_to_invoice,
						}
					line_periods.append(vals)
					next_half_start = r_half_to_date
					r_start_period = next_half_start+relativedelta(days=-1)
					r_start_period = r_start_period
				else:
					r_half_end = r_start_period+relativedelta(months=-2)
					start_day=1
					r_half_to_date=r_half_end.replace(day=start_day)
					if q_count == real_q_count:
						r_half_to_date =start_period

					# code added for amount computation
					month_end_period = r_start_period
					month_start_period = month_end_period.replace(day=1)
					i = 0
					condition=True
					while (month_end_period <=r_start_period):
						if month_start_period >= r_half_to_date:
							no_of_month_days = calendar.monthrange(month_start_period.year, month_start_period.month)[1]
							no_of_days_service_period = (month_end_period-month_start_period).days+1
							# new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
							new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_month_days
							month_end_period = month_start_period+relativedelta(days=-1)
							month_start_period = month_end_period.replace(day=1)
						elif q_count == real_q_count and condition:
							month_start_period =r_half_to_date
							condition=False
						else:
							break;
					# new code added for amount computation end
					vals={
						'start_period' : r_half_to_date,
						'end_period' : r_start_period,
						'amount_to_invoice' : new_amount_to_invoice,
						}
					line_periods.append(vals)
					next_half_start = r_half_to_date
					r_start_period = next_half_start+relativedelta(months=-1)
					r_start_period = r_start_period
					r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
					r_start_period=r_start_period.replace(day=r_start_period_to_day)
			line_periods.reverse()
		#------ correct as on 4 nov 2021
		if frequency == 'M':
			monthly_months = pd.date_range(start_date, end_date, freq='M')
			len_months = len(monthly_months)
			m_count=0
			if not self.contract_line_id.line_regular:
				r_start_period=end_date
				# to get correct count
				real_count=0
				for mm in monthly_months:
					real_count+=1
					r_end_period = r_start_period+relativedelta(months=-1)
					r_end_period = r_end_period + relativedelta(days=+1)
					if real_count==no_of_months:
						if start_period < r_end_period:
							real_count+=1
					r_start_period = r_end_period+relativedelta(days=-1)
				r_start_period=end_date
				for mm in range(0,real_count):
					m_count+=1
					# new code added for amount computation start
					new_amount_to_invoice = 0
					unit_price = self.per_month
					# new code added for amount computation end
					r_end_period = r_start_period+relativedelta(months=-1)
					r_end_period = r_end_period + relativedelta(days=+1)
					if m_count==real_count:
						r_end_period=start_period
					real_month_start = r_start_period+relativedelta(months=-1)
					no_of_month_days = (r_start_period-real_month_start).days
					no_of_days_service_period = (r_start_period-r_end_period).days+1
					# new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
					new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_month_days
					
					vals={
						'start_period' : r_end_period,
						'end_period' : r_start_period,
						'amount_to_invoice':new_amount_to_invoice,
						}
					line_periods.append(vals)
					r_start_period = r_end_period+relativedelta(days=-1)
				line_periods.reverse()
			else:
				for mm in monthly_months:
					m_count+=1
					# new code added for amount computation start
					new_amount_to_invoice = 0
					unit_price = self.per_month
					# new code added for amount computation end
					no_of_month_days = calendar.monthrange(start_period.year, start_period.month)[1]
					no_of_days_service_period = (mm.date()-start_period).days+1
					# new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
					new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_month_days
					vals={
						'start_period' : start_period,
						'end_period' : mm.date(),
						'amount_to_invoice':new_amount_to_invoice,
						}
					line_periods.append(vals)
					next_month_start = mm.replace(day=1)
					start_period = next_month_start+relativedelta(months=+1)
					start_period = start_period.date()
				last_month_end_period = line_periods[(len(line_periods)-1)]['end_period']
				if end_date > last_month_end_period:
					extra_month_start = last_month_end_period.replace(day=1)
					extra_start_period = extra_month_start+relativedelta(months=+1)
					no_of_month_days = calendar.monthrange(extra_start_period.year, extra_start_period.month)[1]
					no_of_days_service_period = (end_date-extra_start_period).days+1
					# new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
					new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_month_days
					vals={
						'start_period' : extra_start_period,
						'end_period' : end_date,
						'amount_to_invoice':new_amount_to_invoice,
						}
					line_periods.append(vals)

		#------ correct as on 4 nov 2021
		if frequency == 'H':
			new_no_of_years = no_of_months/6
			if new_no_of_years>int(new_no_of_years):
				new_no_of_years = int(new_no_of_years)+1
			else:
				new_no_of_years = int(new_no_of_years)
			
			len_halfyears = new_no_of_years
			print ("halffffffffffffff",len_halfyears,new_no_of_years)
			# print (s)
			r_start_period=end_date
			h_count=0
			real_h_count =0
			for qm in range(0,len_halfyears):
				real_h_count+=1
				diff_month=6 if not self.contract_line_id.line_regular else 5
				r_end_period = r_start_period-relativedelta(months=diff_month)
				s_day=start_period.day
				if not self.contract_line_id.line_regular:
					s_day=r_end_period.day+1
				try:
					r_next_end_period=r_end_period.replace(day=(s_day))
				except:
					s_day=s_day-1
					r_next_end_period=r_end_period.replace(day=(s_day))
					r_next_end_period=r_end_period+relativedelta(day=+1)

				if real_h_count==len_halfyears:
					if start_date < r_next_end_period:
						real_h_count+=1
				r_next_start_period = r_next_end_period
				if not self.contract_line_id.line_regular:
					r_start_period = r_next_start_period+relativedelta(days=-1)
				else:
					r_start_period = r_next_start_period+relativedelta(months=-1)
					r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
					r_start_period=r_start_period.replace(day=r_start_period_to_day)
				r_start_period = r_start_period

			r_start_period=end_date
			for mm in range(0,real_h_count):
				h_count+=1
				new_amount_to_invoice = 0
				unit_price = self.per_month
				if not self.contract_line_id.line_regular:
					r_half_end = r_start_period+relativedelta(months=-6)
					start_day=start_period.day
					s_day=r_half_end.day+1
					try:
						r_half_to_date=r_half_end.replace(day=(s_day))
					except:
						s_day=s_day-1
						r_half_to_date=r_half_end.replace(day=(s_day))
						if r_half_end.month!=2:
							r_half_to_date=r_half_end+relativedelta(day=+1)

					if h_count==real_h_count:
						r_half_to_date =start_period
					# code added for amount computation
					month_end_period = r_start_period
					month_start_period = r_start_period+relativedelta(months=-1)
					month_start_period = month_start_period + relativedelta(days=+1)
					i = 0
					condition=True
					while (month_end_period <=r_start_period):
						if month_start_period >= r_half_to_date:
							real_month_start = month_end_period+relativedelta(months=-1)
							no_of_month_days = (month_end_period-real_month_start).days
							no_of_days_service_period = (month_end_period-month_start_period).days+1
							# new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
							new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_month_days
							month_end_period = month_start_period+relativedelta(days=-1)
							month_start_period = month_end_period+relativedelta(months=-1)
							month_start_period = month_start_period+relativedelta(days=+1)
						elif h_count == real_h_count and condition:
							month_start_period =r_half_to_date
							condition=False
						else:
							break;
					# new code added for amount computation end	
					vals={
						'start_period' : r_half_to_date,
						'end_period' : r_start_period,
						'amount_to_invoice' : new_amount_to_invoice,
						}
					line_periods.append(vals)
					next_half_start = r_half_to_date
					r_start_period = next_half_start+relativedelta(days=-1)
					r_start_period = r_start_period
				else:
					r_half_end = r_start_period+relativedelta(months=-5)
					start_day=1
					r_half_to_date=r_half_end.replace(day=start_day)
					if h_count == real_h_count:
						r_half_to_date =start_period
					# code added for amount computation
					month_end_period = r_start_period
					month_start_period = month_end_period.replace(day=1)
					i = 0
					condition=True
					while (month_end_period <=r_start_period):
						if month_start_period >= r_half_to_date:
							no_of_month_days = calendar.monthrange(month_start_period.year, month_start_period.month)[1]
							no_of_days_service_period = (month_end_period-month_start_period).days+1
							# new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
							new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_month_days
							month_end_period = month_start_period+relativedelta(days=-1)
							month_start_period = month_end_period.replace(day=1)
						elif h_count == real_h_count and condition:
							month_start_period =r_half_to_date
							condition=False
						else:
							break;
					# new code added for amount computation end
					vals={
						'start_period' : r_half_to_date,
						'end_period' : r_start_period,
						'amount_to_invoice' : new_amount_to_invoice,
						}
					line_periods.append(vals)
					next_half_start = r_half_to_date
					r_start_period = next_half_start+relativedelta(months=-1)
					r_start_period_to_day=calendar.monthrange(r_start_period.year, r_start_period.month)[1]
					r_start_period=r_start_period.replace(day=r_start_period_to_day)
					r_start_period = r_start_period
			line_periods.reverse()
		#------ correct as on 4 nov 2021
		if frequency == 'Y':
			new_no_of_years = no_of_months/12
			if new_no_of_years>int(new_no_of_years):
				new_no_of_years = int(new_no_of_years)+1
			else:
				new_no_of_years = int(new_no_of_years)
			yr_start_period = start_period
			for mm in range(0,new_no_of_years):
				yr_end_period = yr_start_period+relativedelta(months=+12)
				yr_end_period = yr_end_period+relativedelta(days=-1)
				new_amount_to_invoice =(self.contract_line_id.price_subtotal)/new_no_of_years
				if (mm+1)==new_no_of_years:
					yr_end_period=end_date
				vals={
					'start_period' : yr_start_period,
					'end_period' : yr_end_period,
					'amount_to_invoice' : new_amount_to_invoice,
					}
				line_periods.append(vals)
				next_year_start = yr_end_period+relativedelta(days=+1)
				yr_start_period = next_year_start
		#------ correct as on 4 nov 2021

		# new
		count=0
		for p in line_periods:
			count=count+1
			# print("counttttttt",count)
			period_start=p['start_period']
			period_end=p['end_period']
			no_days = abs((period_end - period_start).days)+1
			# amount_to_invoice = no_days*amount_per_days
			amount_to_invoice = p['amount_to_invoice']
			line_vals={
			'service_id':self.id,
			'period_from':period_start,
			'period_to':period_end,
			'amount':amount_to_invoice,
			'invoiced':False,
			# 'pending_amount':amount_to_invoice,
			}
			# commented here on oct12 2021 waiting for them to report
			# if period_end == end_date and t_amount < total_amount:
				# line_vals['amount'] = total_amount-t_amount
			# commented here on oct12 2021 waiting for them to report endddd

			# added since if there is minimum 90days for quarter,per month*3 is correct.
			if frequency=='Q':
				q_days=(period_end-period_start).days+1
				print("q_daysssss",q_days)
				if q_days>=89:
					line_vals['amount'] = self.per_month*3
				elif q_days>=58:
					line_vals['amount'] = self.per_month*2
				elif q_days>=28:
					line_vals['amount'] = self.per_month
			if frequency=='M':
				m_days=(period_end-period_start).days+1
				if m_days>=28:
					line_vals['amount'] = self.per_month
			if frequency=='H':
				h_days=(period_end-period_start).days+1
				print("hhhh",h_days)
				if h_days>=180:
					line_vals['amount'] = self.per_month*6
				elif h_days>=150:
					line_vals['amount'] = self.per_month*5
				elif h_days>=120:
					line_vals['amount'] = self.per_month*4
				elif h_days>=90:
					line_vals['amount'] = self.per_month*3
				elif h_days>=58:
					line_vals['amount'] = self.per_month*2
				elif h_days>=28:
					line_vals['amount'] = self.per_month





			# for special case, we have to update the amount for first period line from already made invoice 
			if self.contract_line_id.state=='0_draft' and len(self.contract_line_id.invoice_line_ids)==1 and count==1:
				line_vals['amount'] = self.contract_line_id.invoice_line_ids[0].price_subtotal
				line_vals['invoiced'] = True
				line_vals['invoice_line_id'] = self.contract_line_id.invoice_line_ids[0].id
			
			line_id=self.env['od.contract.payment.line'].create(line_vals)
			t_amount = t_amount+line_id.amount
			# print("kgffffffffff",t_amount)

	
#added on 1 apr 2022
	def generate_fluctng_prepay(self,frequency):
		# finding parent prepayment lines in order
		parent_prepayment_qry='''SELECT pl.id FROM od_contract_payment_line pl 
								 LEFT JOIN od_contract_payment p ON p.id=pl.service_id
								 WHERE p.contract_line_id=%s AND pl.period_to>'%s' order by pl.period_from asc'''%(self.contract_line_id.flctng_parent_contract_line_id.id, self.start_date)
		print(parent_prepayment_qry)
		self._cr.execute(parent_prepayment_qry)
		prepayment_result=self._cr.fetchall()
		prepayment_line_ids=[z[0] for z in prepayment_result]
		line_count=0
		for prepay in prepayment_line_ids:
			prepay_line=self.env['od.contract.payment.line'].browse(prepay)
			# print(prepay_line,prepay_line.period_from,prepay_line.period_to)
			line_count=line_count+1
			# prepay_vals={}
			period_from=prepay_line.period_from
			period_to=prepay_line.period_to
			if line_count==1:
				'''replace the period from with new period from for the first line'''
				period_from=self.start_date
				 
			#find amount
			# new_amount_to_invoice = 0
			unit_price = self.per_month
			# no_of_month_days = (period_from-period_to).days
			# no_of_days_service_period = (period_from-period_to).days+1
			# new_amount_to_invoice = new_amount_to_invoice+(unit_price/no_of_month_days)*no_of_days_service_period
			prepay_vals={
			'service_id':self.id,
			'period_from':period_from,
			'period_to':period_to,
			'amount':unit_price,
			'invoiced':False,
			}
			# print(prepay_vals)
			# if frequency=='Q':
			# 	q_days=(period_to-period_from).days+1
			# 	print("q_daysssss",q_days)
			# 	if q_days>=89:
			# 		prepay_vals['amount'] = self.per_month*3
			# 	elif q_days>=58:
			# 		prepay_vals['amount'] = self.per_month*2
			# 	elif q_days>=28:
			# 		prepay_vals['amount'] = self.per_month
			# if frequency=='M':
			# 	prepay_vals['amount']=unit_price

			# print(prepay_vals)
			# line_id=self.env['od.contract.payment.line'].create(prepay_vals)
			self.env['od.contract.payment.line'].create(prepay_vals)



		# print(s)

		


	def generate(self):
		for line in self:
			start_date = line.start_date
			end_date = line.end_date
			total_amount = line.total_amount
			days = abs((end_date - start_date).days)+1
			amount_per_days = total_amount/days
			# for special case the amount divided should be total amount - already invoiced amount
			if self.contract_line_id.state=='0_draft' and len(self.contract_line_id.invoice_line_ids)==1:
				amount_per_days = (total_amount-self.contract_line_id.invoice_line_ids[0].price_total)/days

			if line.billing_cycle=='monthly':
				months = len(pd.date_range(start_date, end_date, freq='M'))
				period_start = start_date
				if line.fluctuating_contract:
					self.generate_fluctng_prepay('M')# to generate prepayment lines for fluctuating conntract lines
				else:
					self.generate_linesnew(start_date, end_date, period_start, 'M', 0, amount_per_days, total_amount)#for prepayment lines for normal cases
				self.generate_lines(start_date, end_date, period_start, months, 0, amount_per_days, total_amount)#to generate revenue lines
					
			if line.billing_cycle == 'quarterly':
				print("dateeeeeee",pd.date_range(start_date, end_date, freq='Q'))
				# print("monnnnnn",pd.date_range(start_date, end_date, freq='M'))
				quarter = len(pd.date_range(start_date, end_date, freq='Q'))
				print("quarterrrrrrrrr",quarter)
				# print(s)
				period_start = start_date
				if line.fluctuating_contract:
					raise UserError(_('Only Monthly billing Cycle is allowed for this contract line'))
				else:
					self.generate_linesnew(start_date, end_date, period_start, 'Q', 0, amount_per_days, total_amount)
				self.generate_lines(start_date, end_date, period_start, quarter, 2, amount_per_days, total_amount)

				
					
			if line.billing_cycle == 'half':
				no_of_years = len(pd.date_range(start_date, end_date, freq='Y'))
				halves = no_of_years*2
				print("noffffffssss",halves)
				period_start = start_date
				if line.fluctuating_contract:
					raise UserError(_('Only Monthly billing Cycle is allowed for this contract line'))
				else:
					self.generate_linesnew(start_date, end_date, period_start, 'H', 0, amount_per_days, total_amount)
				self.generate_lines(start_date, end_date, period_start, halves, 5, amount_per_days, total_amount)


			if line.billing_cycle in ('yearly','annually'):
				years = len(pd.date_range(start_date, end_date, freq='Y'))
				period_start = start_date
				if line.fluctuating_contract:
					raise UserError(_('Only Monthly billing Cycle is allowed for this contract line'))
				else:
					self.generate_linesnew(start_date, end_date, period_start, 'Y', 11, amount_per_days, total_amount)
				self.generate_lines(start_date, end_date, period_start, years, 11, amount_per_days, total_amount)
				
			if line.billing_cycle=='one_time':
				period_start = start_date
				years =1
				# generate paylines
				line_vals={
				'service_id':self.id,
				'period_from':start_date,
				'period_to':end_date,
				'amount':total_amount,
				'invoiced':False,
				}
				if self.contract_line_id.state=='0_draft' and len(self.contract_line_id.invoice_line_ids)==1:
					#~~~~~new change added on jan 24 2022--
					if self.contract_line_id.invoice_line_ids[0].price_subtotal != self.total_amount:
						extra_end_date=calendar.monthrange(start_date.year, start_date.month)[1]
						extra_end_date=period_start.replace(day=extra_end_date)
						line_vals['period_to'] = extra_end_date
					line_vals['amount'] = self.contract_line_id.invoice_line_ids[0].price_subtotal
					line_vals['invoiced'] = True
					line_vals['invoice_line_id'] = self.contract_line_id.invoice_line_ids[0].id
				line_id=self.env['od.contract.payment.line'].create(line_vals)
				#~~~~~new change added on jan 24 2022-- onetime advance case extra one line will be created with remaining amount.
				if line_id.amount!=self.total_amount:
					extra_start_date = extra_end_date+relativedelta(days=+1)
					# extra_end_date=calendar.monthrange(extra_start_date.year, extra_start_date.month)[1]
					# print("oppppp",extra_end_date,period_start)
					# s_day=extra_end_date
					# try:
					# 	extra_end_date=period_start.replace(day=s_day)
					# except:
					# 	s_day=s_day-1
					# 	extra_end_date=period_start.replace(day=(s_day))
					# 	extra_end_date=period_start+relativedelta(day=+1)
					# extra_end_date=extra_end_date
					extra_line_vals={
					'service_id':self.id,
					'period_from':extra_start_date,
					'period_to':end_date,
					'amount':(total_amount-line_id.amount),
					'invoiced':False,
					}
					extra_line_id=self.env['od.contract.payment.line'].create(extra_line_vals)
					extra_line_id.service_id.contract_line_id.next_invoice_date=extra_start_date
				#~~~~~~~~~~~new change end~~~~~~~~~
				# generate revenue line
				self.generate_lines(start_date, end_date, period_start, years, 11, amount_per_days, total_amount)
			self.generate_direct_costing_line()
			self.link_monthly_lines()




	# server action to update revenue lies
	def update_revenue_lines(self):
		for line in self:
			start_date = line.start_date
			end_date = line.end_date
			total_amount = line.total_amount
			days = abs((end_date - start_date).days)+1
			amount_per_days = total_amount/days
			# for special case the amount divided should be total amount - already invoiced amount
			if self.contract_line_id.state=='0_draft' and len(self.contract_line_id.invoice_line_ids)==1:
				amount_per_days = (total_amount-self.contract_line_id.invoice_line_ids[0].price_total)/days

			if line.billing_cycle=='monthly':
				months = len(pd.date_range(start_date, end_date, freq='M'))
				period_start = start_date
				self.generate_lines(start_date, end_date, period_start, months, 0, amount_per_days, total_amount)#to generate revenue lines
					
			if line.billing_cycle == 'quarterly':
				print("dateeeeeee",pd.date_range(start_date, end_date, freq='Q'))
				# print("monnnnnn",pd.date_range(start_date, end_date, freq='M'))
				quarter = len(pd.date_range(start_date, end_date, freq='Q'))
				print("quarterrrrrrrrr",quarter)
				# print(s)
				period_start = start_date
				self.generate_lines(start_date, end_date, period_start, quarter, 2, amount_per_days, total_amount)

				
					
			if line.billing_cycle == 'half':
				no_of_years = len(pd.date_range(start_date, end_date, freq='Y'))
				halves = no_of_years*2
				print("noffffffssss",halves)
				period_start = start_date
				self.generate_lines(start_date, end_date, period_start, halves, 5, amount_per_days, total_amount)


			if line.billing_cycle in ('yearly','annually'):
				years = len(pd.date_range(start_date, end_date, freq='Y'))
				period_start = start_date
				self.generate_lines(start_date, end_date, period_start, years, 11, amount_per_days, total_amount)
				
			if line.billing_cycle=='one_time':
				period_start = start_date
				years =1
				# generate revenue line
				self.generate_lines(start_date, end_date, period_start, years, 11, amount_per_days, total_amount)

	# server action to update amountin revenue line

	def server_action_generate(self):
		for line in self:
			start_date = line.start_date
			end_date = line.end_date
			total_amount = line.total_amount
			days = abs((end_date - start_date).days)+1
			amount_per_days = total_amount/days
			if self.contract_line_id.state=='0_draft' and len(self.contract_line_id.invoice_line_ids)==1:
				amount_per_days = (total_amount-self.contract_line_id.invoice_line_ids[0].price_total)/days

			if line.billing_cycle=='monthly':
				months = len(pd.date_range(start_date, end_date, freq='M'))
				period_start = start_date
				self.server_action_generate_lines(start_date, end_date, period_start, months, 0, amount_per_days, total_amount)#to generate revenue lines
					
			if line.billing_cycle == 'quarterly':
				print("dateeeeeee",pd.date_range(start_date, end_date, freq='Q'))
				# print("monnnnnn",pd.date_range(start_date, end_date, freq='M'))
				quarter = len(pd.date_range(start_date, end_date, freq='Q'))
				print("quarterrrrrrrrr",quarter)
				# print(s)
				period_start = start_date
				self.server_action_generate_lines(start_date, end_date, period_start, quarter, 2, amount_per_days, total_amount)
					
			if line.billing_cycle == 'half':
				no_of_years = len(pd.date_range(start_date, end_date, freq='Y'))
				halves = no_of_years*2
				print("noffffffssss",halves)
				period_start = start_date
				self.server_action_generate_lines(start_date, end_date, period_start, halves, 5, amount_per_days, total_amount)

			if line.billing_cycle in ('yearly','annually'):
				years = len(pd.date_range(start_date, end_date, freq='Y'))
				period_start = start_date
				self.server_action_generate_lines(start_date, end_date, period_start, years, 11, amount_per_days, total_amount)
				
			if line.billing_cycle=='one_time':
				period_start = start_date
				years =1
				self.server_action_generate_lines(start_date, end_date, period_start, years, 11, amount_per_days, total_amount)

	def server_action_generate_lines(self, start_date, end_date, period_start, frequency, months, amount_per_days, total_amount):
		t_amount = 0
		t_amount1 = 0
		period_start = period_start
		prec = self.env['decimal.precision'].precision_get('Account')
		if self.contract_line_id.acculde:
			total_amount = self.total_amount

			for ml in self.monthly_line_ids:
				old_amount = ml.amount
				unit_price = self.per_month
				no_of_month_days = calendar.monthrange(ml.period_from.year, ml.period_from.month)[1]
				amount_to_invoice_curr = (unit_price/no_of_month_days)*no_of_month_days
				amount_to_invoice = (unit_price/no_of_month_days)*no_of_month_days
				if not total_amount:
					amount_to_invoice = 0
				amount_to_invoice = amount_to_invoice * self.contract_id.od_exchange_rate #exchnge rate change
				if ml.invoiced:
					diff_amt = amount_to_invoice - ml.amount
					print("jjjj",diff_amt,ml.period_from,float_is_zero(diff_amt,precision_rounding=self.env.company.currency_id.rounding))
					if not float_is_zero(diff_amt,precision_rounding=self.env.company.currency_id.rounding):
						# print("yyyy",float_compare(ml.amount,amount_to_invoice,precision_digits=prec))
						if float_compare(ml.amount,amount_to_invoice,precision_digits=prec) != 0:
							ml.amt_difference = amount_to_invoice - ml.amount
				if total_amount:
					total_amount -= amount_to_invoice_curr
				ml.amount = amount_to_invoice
				if not ml.invoiced and ml.invoice_line_id:
					ml.invoice_date = ml.invoice_line_id.move_id.invoice_date
					if ml.reverse_line_id:
						ml.reverse_date = ml.reverse_line_id.move_id.invoice_date
				print("ooooooooo",old_amount,amount_to_invoice,float_compare(old_amount,amount_to_invoice,precision_digits=prec),ml.period_from)
			# print(s)
		else:
			if self.billing_cycle=='one_time':

				if len(self.payment_line)>1:
					total_amount = self.total_amount
					for ml in self.monthly_line_ids:
						unit_price = self.per_month
						no_of_month_days = calendar.monthrange(ml.period_from.year, ml.period_from.month)[1]
						amount_to_invoice_curr = (unit_price/no_of_month_days)*no_of_month_days
						amount_to_invoice = (unit_price/no_of_month_days)*no_of_month_days
						if not total_amount:
							amount_to_invoice = 0
						amount_to_invoice = amount_to_invoice * self.contract_id.od_exchange_rate #exchnge rate change
						if ml.invoiced:
							diff_amt = amount_to_invoice - ml.amount
							if float_is_zero(diff_amt,precision_rounding=self.env.company.currency_id.rounding):
								if float_compare(ml.amount,amount_to_invoice,precision_digits=prec) > 0:
									ml.amt_difference = amount_to_invoice - ml.amount
						if total_amount:
							total_amount -= amount_to_invoice_curr
						ml.amount = amount_to_invoice
						if not ml.invoiced and ml.invoice_line_id:
							ml.invoice_date = ml.invoice_line_id.move_id.invoice_date
							if ml.reverse_line_id:
								ml.reverse_date = ml.reverse_line_id.move_id.invoice_date
				else:
					for ml in self.monthly_line_ids:
						amount_to_invoice = self.total_amount * self.contract_id.od_exchange_rate #exchnge rate change
						if ml.invoiced:
							diff_amt = amount_to_invoice - ml.amount
							if float_is_zero(diff_amt,precision_rounding=self.env.company.currency_id.rounding):
								if float_compare(ml.amount,amount_to_invoice,precision_digits=prec) > 0:
									ml.amt_difference = amount_to_invoice - ml.amount
						ml.amount = amount_to_invoice
						if not ml.invoiced and ml.invoice_line_id:
							ml.invoice_date = ml.invoice_line_id.move_id.invoice_date
							if ml.reverse_line_id:
								ml.reverse_date = ml.reverse_line_id.move_id.invoice_date
				# ~~~~ new changed added end~~~~~~
			else:
				for ml in self.monthly_line_ids:
					amount_to_invoice = self.total_amount * self.contract_id.od_exchange_rate #exchnge rate change
					if ml.invoiced:
						diff_amt = amount_to_invoice - ml.amount
						if float_is_zero(diff_amt,precision_rounding=self.env.company.currency_id.rounding):
							if float_compare(ml.amount,amount_to_invoice,precision_digits=prec) > 0:
								ml.amt_difference = amount_to_invoice - ml.amount
					ml.amount = amount_to_invoice
					if not ml.invoiced and ml.invoice_line_id:
						ml.invoice_date = ml.invoice_line_id.move_id.invoice_date
						if ml.reverse_line_id:
							ml.reverse_date = ml.reverse_line_id.move_id.invoice_date
	
	def server_action_revenue_entry(self):
		line_ids = self.env['od.contract.monthly.line'].search([('invoiced','=',True),('amt_difference','!=',0)])
		# print("lllllllllsssss",line_ids)
		print("leeeee",len(line_ids))
		print(s)
		param_id = self.env['ir.config_parameter'].sudo().search([('key','=','revenue_journal_id')])
		if not param_id:
			raise UserError(_("Please set the 'revenue_journal_id' system parameter"))
		entry_vals={
			'date':'2023-06-30',
			'move_type':'entry',
			'currency_id':self.env.company.currency_id.id,
			'journal_id':int(param_id.value),
			}
		entry_id = self.env['account.move'].create(entry_vals)
		print("entryyyy_id",entry_id)
		mv_line = []
		credit = 0
		debit = 0
		amount_to_be_posted = 0
		credit_account=False
		line_ls = []
		for line_id in line_ids:
			credit_account=line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id and line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id.id or line_id.service_id.contract_line_id.product_id.categ_id.property_account_expense_categ_id and line_id.service_id.contract_line_id.product_id.categ_id.property_account_expense_categ_id.id
			if line_id.amt_difference >=0:
				debit = line_id.amt_difference
				credit = 0
			else:
				debit = 0
				credit = abs(line_id.amt_difference)				
			line_vals={
			'account_id':line_id.service_id.contract_line_id.product_id.property_account_income_id and line_id.service_id.contract_line_id.product_id.property_account_income_id.id or line_id.service_id.contract_line_id.product_id.categ_id.property_account_income_categ_id and line_id.service_id.contract_line_id.product_id.categ_id.property_account_income_categ_id.id,
			'product_id':line_id.service_id.contract_line_id.product_id.id,
			'partner_id':line_id.service_id.partner_id.id,
			'debit': debit,
			'credit': credit,
			'revenue_line_id':line_id.id,
			'period_from':line_id.period_from,
			'period_to':line_id.period_to,
			}
			# w_line=(0,0,line_vals)
			line_ls.append(line_vals)
			credit_vals={
				'account_id':credit_account,
				'product_id':line_id.service_id.contract_line_id.product_id.id,
				'partner_id':line_id.service_id.partner_id.id,
				'debit':credit if line_id.amt_difference<0 else 0,
				'credit':debit if line_id.amt_difference>=0 else 0,
				'revenue_line_id':line_id.id,
				'period_from':line_id.period_from,
				'period_to':line_id.period_to,
				}
			# w_line=(0,0,credit_vals)
			line_ls.append(credit_vals)

		print("doneeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
		for line_dict in line_ls:
			print("lineeeee",line_dict)
			balance = line_dict['debit'] - line_dict['credit']
			line_vals={
				'account_id':line_dict['account_id'],
				'product_id':line_dict['product_id'],
				'partner_id':line_dict['partner_id'],
				'debit': balance if balance>=0 else 0,
				'credit': abs(balance) if balance<0 else 0,
				'od_revenue_line_id':line_dict['revenue_line_id'],
				'move_id':entry_id.id,
				'ref':"difference amount for the period "+str(line_dict['period_from'])+" - "+str(line_dict['period_to']),
				}
			w_line=(0,0,line_vals)
			mv_line.append(w_line)
		entry_id.line_ids=mv_line
		entry_id.post()




class OrchidContractPaymentLine(models.Model):
	_name = "od.contract.payment.line"
	_description = "Contract Line Payment Lines"

	service_id = fields.Many2one('od.contract.payment', string="Service", ondelete='cascade')
	period_from = fields.Date(string="Period From")
	period_to = fields.Date(string="Period To")
	amount = fields.Float(digits='Product Price', string="Amount")
	invoice_line_id = fields.Many2one('account.move.line', string="invoice_line")
	invoiced = fields.Boolean(string="Invoiced", default=False)
	invoice_status = fields.Selection(related='invoice_line_id.parent_state', store=True, readonly=True)
	monthly_line_ids = fields.Many2many('od.contract.monthly.line', string="Monthly Lines")

	def update_monthly_lines_details(self):
		for line in self.monthly_line_ids:
			invoice_date = self.invoice_line_id.move_id.invoice_date
			param_id = self.env['ir.config_parameter'].sudo().search([('key','=','od_last_revenue_post_date')])
			print("jjjj",param_id)
			if not param_id:
				raise UserError(_("od_last_revenue_post_date param is not set!!!"))
			last_post_date = self.env['ir.config_parameter'].sudo().get_param('od_last_revenue_post_date')
			# last_post_date = param_id.value
			# print('strrrrrrrrrrrrr',last_post_date,type(last_post_date),str(line.period_from))
			if not line.reverse_line_id:
				line.invoice_date = invoice_date
				line.invoice_line_id = self.invoice_line_id.id
				line.due = True

				# if invoice comes under the monthly period
				if invoice_date>=line.period_from and invoice_date<=line.period_to:
					if str(line.period_from)<last_post_date:
						line.recognition_date = invoice_date
					else:
						line.recognition_date = line.period_from
				elif invoice_date<line.period_from:
					if str(line.period_from)<last_post_date:
						line.recognition_date = invoice_date
					else:
						line.recognition_date = line.period_to
				elif invoice_date>line.period_from:
					if str(line.period_from)<last_post_date:
						line.recognition_date = invoice_date
					else:
						line.recognition_date = line.period_from
				#else
				else:
					line.recognition_date = invoice_date

				# # print("lineeeeee",line)
				# for pl in self.payment_line:
				# 	# print("payment linneee",pl.period_from,pl.period_to)
				# 	if (pl.period_from<=line.period_to) and (pl.period_to>=line.period_to):
				# 		# print("yessss",line.period_to)
				# 		m_ls = pl.monthly_line_ids.ids
				# 		m_ls.append(line.id)
				# 		m_ls = list(set(m_ls))
				# 		# print("kkkkk",m_ls)
				# 		pl.write({'monthly_line_ids':[(6,0,m_ls)]})
				# 		# print("kkfffff",pl.monthly_line_ids)
	
	# pending_amount = fields.Float(digits='Product Price', string="Pending Amount")

	# @api.onchange('invoice_line_id'):
	# def onchange_invoice_status(self):
	# 	for line in self:
	# 		if line.invoice_line_id:
	# 			line.pending_amount=(line.amount-invoice_line_id.price_total)
	# 			if line.pending_amount==0:
	# 				line.invoiced=True

class OrchidContractMonthlyLine(models.Model):
	_name = "od.contract.monthly.line"
	_description = "Contract Line Monthly Lines"

	service_id = fields.Many2one('od.contract.payment', string="Service", ondelete='cascade')
	period_from = fields.Date(string="Period From")
	period_to = fields.Date(string="Period To")
	amount = fields.Float(digits='Product Price', string="Amount")
	invoice_line_id = fields.Many2one('account.move.line', string="Invoice Line")
	reverse_line_id = fields.Many2one('account.move.line', string="Reverse Line")
	invoice_date = fields.Date(string="Invoice Date")
	reverse_date = fields.Date(string="Reverse Date")
	invoiced = fields.Boolean(string="Posted", default=False)
	due = fields.Boolean(string="Due", default=False)
	move_id = fields.Many2one('account.move', string="Journal Entry", ondelete='restrict')
	# invoice_status = fields.Selection(related='invoice_line_id.parent_state', store=True, readonly=True)
	amt_difference = fields.Float(string="Difference")
	recognition_date = fields.Date(string="Recognition Date")

class AccountMove(models.Model):
	_inherit = "account.move"

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
		return res

	def action_post(self):
		res = super(AccountMove, self).action_post()
		# overridden to update the posted(invoiced) field of revenue line. if the entry is reposted , the field is set to true
		revenue_line_ids = self.env['od.contract.monthly.line'].search([('move_id','=',self.id)])
		for line in revenue_line_ids:
			line.invoiced=True
		return res

class AccountMoveLine(models.Model):
	_inherit = "account.move.line"
	od_revenue_line_id = fields.Many2one('od.contract.monthly.line', string="Revenue Line")
	od_reversed_revenue_line_ids = fields.Many2many('od.contract.monthly.line', string="Reversed Revenue Line")

class DirectCostingLine(models.Model):
	_name = 'od.direct.costing.line'
	description = "Direct Costing Lines"

	service_id = fields.Many2one('od.contract.payment', string="Service", ondelete='cascade')
	product_id = fields.Many2one('product.product', string="Product")
	period_from = fields.Date(string="Period From")
	period_to = fields.Date(string="Period To")
	amount = fields.Float(digits='Product Price', string="Direct Cost")
	invoiced = fields.Boolean(string="Posted", default=False)
	move_id = fields.Many2one('account.move', string="Journal Entry", ondelete='restrict')
	service_status = fields.Selection(related='service_id.states', store=True)

	
