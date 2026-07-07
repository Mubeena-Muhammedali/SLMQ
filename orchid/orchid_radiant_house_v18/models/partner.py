# -*- coding: utf-8 -*-

from odoo import models, fields, api,_

class ResPartnerBank(models.Model):
	_inherit = "res.partner.bank"

	od_iban = fields.Char(string='IBAN', tracking=True)

class ResPartner(models.Model):
	_inherit = "res.partner"

	od_product_seq_no = fields.Integer('Product Sequence')
	od_customer_code = fields.Char(string='Customer Code', tracking=True)

	_sql_constraints = [ 
		('code_uniq', 'unique(od_customer_code)', 'customer code should be unique'), 
	]

	@api.model_create_multi
	def create(self, vals_list):
		res = super(ResPartner, self).create(vals_list)
		if res.customer_rank>0 and not res.od_customer_code:
			res.od_customer_code = self.env['ir.sequence'].next_by_code('res.partner.customer') or '/'
		if res.supplier_rank>0 and not res.od_customer_code:
			res.od_customer_code = self.env['ir.sequence'].next_by_code('res.partner.supplier') or '/'
		return res

	@api.depends('parent_id', 'name', 'od_customer_code')
	def _compute_display_name(self):
		"""Compute display name.
		If 'od_customer_code' is set, display as '[od_customer_code] name'.
		Otherwise, show hierarchical name (Parent / Child).
		"""
		for record in self:
			if record.od_customer_code:
				# Show as [od_customer_code] name
				record.display_name = f"[{record.od_customer_code}] {record.name or ''}"
			else:
				# Default hierarchical display name
				names = []
				current = record
				while current:
					names.append(current.name or "")
					current = current.parent_id
				record.display_name = " / ".join(reversed(names))

	@api.model
	def _search_display_name(self, operator, value):
		"""Extend display name search to include 'od_customer_code' field."""
		# Call super to preserve base logic
		domain = super()._search_display_name(operator, value)

		# When searching by name (like/ilike), also look into 'od_customer_code'
		if operator in ('like', 'ilike', '=like', '=ilike'):
			clean_value = value.strip('[] ')  # handle cases like [REF001]
			return ['|',
					('od_customer_code', operator, clean_value),
					('name', operator, value)]

		return domain

	