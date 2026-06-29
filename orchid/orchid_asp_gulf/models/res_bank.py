# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class ResBank(models.Model):
    _inherit = 'res.bank'

    od_bank_iban = fields.Char(string="IBAN")
    od_bank_branch = fields.Char(string="Branch")
