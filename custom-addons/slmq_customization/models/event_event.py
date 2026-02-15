from odoo import models, fields

class EventEvent(models.Model):
    _inherit = 'event.event'

    is_member_only = fields.Boolean(string="Members Only Event")
