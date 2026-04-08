# -*- coding: utf-8 -*-
from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    bank_details_html = fields.Html(string="Bank Details")
    fax_no = fields.Char(string="Fax No")