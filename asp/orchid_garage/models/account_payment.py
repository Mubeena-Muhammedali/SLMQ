from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'


    od_sale_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        copy=False
    )