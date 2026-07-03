# -*- coding: utf-8 -*-
from itertools import chain

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons import decimal_precision as dp

from odoo.tools import pycompat
from odoo.tools import float_repr

class OrchidVolumeRebate(models.Model):
	_name = "orchid.volume.rebate"
	_description="Volume Rebate Process"

	name = fields.Char('Name', required=True)
	active = fields.Boolean('Active', default=True, help="If unchecked, it will allow you to hide the rebate without removing it.")
	rebate_line_ids = fields.One2many(
	'orchid.volume.rebate.line', 'rebate_id', 'Rebate Lines',
	copy=True)
	company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id.id,)
	partner_id = fields.Many2one('res.partner', string="Customer")
	od_bp_code = fields.Char(string="BP Code", related="partner_id.od_ban_bp", store=True)

	def get_product_rebate_rule(self, product, quantity, partner, date=False, uom_id=False):
		#2
		self.ensure_one()
		return self._compute_rebate_rule([(product, quantity, partner)], date=date, uom_id=uom_id)[product.id]

	def _compute_rebate_rule(self, products_qty_partner, date=False, uom_id=False):
		#3
		self.ensure_one()
		if not date:
			date = self._context.get('date') or fields.Datetime.now()
		if not uom_id and self._context.get('uom'):
			uom_id = self._context['uom']
		if uom_id:
			products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
			products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in enumerate(products_qty_partner)]
		else:
			products = [item[0] for item in products_qty_partner]

		if not products:
			return {}

		categ_ids = {}
		for p in products:
			categ = p.categ_id
			while categ:
				categ_ids[categ.id] = True
				categ = categ.parent_id
		categ_ids = list(categ_ids)

		is_product_template = products[0]._name == "product.template"
		if is_product_template:
			prod_tmpl_ids = [tmpl.id for tmpl in products]
			prod_ids = [p.id for p in
						list(chain.from_iterable([t.product_variant_ids for t in products]))]
		else:
			prod_ids = [product.id for product in products]
			prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

		items = self._compute_rebate_rule_get_items(prod_tmpl_ids, categ_ids)

		results = {}
		for product, qty, partner in products_qty_partner:
			results[product.id] = 0.0
			suitable_rule = False
			qty_uom_id = self._context.get('uom') or product.uom_id.id
			rebate_uom_id = product.uom_id.id
			qty_in_product_uom = qty
			if qty_uom_id != product.uom_id.id:
				try:
					qty_in_product_uom = self.env['uom.uom'].browse([self._context['uom']])._compute_quantity(qty, product.uom_id)
				except UserError:
					pass

			free_qty=0

			rebate_uom = self.env['uom.uom'].browse([qty_uom_id])
			for rule in items:
				
				if is_product_template:
					if rule.product_id and product.id != rule.product_id.id:
						continue
				else:
					if rule.product_id and product.product_tmpl_id.id != rule.product_id.id:
						continue

				if rule.categ_id:
					cat = product.categ_id
					while cat:
						if cat.id == rule.categ_id.id:
							break
						cat = cat.parent_id
					if not cat:
						continue
				if qty_in_product_uom is not False:
					free_qty = int((qty * (rule.rebate_volume_per / 100))) or 0
					suitable_rule = rule
				break
			results[product.id] = (free_qty, suitable_rule and suitable_rule or False)

		return results	

	def _compute_rebate_rule_get_items(self, prod_tmpl_ids, categ_ids):
		#4
		self.ensure_one()
		# self.env['orchid.volume.rebate.line'].flush(['rebate_volume_per', 'company_id'])
		self.env.cr.execute(
			"""
			SELECT
				item.id
			FROM
				orchid_volume_rebate_line AS item
			LEFT JOIN product_category AS categ ON item.categ_id = categ.id
			WHERE
				(item.product_id IS NULL OR item.product_id = any(%s))
				AND (item.categ_id IS NULL OR item.categ_id = any(%s))
				AND (item.rebate_id = %s)
			ORDER BY
				item.applied_on, categ.complete_name desc, item.id desc
			""",
			(prod_tmpl_ids, categ_ids, self.id))

		item_ids = [x[0] for x in self.env.cr.fetchall()]
		return self.env['orchid.volume.rebate.line'].browse(item_ids)

