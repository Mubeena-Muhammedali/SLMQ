# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import calendar
from dateutil.relativedelta import relativedelta


class PurchaseOrder(models.Model):
	_inherit = 'purchase.order'

	od_contact_id = fields.Many2one('res.partner', string="Contact Person", ondelete='restrict', domain="[('parent_id','=',partner_id)]", help="Partner contact person")
	od_exchange_rate = fields.Float(digits=0, default=1.0,string="Exchange Rate")
	od_po_costing_line_ids = fields.One2many('od.po.costing.line','purchase_id', string="Purchase Costing Line")
	od_print_po_currency = fields.Boolean(string="Show string in PO Currency", default=False)
	
	@api.depends('order_line.od_frequency','date_approve')
	def onchange_costing_to_date(self):
		for po in self:
			if po.date_approve:
				for line in po.order_line:
					if line.od_start_date:
						start_date = line.od_start_date.replace(day=1)
						no_of_months = line.od_frequency-1
						end_date = start_date+relativedelta(months=+no_of_months)
						end_date_day=calendar.monthrange(end_date.year, end_date.month)[1]
						end_date=end_date.replace(day=end_date_day)
						line.od_to_date = end_date

	def button_confirm(self):
		res = super(PurchaseOrder, self).button_confirm()
		self.onchange_costing_to_date()
		self.od_generate_po_costing_line()
		return res

	def od_generate_po_costing_line(self):
		for line in self.order_line:
			if not line.analytic_distribution and line.od_start_date:
				start_date = line.od_start_date
				end_date = line.od_to_date

				month_start_date = start_date
				month_end_date_day = calendar.monthrange(month_start_date.year, month_start_date.month)[1]
				month_end_date=month_start_date.replace(day=month_end_date_day)

				cost_per_month = line.od_cost_per_month

				while(month_end_date<=end_date):
					line_vals={
					'purchase_id':self.id,
					'period_from':month_start_date,
					'period_to':month_end_date,
					'amount':cost_per_month,
					'invoiced':False,
					'purchase_line_id':line.id,
					'product_id':line.product_id.id,
					}
					self.env['od.po.costing.line'].create(line_vals)
					next_month_start = month_start_date.replace(day=1)
					month_start_date = next_month_start+relativedelta(months=+1)
					month_end_date_day=calendar.monthrange(month_start_date.year, month_start_date.month)[1]
					month_end_date=month_start_date.replace(day=month_end_date_day)

class PurchaseOrderLine(models.Model):
	_inherit = 'purchase.order.line'
	
	company_currency_id = fields.Many2one('res.currency',string='Company Currency', readonly=True, related='company_id.currency_id')
	od_frequency = fields.Integer(string="Frequency")
	od_cost_per_month = fields.Monetary(string="Cost per Month", currency_field='company_currency_id', readonly=True, store=True, compute="od_get_cost_per_mnth")
	od_start_date = fields.Date(string="Start Date", help="to filter in cost recognition")
	od_to_date = fields.Date(string="To Date", help="to filter in cost recognition")


	@api.depends('price_subtotal','od_frequency','order_id.currency_rate')
	def od_get_cost_per_mnth(self):
		for line in self:
			if line.product_id:
				company_currency_subtotal = line.price_subtotal/line.order_id.currency_rate
				line.od_cost_per_month = company_currency_subtotal/(line.od_frequency or 1)


class PurchaseCostingLine(models.Model):
	_name = 'od.po.costing.line'
	description = "Purchase Costing Lines"

	purchase_id = fields.Many2one('purchase.order', string="Purchase Order", ondelete='cascade')
	period_from = fields.Date(string="Period From")
	period_to = fields.Date(string="Period To")
	amount = fields.Float(digits='Product Price', string="Cost")
	purchase_line_id = fields.Many2one('purchase.order.line', string="Purchase Line")
	invoiced = fields.Boolean(string="Posted", default=False)
	move_id = fields.Many2one('account.move', string="Journal Entry", ondelete='restrict')
	purchase_status = fields.Selection(related='purchase_line_id.state', store=True)
	product_id = fields.Many2one('product.product', string="Product")
