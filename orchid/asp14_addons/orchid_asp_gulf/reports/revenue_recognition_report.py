# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidRevenueRecognitionReport(models.TransientModel):
	_name = 'od.revenue.recognition.report'
	_description = "Revenue Recognition Utility Report"

	date = fields.Date(string="Wizard Date")
	revenue_date_from = fields.Date(string="Revenue Period From")
	revenue_date_to = fields.Date(string="Revenue Period To")
	revenue_line_id = fields.Many2one('od.contract.monthly.line', string="Revenue Line")
	partner_id = fields.Many2one('res.partner', string="Partner")
	product_id = fields.Many2one('product.product', string="Product")
	account_id = fields.Many2one('account.account', string="Account")
	company_id = fields.Many2one('res.company', string="Company")
	company_currency_id = fields.Many2one('res.currency',string='Company Currency', readonly=True, related='company_id.currency_id')
	debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
	credit = fields.Monetary(string='Credit', currency_field='company_currency_id')
	contract_number = fields.Char(string="Contract")
	name = fields.Char(string="Contract Name")
	invoice = fields.Char(string="Invoice")
	revenue_account_id = fields.Many2one('account.account', string="Revenue Account")