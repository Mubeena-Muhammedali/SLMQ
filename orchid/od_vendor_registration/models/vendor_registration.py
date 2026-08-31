# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class OdVendorRegistration(models.Model):
    _name = 'od.vendor.registration'
    _description = 'Vendor Registration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ------------------------------------------------------------------
    # Identification / partner-master-like fields
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Name', tracking=True, required=True,
        help='Company / vendor legal name.')
    phone = fields.Char(string='Phone', tracking=True)
    email = fields.Char(string='Email', tracking=True)

    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one(
        'res.country.state', string='State',
        domain="[('country_id', '=', country_id)]")
    zip = fields.Char(string='Zip')
    country_id = fields.Many2one('res.country', string='Country')

    cr_number = fields.Char(
        string='CR',
        tracking=True,
    )
    vat_number = fields.Char(
        string='VAT',
        tracking=True,
    )
    contact_person = fields.Char(
        string='Contact Person',
        tracking=True,
    )
    # ------------------------------------------------------------------
    # Banking - plain char fields on the registration; mapped onto a
    # res.partner.bank record (linked via partner_id.bank_ids) on approval.
    # ------------------------------------------------------------------
    iban = fields.Char(
        string='IBAN',
        tracking=True,
    )
    bank_name = fields.Char(
        string='Bank Name',
        tracking=True,
    )
    category = fields.Selection([
        ('ksa_based_vendor', 'KSA-based Vendor'),
        ('onsite_work_vendor', 'On-site Work Vendor'),
        ('technical_engineering_vendor', 'Technical/Engineering Vendor'),
    ], string='Category', tracking=True)

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('register', 'Registered'),
        ('review', 'Reviewed'),
        ('approve', 'Approved'),
        ('reject', 'Rejected')
    ], string='Status', default='register', tracking=True, copy=False)

    access_token = fields.Char(
        string='Access Token', copy=False, default=lambda self: str(uuid.uuid4()),
        readonly=True)
    registration_url = fields.Char(
        string='Registration URL', compute='_compute_registration_url',
        help='Public link to share with the vendor so they can fill in / '
             'update their own registration data.')

    partner_id = fields.Many2one(
        'res.partner', string='Vendor (Partner)', copy=False, readonly=True,
        help='Vendor contact created automatically on approval.')

    submitted_date = fields.Datetime(string='Submitted On', readonly=True, copy=False)
    reviewed_date = fields.Datetime(string='Reviewed On', readonly=True, copy=False)
    approved_date = fields.Datetime(string='Approved On', readonly=True, copy=False)
    rejected_date = fields.Datetime(string='Rejected On', tracking=True, copy=False)

    reject_reason = fields.Text(string='Reject Reason', tracking=True, copy=False)

    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    # ------------------------------------------------------------------
    # Required Documents Checklist
    # ------------------------------------------------------------------
    document_ids = fields.One2many(
        'od.vendor.document', 'registration_id', string='Documents')
    document_count = fields.Integer(compute='_compute_document_stats')
    missing_mandatory_count = fields.Integer(
        compute='_compute_document_stats',
        help='Mandatory documents (for this vendor Category) not yet uploaded.')

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('document_ids.state', 'document_ids.level')
    def _compute_document_stats(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)
            rec.missing_mandatory_count = len(rec.document_ids.filtered(
                lambda d: d.level == 'mandatory' and d.state == 'missing'))

    @api.depends('access_token')
    def _compute_registration_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.id and rec.access_token:
                rec.registration_url = '%s/vendor/register/%s/%s' % (
                    base_url, rec.id, rec.access_token)
            else:
                rec.registration_url = False
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.write({'submitted_date': fields.Datetime.now()})
        records._sync_document_lines()
        return records

    @api.onchange('category')
    def _onchange_category_sync_documents(self):
        self._sync_document_lines()

    # ------------------------------------------------------------------
    # Required Documents Checklist - sync from the od.vendor.document.type
    # master list. "All Vendors" documents are always added; category
    # specific ones (KSA-based / On-site / Technical-Engineering) are
    # added once that Category is selected. Existing lines (and any file
    # already uploaded against them) are never removed automatically.
    # ------------------------------------------------------------------
    def _sync_document_lines(self):
        DocType = self.env['od.vendor.document.type'].sudo()
        Document = self.env['od.vendor.document'].sudo()
        for rec in self:
            domain = [('applies_to', '=', 'all')]
            if rec.category:
                domain = ['|'] + domain + [('applies_to', '=', rec.category)]
            applicable = DocType.search(domain)
            existing_type_ids = set(rec.document_ids.document_type_id.ids)
            to_add = applicable.filtered(lambda dt: dt.id not in existing_type_ids)
            for doc_type in to_add:
                if rec.id:
                    Document.create({
                        'registration_id': rec.id,
                        'document_type_id': doc_type.id,
                    })
                else:
                    # record not saved yet (e.g. onchange on a new form):
                    # stage the line so it is created together with the parent
                    rec.document_ids = [(0, 0, {'document_type_id': doc_type.id})]

    # ------------------------------------------------------------------
    # CRUD guard - only 'register' state is editable by non-internal users
    # ------------------------------------------------------------------
    def write(self, vals):
        # Internal (backoffice) users may always edit. External writes are
        # performed through the sudo()'d controller, so we specifically
        # guard against state changes happening while not in 'register',
        # unless the write is explicitly changing the workflow state via
        # the action_* methods (which set state themselves).
        if not self.env.user.has_group('base.group_user'):
            for rec in self:
                if rec.state != 'register' and 'state' not in vals:
                    raise UserError(_(
                        'This registration is no longer editable. It is '
                        'currently under review or has already been approved.'))
        result = super().write(vals)
        if 'category' in vals:
            self._sync_document_lines()
        return result

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def action_reset_to_register(self):
        """Internal user rejects the submission / sends it back for
        vendor correction. A reason is mandatory and is logged on the
        chatter so there is always a record of why it was sent back."""
        for rec in self:
            if rec.state not in ('review', 'reject'):
                raise UserError(_('Only registrations in the "Reviewed" or "Rejected" records can be reset to the "Register".'))
            rec.write({'state': 'register'})

    def action_review(self):
        """Manual transition, e.g. an internal user pulls a draft into review."""
        for rec in self:
            if rec.state != 'register':
                raise UserError(_('Only registrations in the "Registered" state can be reviewed.'))

            missing_docs = rec.document_ids.filtered(
                lambda d: d.level == 'mandatory' and d.state == 'missing')
            if missing_docs:
                raise UserError(_(
                    'The following mandatory documents are still missing:\n- %s'
                ) % '\n- '.join(missing_docs.mapped('document_type_id.name')))

            incomplete_expiry = rec.document_ids.filtered('is_expiry_incomplete')
            if incomplete_expiry:
                raise UserError(_(
                    'Please provide an Expiry Date for the following uploaded '
                    'documents:\n- %s'
                ) % '\n- '.join(incomplete_expiry.mapped('document_type_id.name')))
                
            rec.write({
                'state': 'review',
                'reviewed_date': fields.Datetime.now(),
            })

    def action_approve(self):
        """Approve the registration and create/link a res.partner vendor."""
        for rec in self:
            if rec.state != 'review':
                raise UserError(_('Only registrations under "Reviewed" records can be approved.'))

            partner_vals = {
                'name': rec.name,
                'phone': rec.phone,
                'email': rec.email,
                'street': rec.street,
                'street2': rec.street2,
                'city': rec.city,
                'state_id': rec.state_id.id,
                'zip': rec.zip,
                'country_id': rec.country_id.id,
                'vat': rec.vat_number,
                'od_cr_number': rec.cr_number,
                'od_category': rec.category,
                'company_type': 'company',
                'od_vendor_code': self.env['ir.sequence'].next_by_code('od.vendor.code'),
                'supplier_rank': 1,
            }
            partner = self.env['res.partner'].sudo().create(partner_vals)

            if rec.contact_person:
                self.env['res.partner'].sudo().create({
                    'name': rec.contact_person,
                    'parent_id': partner.id,
                    'type': 'contact',
                    'company_type': 'person',
                    'phone': rec.phone,
                    'email': rec.email,
                })

            if rec.iban or rec.bank_name:
                bank = False
                if rec.bank_name:
                    bank = self.env['res.bank'].sudo().search(
                        [('name', '=', rec.bank_name)], limit=1)
                    if not bank:
                        bank = self.env['res.bank'].sudo().create({'name': rec.bank_name})
                self.env['res.partner.bank'].sudo().create({
                    'acc_number': rec.iban,
                    'partner_id': partner.id,
                    'bank_id': bank.id if bank else False,
                })

            rec.write({
                'state': 'approve',
                'partner_id': partner.id,
                'approved_date': fields.Datetime.now(),
            })

    def action_reject(self, reason=None):
        """Reject the registration. A reason is mandatory and is logged
        on the chatter."""
        if not reason or not reason.strip():
            raise UserError(_('Please provide a reason for rejecting this registration.'))
        for rec in self:
            if rec.state not in ('review', 'register'):
                raise UserError(_('Only registrations under "Reviewed" or "Registered" records can be rejected.'))
            rec.write({'state': 'reject', 'reject_reason': reason, 'rejected_date': fields.Datetime.now()})

    def action_open_reject_wizard(self):
        """Opens the mandatory-comment wizard before rejecting."""
        self.ensure_one()
        return self._open_reason_wizard()

    def _open_reason_wizard(self):
        view = self.env.ref(
            'od_vendor_registration.view_od_vendor_registration_reason_wizard_form')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Registration'),
            'res_model': 'od.vendor.registration.reason.wizard',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': {
                'default_registration_id': self.id,
            },
        }


    @api.model
    def action_show_self_service_link(self):
        """Show the generic self-service registration URL."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        wizard = self.env['od.vendor.registration.link.wizard'].create({
            'link': '%s/vendor/register' % base_url,
        })

        view = self.env.ref(
            'od_vendor_registration.view_od_vendor_registration_link_wizard_form'
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor Registration Link'),
            'res_model': 'od.vendor.registration.link.wizard',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_id': wizard.id,
            'target': 'new',
        }

    def action_open_partner(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Vendor'),
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
            'target': 'current',
        }

    def unlink(self):
        for rec in self:
            if rec.state not in ('register', 'reject'):
                raise UserError(_(
                    'You can only delete vendor registrations in '
                    '"Registered" or "Cancelled" records.'
                ))
        return super().unlink()
