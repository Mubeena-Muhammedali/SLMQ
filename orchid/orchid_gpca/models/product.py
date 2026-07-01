from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    od_group_id = fields.Many2one('od.product.group',string="Group", tracking=True)