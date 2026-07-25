# -*- coding: utf-8 -*-
from odoo import fields, models


class OdStockQuantInDate(models.Model):
    _name = 'od.stock.quant.in.date'
    _description = 'Stock Quant In-Date'
    _order = 'in_date desc'

    quant_id = fields.Many2one(
        'stock.quant', string='Quant', ondelete='cascade',
        required=True, index=True,
    )
    product_id = fields.Many2one(
        related='quant_id.product_id', store=True, string='Product',
    )
    location_id = fields.Many2one(
        related='quant_id.location_id', store=True, string='Location',
    )
    in_date = fields.Date(string='In Date', required=True)
    quantity = fields.Float(string='Quantity Received', digits='Product Unit of Measure')

    _sql_constraints = [
        (
            'quant_date_uniq',
            'unique(quant_id, in_date)',
            'Only one breakdown line is allowed per quant per date.',
        )
    ]
