# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict

class PurchaserderLine(models.Model):
	_inherit = "purchase.order.line"

	od_last_po_date = fields.Date(string="Last Purchase Date", compute="_compute_od_last_purchase_info")
	od_last_purchase_price = fields.Monetary(
		string="Last Purchase Price",
		currency_field='currency_id',
		compute="_compute_od_last_purchase_info",
	)

	@api.onchange('product_id')
	def od_get_last_po_date(self):
		for line in self:
			line._compute_od_last_purchase_info()

	@api.depends('product_id', 'company_id', 'order_id.currency_id', 'order_id.date_order')
	def _compute_od_last_purchase_info(self):
		for line in self:
			line.od_last_po_date = False
			line.od_last_purchase_price = 0.0
			if not line.product_id:
				continue

			last_line = line._od_get_latest_purchase_line()
			if last_line:
				line.od_last_po_date = last_line.order_id.date_order.date() if last_line.order_id.date_order else False
				line.od_last_purchase_price = line._od_convert_latest_purchase_price(last_line)

	def _od_get_latest_purchase_line(self):
		self.ensure_one()
		params = [self.product_id.id, self.company_id.id]
		exclude_current_line = ""
		if self._origin.id:
			exclude_current_line = "AND pol.id != %s"
			params.append(self._origin.id)

		self.env.cr.execute(f"""
			SELECT pol.id
			FROM purchase_order_line pol
			JOIN purchase_order po ON po.id = pol.order_id
			WHERE pol.product_id = %s
			  AND po.state IN ('purchase', 'done')
			  AND pol.company_id = %s
			  {exclude_current_line}
			ORDER BY po.date_order DESC, pol.id DESC
			LIMIT 1
		""", params)
		result = self.env.cr.fetchone()
		return self.env['purchase.order.line'].browse(result[0]) if result else False

	def _od_convert_latest_purchase_price(self, last_line):
		self.ensure_one()
		if not last_line:
			return 0.0

		price = last_line.price_unit
		from_currency = last_line.currency_id
		to_currency = self.order_id.currency_id

		if from_currency and to_currency and from_currency != to_currency:
			price = from_currency._convert(
				price,
				to_currency,
				self.company_id,
				self.order_id.date_order or fields.Date.today(),
			)
		return price


	@api.depends('product_qty', 'product_uom', 'company_id', 'order_id.partner_id')
	def _compute_price_unit_and_date_planned_and_name(self):
		res = super()._compute_price_unit_and_date_planned_and_name()

		for line in self:
			product = line.product_id
			partner = line.order_id.partner_id

			if not product or not partner:
				continue

			# 1. Try same vendor
			domain = [
				('product_id', '=', product.id),
				('order_id.partner_id', '=', partner.id),
				('order_id.state', 'in', ['purchase', 'done']),
				('company_id','=',line.company_id.id),
			]

			last_line = self.env['purchase.order.line'].search(
				domain, order='create_date desc', limit=1
			)

			# 2. If not found, try any vendor
			if not last_line:
				domain = [
					('product_id', '=', product.id),
					('order_id.state', 'in', ['purchase', 'done']),
					('company_id','=',line.company_id.id),
				]
				last_line = self.env['purchase.order.line'].search(
					domain, order='create_date desc', limit=1
				)

			# 3. If found, apply price (with currency conversion)
			if last_line:
				price = last_line.price_unit
				from_currency = last_line.currency_id
				to_currency = line.order_id.currency_id
				company = line.company_id
				date = line.order_id.date_order or fields.Date.today()

				if from_currency != to_currency:
					price = from_currency._convert(
						price, to_currency, company, date
					)

				line.price_unit = price

		return res
			
