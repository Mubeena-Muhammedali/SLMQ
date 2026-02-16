from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class EventRegistration(models.Model):
    _inherit = 'event.registration'

    is_member_only = fields.Boolean(related='event_id.is_member_only', store=True, readonly=True)


    @api.constrains('partner_id', 'event_id')
    def _check_paid_member(self):
        for rec in self:
            # Skip if not member-only event
            if not rec.event_id.is_member_only:
                continue

            partner = rec.partner_id

            # If partner not selected, try to find using email or phone
            if not partner:
                domain = []
                if rec.email:
                    domain = [('email', '=', rec.email),('email', '!=', False)]
                elif rec.phone:
                    domain = [('phone', '=', rec.phone),('phone', '!=', False)]

                if domain:
                    partner = self.env['res.partner'].search(domain, limit=1)

            # If still no partner → No membership
            if not partner:
                raise ValidationError(
                    _("No registered member found with the provided Email or Phone number. "
                    "Please complete your membership registration first.")
                )

            # Check member category
            if partner.member_category not in ('paid', 'founder'):
                raise ValidationError(
                    _("Only paid or founder members can register for this event. "
                      "Please contact the committee for assistance.")
                )


    @api.onchange('partner_id')
    def _onchange_is_committee_member(self):
        if self.partner_id:
            self.phone = self.partner_id.phone
            self.email = self.partner_id.email
