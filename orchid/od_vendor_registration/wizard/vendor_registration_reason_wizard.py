# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class OdVendorRegistrationReasonWizard(models.TransientModel):
    _name = 'od.vendor.registration.reason.wizard'
    _description = 'Vendor Registration Reject/Cancel Reason'

    registration_id = fields.Many2one(
        'od.vendor.registration', string='Registration', required=True)
    reason = fields.Text(string='Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise UserError(_('Please enter a reason before continuing.'))
        self.registration_id.action_reject(reason=self.reason)
        return {'type': 'ir.actions.act_window_close'}
