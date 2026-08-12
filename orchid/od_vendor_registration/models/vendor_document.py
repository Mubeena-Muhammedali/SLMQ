# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OdVendorDocument(models.Model):
    _name = 'od.vendor.document'
    _description = 'Vendor Registration Document'
    _order = 'sequence, id'

    registration_id = fields.Many2one(
        'od.vendor.registration', string='Registration',
        required=True, ondelete='cascade', index=True)

    document_type_id = fields.Many2one(
        'od.vendor.document.type', string='Document',
        required=True, ondelete='restrict')

    sequence = fields.Integer(related='document_type_id.sequence', store=True, readonly=True)
    level = fields.Selection(related='document_type_id.level', store=True, readonly=True, string='Level')
    has_expiry = fields.Boolean(related='document_type_id.has_expiry', readonly=True, string='Expiry?')
    applies_to = fields.Selection(related='document_type_id.applies_to', store=True, readonly=True, string='Applies To')

    attachment = fields.Binary(string='File', attachment=True)
    attachment_filename = fields.Char(string='Filename')
    expiry_date = fields.Date(string='Expiry Date')

    state = fields.Selection([
        ('missing', 'Missing'),
        ('uploaded', 'Uploaded'),
    ], compute='_compute_state', store=True, string='Status')

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
