from odoo import models, fields

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    iban = fields.Char(string="IBAN")