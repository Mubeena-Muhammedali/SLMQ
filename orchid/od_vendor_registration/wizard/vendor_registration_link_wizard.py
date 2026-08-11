# -*- coding: utf-8 -*-
from odoo import fields, models


class OdVendorRegistrationLinkWizard(models.TransientModel):
    _name = 'od.vendor.registration.link.wizard'
    _description = 'Vendor Registration Link'

    link = fields.Char(string='Registration Link', readonly=True)
