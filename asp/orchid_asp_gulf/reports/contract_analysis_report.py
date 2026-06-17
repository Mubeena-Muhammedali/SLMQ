# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo import tools


class OdContractAnalysisView(models.Model):

	_name = 'od.contract.analysis.view'
	_description = "Contract Analysis View"
	_auto = False

	name = fields.Char(string="Contract Number")
	contract_code = fields.Char(string="Contract Name")
	partner_id = fields.Many2one('res.partner', string="Customer")
	currency_id = fields.Many2one('res.currency', string="Currency")
	analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
	contract_period = fields.Integer(string="Contract Period")
	date_from = fields.Date(string="Start Date")
	date_to = fields.Date(string="To Date")
	company_id = fields.Many2one("res.company",string="Company")
	effective_date = fields.Date(string="Effective Date")
	billing_from = fields.Date(string="Billing From")
	billing_to = fields.Date(string="Billing To")
	next_invoice_date = fields.Date(string="Next Payment Date")
	billing_cycle = fields.Selection([('monthly','Monthly'), ('quarterly','Quarterly'), ('half','Half yearly'), ('yearly','Yearly'), ('one_time','One Time'), ('annually','Annually')], string="Billing Cycle")
	acculde = fields.Boolean(string="Accrued")
	state=fields.Selection([('0_draft','Draft'),('active','Active'),('inactive','Expired'),('terminate','Terminated')], string="Active")
	product_id = fields.Many2one('product.product', string="Product")
	product_uom_qty = fields.Float(string="Quantity")
	price_unit = fields.Float(string="Unit Price")
	price_subtotal = fields.Float(string="Price Subtotal")
	price_total = fields.Float(string="Total")
	discount = fields.Float(string='Discount (%)')
	frequency = fields.Integer(string="Frequency")


	def init(self):
		cr = self.env.cr   
		tools.drop_view_if_exists(cr, 'od_contract_analysis_view')
		cr.execute("""
			CREATE or replace view od_contract_analysis_view as (
				SELECT
				cl.id as id,
				cl.effective_date as effective_date,
				cl.billing_from as billing_from,
				cl.billing_to as billing_to,
				cl.next_invoice_date as next_invoice_date,
				cl.billing_cycle as billing_cycle,
				cl.acculde as acculde,
				cl.state as state,
				cl.product_id as product_id,
				cl.product_uom_qty as product_uom_qty,
				cl.price_unit as price_unit,
				cl.price_subtotal as price_subtotal,
				cl.price_total as price_total,
				cl.discount as discount,
				cl.frequency as frequency,


				ct.name as name,
				ct.contract_code as contract_code,
				ct.partner_id as partner_id,
				ct.contract_period as contract_period,
				ct.analytic_account_id as analytic_account_id,
				ct.date_from as date_from,
				ct.date_to as date_to,
				ct.company_id as company_id

				FROM od_asp_contract_line cl
				LEFT JOIN od_asp_contract ct ON ct.id = cl.order_id
				-- WHERE ail.exclude_from_invoice_tab is false AND ai.state IN ('posted')
				-- GROUP BY 
				
				ORDER BY ct.name ASC
				)
		""")

	
