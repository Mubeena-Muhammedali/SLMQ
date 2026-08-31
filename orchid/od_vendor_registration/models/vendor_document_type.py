# -*- coding: utf-8 -*-
from odoo import fields, models


class OdVendorDocumentType(models.Model):
    _name = 'od.vendor.document.type'
    _description = 'Vendor Document Type'
    _order = 'sequence, id'

    name = fields.Char(string='Document', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    level = fields.Selection([
        ('mandatory', 'Mandatory'),
        ('recommended', 'Recommended'),
        ('conditional', 'Optional'),
    ], string='Level', required=True, default='mandatory',
        help='Mandatory documents block Approval when missing. Recommended '
             'and Conditional documents are shown on the checklist but do '
             'not block Approval.')
    has_expiry = fields.Boolean(
        string='Expiry?',
        help='This document is expiry-tracked and feeds the monitoring '
             'cycle. An Expiry Date is requested once the document is '
             'uploaded.')
    applies_to = fields.Selection([
        ('all', 'All Vendors'),
        ('ksa_based_vendor', 'KSA-based Vendors'),
        ('onsite_work_vendor', 'On-site Work Vendors'),
        ('technical_engineering_vendor', 'Technical/Engineering Vendors'),
    ], string='Applies To', required=True, default='all',
        help='Vendor category this document is required/relevant for. '
             '"All Vendors" is always shown, the other options are only '
             'shown when the registration/vendor Category matches.')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_applies_to_uniq', 'unique(name, applies_to)',
         'A document type with this name already exists for this vendor category.'),
    ]
