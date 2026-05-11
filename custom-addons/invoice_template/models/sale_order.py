# -*- coding: utf-8 -*-
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    report_total_pages = fields.Integer(
        string='Report Total Pages',
        default=1,
        store=False,  # not stored in DB
    )