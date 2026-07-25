# -*- coding: utf-8 -*-
{
    'name': 'Stock Quant In-Date Breakdown',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Track quantity received per date even when quants are merged',
    'description': """
Stock Quant In-Date Breakdown
==============================
Odoo merges incoming stock into a single quant (per product/location/lot/package)
and keeps only the OLDEST in_date on that quant. This module adds a per-date
quantity breakdown so you can see exactly how much stock came in on each date,
even when the quant itself shows one merged total.

Example:
    Day 1: receive 3 units  -> quant qty = 3, in_date = Day 1
    Day 2: receive 5 units  -> quant qty = 8, in_date stays Day 1 (Odoo default)
    This module additionally records:
        Day 1 -> 3
        Day 2 -> 5
    on a new "In Date Lines" tab/column on the quant.
""",
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_quant_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
