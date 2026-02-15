from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    member_category = fields.Selection([
        ('new', 'New'),
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('old', 'Old'),
        ('founder', 'Founder'),
    ], default='new', string="Member Category")

    is_committee_member = fields.Boolean(default=True, string="Is Committee Member?")
    

    @api.constrains('email', 'phone')
    def _check_duplicate_member(self):
        for rec in self:
            if rec.email or rec.phone:
                domain = [
                    ('id', '!=', rec.id),
                    '|',
                    ('email', '=', rec.email),
                    ('phone', '=', rec.phone)
                ]
                if self.search(domain, limit=1):
                    raise ValidationError("Email or Phone already registered.")

    
    @api.onchange('is_committee_member')
    def _onchange_is_committee_member(self):
        if not self.is_committee_member:
            self.member_category = False
        else:
            self.member_category = 'new'