class OrchidVolumeRebateLine(models.Model):
	_name = "orchid.volume.rebate.line"
	_description="Volume Rebate Process Lines"

	rebate_id=fields.Many2one('orchid.volume.rebate', 'Rebate', index=True, ondelete='cascade', required=True)
	applied_on = fields.Selection([
	('2_product_category', 'Product Line'),
	('1_product', 'Product'),
	], "Apply On", required=True,help='Rebate Item applicable on selected option')
	company_id = fields.Many2one('res.company', 'Company',readonly=True, related='rebate_id.company_id', store=True)
	product_id = fields.Many2one('product.template', 'Product', ondelete='cascade', check_company=True,help="Specify a product if this rule only applies to one product. Keep empty otherwise.")
	categ_id = fields.Many2one('product.category', 'Product Line', ondelete='cascade',help="Specify a product category if this rule only applies to products belonging to this category or its children categories. Keep empty otherwise.")
	rebate_volume_per = fields.Float(string="Rebate Volume %")


	
	@api.constrains('product_id', 'categ_id')
	def _check_product_consistency(self):
		for item in self:
			if item.applied_on == "2_product_category" and not item.categ_id:
				raise ValidationError(_("Please specify the category for which this rule should be applied"))
			elif item.applied_on == "1_product" and not item.product_id:
				raise ValidationError(_("Please specify the product for which this rule should be applied"))

	@api.model
	def create(self, vals):
		if vals.get('applied_on', False):
			applied_on = vals['applied_on']
		if applied_on == '2_product_category':
			vals.update(dict(product_id=None))
		elif applied_on == '1_product':
			vals.update(dict(categ_id=None))
		return super(OrchidVolumeRebateLine, self).create(vals)

	def write(self, values):
		if values.get('applied_on', False):
			applied_on = values['applied_on']
			if applied_on == '2_product_category':
				values.update(dict(product_id=None))
			elif applied_on == '1_product':
				values.update(dict(categ_id=None))
		res = super(OrchidVolumeRebateLine, self).write(values)
		# self.flush()
		self.invalidate_cache()
		return res


class SaleOrder(models.Model):
	_inherit = "sale.order"
	od_rebate_id = fields.Many2one('orchid.volume.rebate', 'Volume Rebate', ondelete='restrict')
	od_show_update_rebate = fields.Boolean(string='Has Rebate Changed',help="Technical Field, True if the Rebate was changed;\n"
                                                " this will then display a recomputation button")
	@api.onchange('partner_id')
	def onchange_rebate(self):
		if self.partner_id:
			self.od_rebate_id = self.partner_id.od_rebate_id and self.partner_id.od_rebate_id.id

	@api.onchange('od_rebate_id')
	def _onchange_od_rebate_id(self):
		if self.order_line and self.od_rebate_id and self._origin.od_rebate_id and self._origin.od_rebate_id != self.od_rebate_id:
			self.od_show_update_rebate = True
		else:
			self.od_show_update_rebate = False

	def update_free_qtys(self):
		self.ensure_one()
		lines_to_update = []
		for line in self.order_line:
			product = line.product_id.with_context(
				partner=self.partner_id,
				quantity=line.product_uom_qty,
				date=self.date_order,
				od_rebate_id=self.od_rebate_id.id,
				uom=line.product_uom.id
			)
			od_free_qty = line._od_get_display_rebate(product)
			lines_to_update.append((1, line.id, {'od_free_qty': od_free_qty}))
		self.update({'order_line': lines_to_update})
		self.od_show_update_rebate = False


class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"
	
	def _od_get_display_rebate(self, product):
		#1
		product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.product_uom.id)
		final_rebate, rule_id = self.order_id.od_rebate_id.with_context(product_context).get_product_rebate_rule(product or self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
		return max(0, final_rebate)

	@api.onchange('product_id','product_uom', 'product_uom_qty')
	def rebate_change(self):
		if self.product_id and self.order_id.od_rebate_id:
			self.od_free_qty = self._od_get_display_rebate(self.product_id)

class Partner(models.Model):
	_inherit = "res.partner"
	od_rebate_id = fields.Many2one('orchid.volume.rebate', 'Volume Rebate', ondelete='restrict')