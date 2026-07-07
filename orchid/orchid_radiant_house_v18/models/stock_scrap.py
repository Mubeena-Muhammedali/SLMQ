from odoo import models, fields, api, _
from datetime import datetime
from collections import defaultdict
from odoo.exceptions import UserError

class StockScrap(models.Model):
	_inherit = "stock.scrap"

	od_sale_order_line_id = fields.Many2one('sale.order.line', string="Sale Order Line", tracking=True)
	od_production_cost = fields.Float(string="Cost", related="od_sale_order_line_id.od_total_cost", store=True, tracking=True)

	@api.onchange('od_sale_order_line_id')
	def od_onchange_line(self):
		for scrap in self:
			if scrap.od_sale_order_line_id:
				scrap.origin = scrap.od_sale_order_line_id.order_id.name