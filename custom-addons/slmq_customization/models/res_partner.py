from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_member = fields.Boolean()
    member_type = fields.Selection([
        ('member','Member'),('founder','Founder'),('past','Past')
    ])
    membership_id = fields.Many2one('membership.membership')


    @api.constrains('email', 'phone','parent_id')
    def _check_unique_email_phone(self):
        for rec in self:

            domain = [('id', '!=', rec.id)]

            if rec.parent_id:
                domain.append(('id', '!=', rec.parent_id.id))

            if rec.email:
                if self.search(domain + [('email', '=', rec.email)], limit=1):
                    raise ValidationError("Email already exists!")

            if rec.phone:
                if self.search(domain + [('phone', '=', rec.phone)], limit=1):
                    raise ValidationError("Phone already exists!")

    def unlink(self):
        for rec in self:
            # Prevent deleting member contacts
            if rec.is_member:
                raise ValidationError("You cannot delete a member contact.")

        return super().unlink()