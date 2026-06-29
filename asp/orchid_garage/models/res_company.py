from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    sub_branch_image = fields.Image(
        string="Sub Branch Image",
        max_width=1920,
        max_height=1920,
    )