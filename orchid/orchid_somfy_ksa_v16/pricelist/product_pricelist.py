# -*- coding: utf-8 -*-
from itertools import chain

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons import decimal_precision as dp

from odoo.tools import pycompat, format_datetime, formatLang


class PricelistItem(models.Model):
	_inherit = "product.pricelist.item"
	

	applied_on = fields.Selection(
		selection=[
			('3_global', "All Products"),
			('2_rproduct_brand','Product Brand'),
			('2_qproduct_group','Product Group'),
			('2_qproduct_ftype','Product Type'),
			('2_product_category', "Product Category"),
			('1_product_segment', "Product Segment"),
			('1_product', "Product"),
			('0_product_variant', "Product Variant"),
			
		],
		string="Apply On",
		default='3_global',
		required=True,
		help="Pricelist Item applicable on selected option")
	# applied_on = fields.Selection(selection_add=[('2_rproduct_brand','Product Brand'),('2_qproduct_ftype','Product Type'),('2_qproduct_group','Product Group')],default='3_global')
	orchid_brand_id =  fields.Many2one('orchid.product.brand', string='Brand')
	orchid_type_id =  fields.Many2one('orchid.product.type', string='Type')
	orchid_group_id =  fields.Many2one('orchid.product.group', string='Group')
	od_product_segment_id = fields.Many2one('od.product.segment', string="Product Segment")


	@api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
		'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge', 'orchid_brand_id', 'orchid_type_id', 'orchid_group_id','od_product_segment_id')
	def _compute_name_and_price(self):
		for item in self:
			if item.categ_id and item.applied_on == '2_product_category':
				item.name = _("Category: %s") % (item.categ_id.display_name)
			elif item.product_tmpl_id and item.applied_on == '1_product':
				item.name = _("Product: %s") % (item.product_tmpl_id.display_name)
			elif item.product_id and item.applied_on == '0_product_variant':
				item.name = _("Variant: %s") % (item.product_id.with_context(display_default_code=False).display_name)
			elif item.od_product_segment_id and item.applied_on == '1_product_segment':
				item.name = _("Product Segment: %s") % (item.od_product_segment_id.name)
			elif item.orchid_brand_id and item.applied_on == '2_rproduct_brand':
				item.name = _("Product Brand: %s") % (item.orchid_brand_id.name)
			elif item.orchid_type_id and item.applied_on == '2_qproduct_ftype':
				item.name = _("Product Type: %s") % (item.orchid_type_id.name)
			elif item.orchid_group_id and item.applied_on == '2_qproduct_group':
				item.name = _("Product Group: %s") % (item.orchid_group_id.name)
			else:
				item.name = _("All Products")

			if item.compute_price == 'fixed':
				item.price = formatLang(
					item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id)
			elif item.compute_price == 'percentage':
				item.price = _("%s %% discount", item.percent_price)
			else:
				item.price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount, price=item.price_surcharge)

	@api.constrains('product_id', 'product_tmpl_id', 'categ_id', 'orchid_brand_id', 'orchid_type_id', 'orchid_group_id','od_product_segment_id')
	def _check_product_consistency(self):
		for item in self:
			if item.applied_on == '2_rproduct_brand' and not item.orchid_brand_id:
				raise ValidationError(_("Please specify the product brand for which this rule should be applied"))
			elif item.applied_on == '2_qproduct_group' and not item.orchid_group_id:
				raise ValidationError(_("Please specify the product group for which this rule should be applied"))
			elif item.applied_on == '2_qproduct_ftype' and not item.orchid_type_id:
				raise ValidationError(_("Please specify the product type for which this rule should be applied"))
			elif item.applied_on == "2_product_category" and not item.categ_id:
				raise ValidationError(_("Please specify the category for which this rule should be applied"))
			elif item.applied_on == "1_product_segment" and not item.od_product_segment_id:
				raise ValidationError(_("Please specify the product segment for which this rule should be applied"))
			elif item.applied_on == "1_product" and not item.product_tmpl_id:
				raise ValidationError(_("Please specify the product for which this rule should be applied"))
			elif item.applied_on == "0_product_variant" and not item.product_id:
				raise ValidationError(_("Please specify the product variant for which this rule should be applied"))
			
			
			

	@api.onchange('product_id', 'product_tmpl_id', 'categ_id', 'orchid_brand_id', 'orchid_type_id', 'orchid_group_id','od_product_segment_id')
	def _onchange_rule_content(self):
		if not self.user_has_groups('product.group_sale_pricelist') and not self.env.context.get('default_applied_on', False):
			# If advanced pricelists are disabled (applied_on field is not visible)
			# AND we aren't coming from a specific product template/variant.
			variants_rules = self.filtered('product_id')
			template_rules = (self-variants_rules).filtered('product_tmpl_id')
			variants_rules.update({'applied_on': '0_product_variant'})
			template_rules.update({'applied_on': '1_product'})
			(self-variants_rules-template_rules).update({'applied_on': '3_global'})

	# @api.one
	# @api.depends('categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
	# 	'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge', 'orchid_brand_id', 'orchid_type_id', 'orchid_group_id')
	# def _get_pricelist_item_name_price(self):
	# 	if self.categ_id:
	# 		self.name = _("Category: %s") % (self.categ_id.name)
	# 	elif self.product_tmpl_id:
	# 		self.name = self.product_tmpl_id.name
	# 	elif self.product_id:
	# 		self.name = self.product_id.display_name.replace('[%s]' % self.product_id.code, '')
	# 	elif self.orchid_brand_id:
	# 		self.name = _("Product Brand: %s") % (self.orchid_brand_id.name)
	# 	elif self.orchid_type_id:
	# 		self.name = _("Product Type: %s") % (self.orchid_type_id.name)
	# 	elif self.orchid_group_id:
	# 		self.name = _("Product Group: %s") % (self.orchid_group_id.name)
	# 	else:
	# 		self.name = _("All Products")

	# 	if self.compute_price == 'fixed':
	# 		self.price = ("%s %s") % (self.fixed_price, self.pricelist_id.currency_id.name)
	# 	elif self.compute_price == 'percentage':
	# 		self.price = _("%s %% discount") % (self.percent_price)
	# 	else:
	# 		self.price = _("%s %% discount and %s surcharge") % (self.price_discount, self.price_surcharge)

	# @api.onchange('applied_on')
	# def _onchange_applied_on(self):
	# 	if self.applied_on != '0_product_variant':
	# 		self.product_id = False
	# 	if self.applied_on != '1_product':
	# 		self.product_tmpl_id = False
	# 	if self.applied_on != '2_product_category':
	# 		self.categ_id = False
	# 	if self.applied_on != '2_rproduct_brand':
	# 		self.orchid_brand_id = False
	# 	if self.applied_on != '2_qproduct_ftype':
	# 		self.orchid_type_id = False
	# 	if self.applied_on != '2_qproduct_group':
	# 		self.orchid_group_id = False

	@api.model_create_multi
	def create(self, vals_list):
		for values in vals_list:
			if values.get('applied_on', False):
				# Ensure item consistency for later searches.
				applied_on = values['applied_on']
				if applied_on == '3_global':
					values.update(dict(product_id=None, product_tmpl_id=None, categ_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
				elif applied_on == '2_rproduct_brand':
					values.update(dict(product_id=None, product_tmpl_id=None,categ_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
				elif applied_on == '2_qproduct_group':
					values.update(dict(product_id=None, product_tmpl_id=None,categ_id=None, orchid_brand_id=None, orchid_type_id=None, od_product_segment_id=None))
				elif applied_on == '2_qproduct_ftype':
					values.update(dict(product_id=None, product_tmpl_id=None,categ_id=None, orchid_brand_id=None, orchid_group_id=None, od_product_segment_id=None))
				elif applied_on == '2_product_category':
					values.update(dict(product_id=None, product_tmpl_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
				elif applied_on == '1_product_segment':
					values.update(dict(product_id=None, product_tmpl_id=None, categ_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None))
				elif applied_on == '1_product':
					values.update(dict(product_id=None, categ_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
				elif applied_on == '0_product_variant':
					values.update(dict(categ_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
				
		return super().create(vals_list)

	def write(self, values):
		if values.get('applied_on', False):
			# Ensure item consistency for later searches.
			applied_on = values['applied_on']
			if applied_on == '3_global':
				values.update(dict(product_id=None, product_tmpl_id=None, categ_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
			elif applied_on == '2_rproduct_brand':
				values.update(dict(product_id=None, product_tmpl_id=None,categ_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
			elif applied_on == '2_qproduct_group':
				values.update(dict(product_id=None, product_tmpl_id=None,categ_id=None, orchid_brand_id=None, orchid_type_id=None, od_product_segment_id=None))
			elif applied_on == '2_qproduct_ftype':
				values.update(dict(product_id=None, product_tmpl_id=None,categ_id=None, orchid_brand_id=None, orchid_group_id=None, od_product_segment_id=None))
			elif applied_on == '2_product_category':
				values.update(dict(product_id=None, product_tmpl_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
			elif applied_on == '1_product_segment':
				values.update(dict(product_id=None, product_tmpl_id=None, categ_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None))
			elif applied_on == '1_product':
				values.update(dict(product_id=None, categ_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
			elif applied_on == '0_product_variant':
				values.update(dict(categ_id=None, orchid_brand_id=None, orchid_type_id=None, orchid_group_id=None, od_product_segment_id=None))
			
		return super().write(values)

	def _is_applicable_for(self, product, qty_in_product_uom):
		"""Check whether the current rule is valid for the given product & qty.

		Note: self.ensure_one()

		:param product: product record (product.product/product.template)
		:param float qty_in_product_uom: quantity, expressed in product UoM
		:returns: Whether rules is valid or not
		:rtype: bool
		"""
		self.ensure_one()
		product.ensure_one()
		res = True

		is_product_template = product._name == 'product.template'
		if self.min_quantity and qty_in_product_uom < self.min_quantity:
			res = False

		elif self.orchid_brand_id:
			# Applied on a specific brand
			cat = product.orchid_brand_id
			while cat:
				if cat.id == self.orchid_brand_id.id:
					break
				# cat = cat.parent_id
			if not cat:
				res = False
		elif self.orchid_group_id:
			# Applied on a specific group
			cat = product.orchid_group_id
			while cat:
				if cat.id == self.orchid_group_id.id:
					break
				# cat = cat.parent_id
			if not cat:
				res = False
		elif self.orchid_type_id:
			# Applied on a specific type
			cat = product.orchid_type_id
			while cat:
				if cat.id == self.orchid_type_id.id:
					break
				# cat = cat.parent_id
			if not cat:
				res = False
		

		elif self.categ_id:
			# Applied on a specific category
			cat = product.categ_id
			while cat:
				if cat.id == self.categ_id.id:
					break
				cat = cat.parent_id
			if not cat:
				res = False
		else:
			if self.od_product_segment_id:
				# Applied on a specific product segment
				cat = product.od_product_segment_id
				while cat:
					for c in cat:
						if c.id == self.od_product_segment_id.id:
							cat = c
							break
					if cat.id == self.od_product_segment_id.id:
						break
					# cat = cat.parent_id
					# if cat.id == self.od_product_segment_id.id:
					# 	break
					# cat = cat.parent_id
				if not cat:
					res = False

			# Applied on a specific product template/variant
			elif is_product_template:
				if self.product_tmpl_id and product.id != self.product_tmpl_id.id:
					res = False
				elif self.product_id and not (
					product.product_variant_count == 1
					and product.product_variant_id.id == self.product_id.id
				):
					# product self acceptable on template if has only one variant
					res = False
			else:
				if self.product_tmpl_id and product.product_tmpl_id.id != self.product_tmpl_id.id:
					res = False
				elif self.product_id and product.id != self.product_id.id:
					res = False

		return res

	def _compute_base_price(self, product, quantity, uom, date, target_currency):
		""" Compute the base price for a given rule

		:param product: recordset of product (product.product/product.template)
		:param float qty: quantity of products requested (in given uom)
		:param uom: unit of measure (uom.uom record)
		:param datetime date: date to use for price computation and currency conversions
		:param target_currency: pricelist currency

		:returns: base price, expressed in provided pricelist currency
		:rtype: float
		"""
		target_currency.ensure_one()

		rule_base = self.base or 'list_price'
		if rule_base == 'pricelist' and self.base_pricelist_id:
			price = self.base_pricelist_id._get_product_price(product, quantity, uom, date)
			src_currency = self.base_pricelist_id.currency_id
		elif rule_base == "standard_price":
			src_currency = product.cost_currency_id
			price = product.price_compute(rule_base, uom=uom, date=date)[product.id]
		else: # list_price
			src_currency = product.currency_id
			price = product.price_compute(rule_base, uom=uom, date=date)[product.id]

		# orchid change-----product prices are in euro. no conversion needed
		# if src_currency != target_currency:
		#     price = src_currency._convert(price, target_currency, self.env.company, date, round=False)
		print("priceeeeeeeeeeeee",price)
		return price
class Pricelist(models.Model):
	_inherit = "product.pricelist"

	partner_id = fields.Many2one('res.partner', string="Customer")
	od_bp_code = fields.Char(string="BP Code", related="partner_id.od_ban_bp", store=True)

	def _get_applicable_rules_domain(self, products, date, **kwargs):
		if products._name == 'product.template':
			templates_domain = ('product_tmpl_id', 'in', products.ids)
			products_domain = ('product_id.product_tmpl_id', 'in', products.ids)
		else:
			templates_domain = ('product_tmpl_id', 'in', products.product_tmpl_id.ids)
			products_domain = ('product_id', 'in', products.ids)

		return [
			('pricelist_id', '=', self.id),
			'|', ('orchid_brand_id', '=', False), ('orchid_brand_id', 'in', products.orchid_brand_id.ids),
			'|', ('orchid_group_id', '=', False), ('orchid_group_id', 'in', products.orchid_group_id.ids),
			'|', ('orchid_type_id', '=', False), ('orchid_type_id', 'in', products.orchid_type_id.ids),
			'|', ('od_product_segment_id', '=', False), ('od_product_segment_id', 'in', products.od_product_segment_id.ids),
			'|', ('categ_id', '=', False), ('categ_id', 'child_of', products.categ_id.ids),
			'|', ('product_tmpl_id', '=', False), templates_domain,
			'|', ('product_id', '=', False), products_domain,
			'|', ('date_start', '=', False), ('date_start', '<=', date),
			'|', ('date_end', '=', False), ('date_end', '>=', date),
		]

	# @api.multi
	# def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
	# 	""" Low-level method - Mono pricelist, multi products
	# 	Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

	# 	If date in context: Date of the pricelist (%Y-%m-%d)

	# 		:param products_qty_partner: list of typles products, quantity, partner
	# 		:param datetime date: validity date
	# 		:param ID uom_id: intermediate unit of measure
	# 	"""
	# 	self.ensure_one()
	# 	if not date:
	# 		date = self._context.get('date') or fields.Date.context_today(self)
	# 	if not uom_id and self._context.get('uom'):
	# 		uom_id = self._context['uom']
	# 	if uom_id:
	# 		# rebrowse with uom if given
	# 		products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
	# 		products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in enumerate(products_qty_partner)]
	# 	else:
	# 		products = [item[0] for item in products_qty_partner]

	# 	if not products:
	# 		return {}

	# 	categ_ids = {}
	# 	brand_ids = {}
	# 	type_ids = {}
	# 	group_ids = {}
	# 	for p in products:
	# 		categ = p.categ_id
	# 		while categ:
	# 			categ_ids[categ.id] = True
	# 			categ = categ.parent_id
	# 	categ_ids = list(categ_ids)

	# 	for pr in products:
	# 		brand = pr.orchid_brand_id
	# 		if brand:
	# 			brand_ids[brand.id] = True
	# 	brand_ids = list(brand_ids)
	# 	for pr in products:
	# 		types = pr.orchid_type_id
	# 		if types:
	# 			type_ids[types.id] = True
	# 	type_ids = list(type_ids)

	# 	for pr in products:
	# 		group = pr.orchid_group_id
	# 		if group:
	# 			group_ids[group.id] = True
	# 	group_ids = list(group_ids)

	# 	is_product_template = products[0]._name == "product.template"
	# 	if is_product_template:
	# 		prod_tmpl_ids = [tmpl.id for tmpl in products]
	# 		# all variants of all products
	# 		prod_ids = [p.id for p in
	# 					list(chain.from_iterable([t.product_variant_ids for t in products]))]
	# 	else:
	# 		prod_ids = [product.id for product in products]
	# 		prod_tmpl_ids = [product.product_tmpl_id.id for product in products]
		
	# 	# Load all rules
	# 	self._cr.execute(
	# 		'SELECT item.id '
	# 		'FROM product_pricelist_item AS item '
	# 		'LEFT JOIN product_category AS categ '
	# 		'ON item.categ_id = categ.id '
	# 		'WHERE (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))'
	# 		'AND (item.product_id IS NULL OR item.product_id = any(%s))'
	# 		'AND (item.categ_id IS NULL OR item.categ_id = any(%s)) '
	# 		'AND (item.pricelist_id = %s) '
	# 		'AND (item.date_start IS NULL OR item.date_start<=%s) '
	# 		'AND (item.date_end IS NULL OR item.date_end>=%s)'
	# 		'AND (item.orchid_brand_id IS NULL OR item.orchid_brand_id = any(%s)) '
	# 		'AND (item.orchid_type_id IS NULL OR item.orchid_type_id = any(%s)) '
	# 		'AND (item.orchid_group_id IS NULL OR item.orchid_group_id = any(%s)) '
	# 		'ORDER BY item.applied_on, item.min_quantity desc, categ.parent_left desc',
	# 		(prod_tmpl_ids, prod_ids, categ_ids, self.id, date, date, brand_ids, type_ids, group_ids))

	# 	item_ids = [x[0] for x in self._cr.fetchall()]
	# 	items = self.env['product.pricelist.item'].browse(item_ids)
	# 	results = {}
	# 	for product, qty, partner in products_qty_partner:
	# 		results[product.id] = 0.0
	# 		suitable_rule = False

	# 		# Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
	# 		# An intermediary unit price may be computed according to a different UoM, in
	# 		# which case the price_uom_id contains that UoM.
	# 		# The final price will be converted to match `qty_uom_id`.
	# 		qty_uom_id = self._context.get('uom') or product.uom_id.id
	# 		price_uom_id = product.uom_id.id
	# 		qty_in_product_uom = qty
	# 		if qty_uom_id != product.uom_id.id:
	# 			try:
	# 				qty_in_product_uom = self.env['product.uom'].browse([self._context['uom']])._compute_quantity(qty, product.uom_id)
	# 			except UserError:
	# 				# Ignored - incompatible UoM in context, use default product UoM
	# 				pass

	# 		# if Public user try to access standard price from website sale, need to call price_compute.
	# 		# TDE SURPRISE: product can actually be a template
	# 		price = product.price_compute('list_price')[product.id]

	# 		price_uom = self.env['product.uom'].browse([qty_uom_id])
	# 		for rule in items:
	# 			if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
	# 				continue
	# 			if is_product_template:
	# 				if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
	# 					continue
	# 				if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
	# 					# product rule acceptable on template if has only one variant
	# 					continue
	# 			else:
	# 				if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
	# 					continue
	# 				if rule.product_id and product.id != rule.product_id.id:
	# 					continue

	# 			if rule.categ_id:
	# 				cat = product.categ_id
	# 				while cat:
	# 					if cat.id == rule.categ_id.id:
	# 						break
	# 					cat = cat.parent_id
	# 				if not cat:
	# 					continue

	# 			if rule.orchid_brand_id:
	# 				brand = product.orchid_brand_id
	# 				while brand:
	# 					if brand.id == rule.orchid_brand_id.id:
	# 						break
	# 				if not brand:
	# 					continue

	# 			if rule.base == 'pricelist' and rule.base_pricelist_id:
	# 				price_tmp = rule.base_pricelist_id._compute_price_rule([(product, qty, partner)])[product.id][0]  # TDE: 0 = price, 1 = rule
	# 				price = rule.base_pricelist_id.currency_id.compute(price_tmp, self.currency_id, round=False)
	# 			else:
	# 				# if base option is public price take sale price else cost price of product
	# 				# price_compute returns the price in the context UoM, i.e. qty_uom_id
	# 				price = product.price_compute(rule.base)[product.id]

	# 			convert_to_price_uom = (lambda price: product.uom_id._compute_price(price, price_uom))

	# 			if price is not False:
	# 				if rule.compute_price == 'fixed':
	# 					price = convert_to_price_uom(rule.fixed_price)
	# 				elif rule.compute_price == 'percentage':
	# 					price = (price - (price * (rule.percent_price / 100))) or 0.0
	# 				else:
	# 					# complete formula
	# 					price_limit = price
	# 					price = (price - (price * (rule.price_discount / 100))) or 0.0
	# 					if rule.price_round:
	# 						price = tools.float_round(price, precision_rounding=rule.price_round)

	# 					if rule.price_surcharge:
	# 						price_surcharge = convert_to_price_uom(rule.price_surcharge)
	# 						price += price_surcharge

	# 					if rule.price_min_margin:
	# 						price_min_margin = convert_to_price_uom(rule.price_min_margin)
	# 						price = max(price, price_limit + price_min_margin)

	# 					if rule.price_max_margin:
	# 						price_max_margin = convert_to_price_uom(rule.price_max_margin)
	# 						price = min(price, price_limit + price_max_margin)
	# 				suitable_rule = rule
	# 			break
	# 		# Final price conversion into pricelist currency

	# 		#commented as the product price is already in euro and need not to convert to the pricelist currency,euro
	# 		# if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
	# 		# 	if suitable_rule.base == 'standard_price':
	# 		# 		# The cost of the product is always in the company currency
	# 		# 		price = product.cost_currency_id.compute(price, self.currency_id, round=False)
	# 		# 	else:
	# 		# 		price = product.currency_id.compute(price, self.currency_id, round=False)

	# 		results[product.id] = (price, suitable_rule and suitable_rule.id or False)

	# 	return results