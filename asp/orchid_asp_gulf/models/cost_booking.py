from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import calendar
from dateutil.relativedelta import relativedelta
import pandas as pd
import math

class OrchidCostBooking(models.Model):
	_name = "od.cost.booking"
	_description = "Cost Booking"
	_inherit = ['mail.thread']

	date = fields.Date(string="Date", required=True)
	date_start = fields.Date(string="Date From")
	state = fields.Selection([('draft','draft'),('confirm','confirm')], string="State", default='draft')
	costing_line_ids = fields.One2many('od.cost.booking.line','cost_booking_id', string="Costing Lines", copy=False)
	name = fields.Text(string="Remarks")
	company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
	company_currency_id = fields.Many2one('res.currency',string='Company Currency', readonly=True, related='company_id.currency_id')
	total_cost = fields.Monetary(string='Total Cost', currency_field='company_currency_id')
	move_id = fields.Many2one('account.move', string="Entry")

	def unlink(self):
		if self.state != 'draft':
			raise UserError(_("Only draft records can be deleted!!"))
		return super(OrchidCostBooking, self).unlink()

	@api.onchange('date')
	def onchange_date(self):
		for cost in self:
			if cost.date:
				cost.date_start = cost.date.replace(day=1)
			if cost.date:
				cost.name = "Cost Booking for "+ str(self.date_start) +" - "+str(self.date)

	def generate_lines(self):
		if self.date:
			if self.costing_line_ids:
				self.costing_line_ids.unlink()
			domain=[('period_from', '>=', self.date_start),('period_to', '<=', self.date),('invoiced','=',False)]
			get_total_cost = ('''SELECT sum(coalesce(pl.amount,0)) FROM od_po_costing_line pl WHERE pl.period_from >= '%s' AND pl.period_to <= '%s' AND pl.invoiced=false ''')%(self.date_start,self.date)
			self._cr.execute(get_total_cost)
			total_cost = self._cr.fetchone()
			total_cost = total_cost[0]
			self.total_cost = total_cost

			get_direct_cost_line = ('''SELECT 
								[]		dl.product_id as product,
										cp.partner_id as partner,
										sum(coalesce(dl.amount,0)) as debit
										FROM od_direct_costing_line dl
										LEFT JOIN od_contract_payment cp ON cp.id = dl.service_id
										WHERE dl.period_from >= '%s' AND dl.period_to <= '%s' AND dl.invoiced=false 
										AND cp.states='active'
										GROUP BY dl.product_id, cp.partner_id
										''')%(self.date_start,self.date)
			
			self._cr.execute(get_direct_cost_line)
			direct_cost_line = self._cr.dictfetchall()

			get_subscription_line = ('''SELECT 
										pcl.product_id as product,
										sum(coalesce(pcl.amount,0)) as credit
										FROM od_po_costing_line pcl
										WHERE pcl.period_from >= '%s' AND pcl.period_to <= '%s' AND pcl.invoiced=false 
										GROUP BY pcl.product_id
										''')%(self.date_start,self.date)
			
			self._cr.execute(get_subscription_line)
			subscription_line = self._cr.dictfetchall()

			get_asp_cost_line = ('''SELECT foo.product as product, sum(foo.pcl_amount) - sum(foo.dl_amount) as amount FROM 
								(SELECT 
								pcl.product_id as product,
								sum(coalesce(pcl.amount,0)) as pcl_amount,
								0 as dl_amount
								FROM od_po_costing_line pcl
								WHERE pcl.period_from >= '%s' AND pcl.period_to <= '%s' AND pcl.invoiced=false 
								AND pcl.product_id in (SELECT 
										dl.product_id as product FROM od_direct_costing_line dl
										LEFT JOIN od_contract_payment cp ON cp.id = dl.service_id
										WHERE dl.period_from >= '%s' AND dl.period_to <= '%s' AND dl.invoiced=false AND cp.states='active'
										GROUP BY dl.product_id)
								GROUP BY pcl.product_id

								UNION ALL
								SELECT 
								dl.product_id as product,
								0 as pcl_amount,
								sum(coalesce(dl.amount,0)) as dl_amount
								FROM od_direct_costing_line dl
								LEFT JOIN od_contract_payment cp ON cp.id = dl.service_id
								WHERE dl.period_from >= '%s' AND dl.period_to <= '%s' AND dl.invoiced=false AND cp.states='active'
								GROUP BY dl.product_id) as foo
								GROUP BY foo.product
								HAVING sum(foo.pcl_amount) - sum(foo.dl_amount)<>0
								''')%(self.date_start,self.date,self.date_start,self.date,self.date_start,self.date)
			
			
			self._cr.execute(get_asp_cost_line)
			asp_cost_line = self._cr.dictfetchall()

			get_asp_cost_only_po_line = ('''SELECT 
										pcl.product_id as product,
										sum(coalesce(pcl.amount,0)) as amount
										FROM od_po_costing_line pcl
										WHERE pcl.period_from >= '%s' AND pcl.period_to <= '%s' AND pcl.invoiced=false 
										AND pcl.product_id not in (SELECT 
										dl.product_id as product FROM od_direct_costing_line dl
										LEFT JOIN od_contract_payment cp ON cp.id = dl.service_id
										WHERE dl.period_from >= '%s' AND dl.period_to <= '%s' AND dl.invoiced=false AND cp.states='active'
										GROUP BY dl.product_id)
										GROUP BY pcl.product_id

								''')%(self.date_start,self.date,self.date_start,self.date)
			
			
			self._cr.execute(get_asp_cost_only_po_line)
			asp_cost_only_po_line = self._cr.dictfetchall()

			lines = []
			for direct_line in direct_cost_line:
				account_id = self.env['product.product'].browse(direct_line['product']).property_account_expense_id.id
				direct_vals={
					'cost_booking_id':self.id,
					'date':self.date,
					'credit':0,
					'partner_id':direct_line['partner'],
					'product_id':direct_line['product'],
					'debit':direct_line['debit'],
					'name':'Direct Cost',
					'account_id':account_id,
					'amount':direct_line['debit'],
				}
				lines.append((0,0,direct_vals))
			for asp_line in asp_cost_line:
				account_id = self.env['product.product'].browse(asp_line['product']).property_account_expense_id.id
				credit = debit=amount=0
				amount = asp_line['amount']
				if asp_line['amount'] >0:
					debit = abs(asp_line['amount'])
				else:
					credit = abs(asp_line['amount'])
				asp_vals={
					'cost_booking_id':self.id,
					'date':self.date,
					'credit':credit,
					'product_id':asp_line['product'],
					'debit':debit,
					'name':'ASP Cost',
					'account_id':account_id,
					'amount':amount,
				}
				lines.append((0,0,asp_vals))

			for asp_line in asp_cost_only_po_line:
				account_id = self.env['product.product'].browse(asp_line['product']).property_account_expense_id.id
				asp_vals={
					'cost_booking_id':self.id,
					'date':self.date,
					'credit':0,
					'product_id':asp_line['product'],
					'debit':asp_line['amount'],
					'name':'ASP Cost',
					'account_id':account_id,
					'amount':asp_line['amount'],
				}
				lines.append((0,0,asp_vals))

			for sub_line in subscription_line:
				account_id = self.env['product.product'].browse(sub_line['product']).od_property_account_subscription_id.id
				sub_vals={
					'cost_booking_id':self.id,
					'date':self.date,
					'credit':sub_line['credit'],
					'product_id':sub_line['product'],
					'debit':0,
					'name':'Subscription Cost',
					'account_id':account_id,
					'amount':sub_line['credit']*-1,
				}
				lines.append((0,0,sub_vals))
			self.costing_line_ids = lines

	
	def button_confirm(self):
		# generate_entries
		line_ls = []
		param_id = self.env['ir.config_parameter'].sudo().search([('key','=','costing_journal_id')])
		if not param_id:
			raise UserError(_("Please set the 'costing_journal_id' system parameter"))
		entry_vals={
				'date':self.date,
				'move_type':'entry',
				'currency_id':self.env.company.currency_id.id,
				'journal_id':int(param_id.value),
			}
		entry_id = self.env['account.move'].create(entry_vals)
		self.move_id = entry_id.id
		move_line = []
		for line_id in self.costing_line_ids:
			line_vals={
				'account_id':line_id.account_id.id,
				'product_id':line_id.product_id.id,
				'partner_id':line_id.partner_id.id,
				'debit': line_id.debit,
				'credit': line_id.credit,
				'move_id':entry_id.id,
			}
			move_line.append((0,0,line_vals))
		entry_id.line_ids  = move_line
		entry_id.post()
		update_direct_cost_line = '''UPDATE od_direct_costing_line dl set invoiced=True, move_id=%s FROM od_contract_payment cp WHERE cp.id = dl.service_id AND cp.states='active' AND dl.period_from >= '%s' AND dl.period_to <= '%s' AND dl.invoiced=false '''%(self.move_id.id,self.date_start,self.date)
		self._cr.execute(update_direct_cost_line)
		update_po_cost_line = '''UPDATE od_po_costing_line set invoiced=True, move_id=%s WHERE period_from >= '%s' AND period_to <= '%s' AND invoiced=false '''%(self.move_id.id,self.date_start,self.date)
		self._cr.execute(update_po_cost_line)
		self.state='confirm'



class OrchidCostBookingLine(models.Model):
	_name = "od.cost.booking.line"
	_description = "Cost Booking Line"

	cost_booking_id = fields.Many2one('od.cost.booking', string="Cost Booking", ondelete="cascade", copy=False)
	date = fields.Date(string="Date")
	partner_id = fields.Many2one('res.partner', string="Partner")
	product_id = fields.Many2one('product.product', string="Product")
	account_id = fields.Many2one('account.account', string="Account")
	company_id = fields.Many2one('res.company', string="Company", related="cost_booking_id.company_id")
	company_currency_id = fields.Many2one('res.currency',string='Company Currency', readonly=True, related='company_id.currency_id')
	debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
	credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
	name = fields.Char(string="Ref")
	amount = fields.Monetary(string='Cost', currency_field='company_currency_id')
