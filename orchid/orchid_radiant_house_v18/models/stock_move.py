# -*- coding: utf-8 -*-
from odoo import fields, models

class StockMove(models.Model):
    _inherit = "stock.move"

    od_qty_on_hand = fields.Float(
        string="Qty On Hand",
        related="product_id.qty_available",
        readonly=True,
    )