from odoo import models, api
from odoo.exceptions import ValidationError

class EventRegistration(models.Model):
    _inherit = 'event.registration'

    @api.constrains('partner_id')
    def _check_paid_member(self):
        for rec in self:
            partner = rec.partner_id
            if partner.member_category != 'paid':
                raise ValidationError("Only Paid Members can register for this event.")

    @api.onchange('partner_id')
    def _onchange_is_committee_member(self):
        if self.partner_id:
            self.phone = self.partner_id.phone
            self.email = self.partner_id.email
