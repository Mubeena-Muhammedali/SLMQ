# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo import tools


class OrchidContractRevenueReport(models.Model):
	_name = 'od.contract.revenue.report'
	_description = "Current year revenue report"
	_order = 'partner_id'

	name = fields.Char(string="Contract Name")
	partner_id = fields.Many2one('res.partner', string="Customer")
	user_id = fields.Many2one('res.users', string="Salesperson")
	product_id = fields.Many2one('product.product', string="Product")
	expected_revenue = fields.Monetary('One Time Revenue', currency_field='company_currency')
	recurring_revenue = fields.Monetary('Recurring Revenues', currency_field='company_currency')
	recurring_revenue_monthly = fields.Monetary('Expected MRR', currency_field='company_currency')
	total_revenue = fields.Monetary('Total Revenues', currency_field='company_currency')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
	company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True)
	