# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OdVendorDocument(models.Model):
    _name = 'od.vendor.document'
    _description = 'Vendor Registration Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    registration_id = fields.Many2one(
        'od.vendor.registration', string='Registration',tracking=True,
        required=True, ondelete='cascade', index=True)

    partner_id = fields.Many2one(
        'res.partner', string='Partner', tracking=True,
        ondelete='cascade', index=True,
        help='Set automatically once the related Registration is approved '
             'and a Partner is created/linked. Lets this document be found '
             'from the Partner\'s Documents smart button.')

    document_type_id = fields.Many2one(
        'od.vendor.document.type', string='Document',tracking=True,
        required=True, ondelete='restrict')

    sequence = fields.Integer(related='document_type_id.sequence', store=True, readonly=True, tracking=True)
    level = fields.Selection(related='document_type_id.level', store=True, readonly=True, string='Level', tracking=True)
    has_expiry = fields.Boolean(related='document_type_id.has_expiry', readonly=True, string='Expiry?', tracking=True)
    applies_to = fields.Selection(related='document_type_id.applies_to', store=True, readonly=True, string='Applies To', tracking=True)

    attachment = fields.Binary(string='File', attachment=True)
    attachment_filename = fields.Char(string='Filename', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)

    state = fields.Selection([
        ('missing', 'Missing'),
        ('uploaded', 'Uploaded'),
    ], compute='_compute_state', store=True, string='Status', tracking=True)

    is_missing_mandatory = fields.Boolean(compute='_compute_state', store=True)
    is_expiry_incomplete = fields.Boolean(compute='_compute_state', store=True)

    _sql_constraints = [
        ('registration_document_type_uniq', 'unique(registration_id, document_type_id)',
         'This document is already listed on the registration.'),
    ]

    @api.depends('attachment', 'level', 'has_expiry', 'expiry_date')
    def _compute_state(self):
        for rec in self:
            rec.state = 'uploaded' if rec.attachment else 'missing'
            rec.is_missing_mandatory = rec.level == 'mandatory' and not rec.attachment
            rec.is_expiry_incomplete = bool(rec.attachment) and rec.has_expiry and not rec.expiry_date
