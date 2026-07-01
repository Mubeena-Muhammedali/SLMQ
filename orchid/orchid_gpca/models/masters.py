from odoo import api, fields, models


class OrchidProductGroup(models.Model):
    _name = 'od.product.group'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description="Product Groups"

    name = fields.Char(string="Name", tracking=True)
    active = fields.Boolean(string="Active", tracking=True, default=True)