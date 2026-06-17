# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

ACCOUNT_DOMAIN = [
    ('deprecated', '=', False),
    ('account_type', '=', 'income'),
    ('is_off_balance', '=', False)
]



class ProducTemplate(models.Model):
	_inherit = "product.template"

	od_property_account_revenue_id = fields.Many2one('account.account', company_dependent=True,string="Revenue Account", domain=ACCOUNT_DOMAIN)
	od_property_account_subscription_id = fields.Many2one('account.account', company_dependent=True,string="Subscription Account", domain=ACCOUNT_DOMAIN)
	od_property_account_subscription_id = fields.Many2one('account.account', company_dependent=True,string="Subscription Account")
	od_company_currency_id = fields.Many2one('res.currency',string='Company Currency', readonly=True, default=lambda self: self.env.company.currency_id.id)
	od_avg_cost = fields.Monetary(string="Average Cost", currency_field='od_company_currency_id', readonly=True, help="for cost recognition")
	od_supplier_ref = fields.Char(string="Supplier Reference")
	od_revenue_type = fields.Selection([
		('hosting', 'Hosting'),
		('public_cloud', 'Public Cloud'),
		('m365', 'M365'),
		('prof_serv', 'Prof Serv'),
		('trading', 'Trading'),
	], string="Revenue Type")


class Product(models.Model):
	_inherit='product.product'

	def get_product_multiline_description_sale(self):
		""" overidden to remove the product code from description
		"""
		# name = self.display_name
		name = self.name
		if self.description_sale:
			name += '\n' + self.description_sale

		return name
