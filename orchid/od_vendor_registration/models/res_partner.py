
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    od_cr_number = fields.Char(
        string='CR',
        copy=False,
    )
    od_category = fields.Selection([
        ('ksa_based_vendor', 'KSA-based Vendor'),
        ('onsite_work_vendor', 'On-site Work Vendor'),
        ('technical_engineering_vendor', 'Technical/Engineering Vendor'),
    ], string='Category', tracking=True)
    od_vendor_code = fields.Char(
        string='Vendor ID',
        copy=False,
        readonly=True,
        index=True,
    )