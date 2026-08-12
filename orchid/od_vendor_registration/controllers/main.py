# -*- coding: utf-8 -*-
import base64

from odoo import http
from odoo.http import request


class OdVendorRegistrationController(http.Controller):
    """
    Public, token-protected vendor registration form.

    Deliberately does NOT depend on the 'website' module - these are plain
    http routes (auth='public') that render self-contained HTML via QWeb,
    so this module works on a database that doesn't have the Website app
    installed (or where installing it would pull in unrelated broken
    modules).
    """

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _od_get_registration(self, reg_id, token):
        return request.env['od.vendor.registration'].sudo().search([
            ('id', '=', reg_id),
            ('access_token', '=', token),
        ], limit=1)

    def _od_vals_from_post(self, post):
        return {
            'name': post.get('name'),
            'phone': post.get('phone'),
            'email': post.get('email'),
            'street': post.get('street'),
            'street2': post.get('street2'),
            'city': post.get('city'),
            'zip': post.get('zip'),
            'country_id': int(post['country_id']) if post.get('country_id') else False,
            'state_id': int(post['state_id']) if post.get('state_id') else False,
            'vat_number': post.get('vat_number'),
            'cr_number': post.get('cr_number'),
            'contact_person': post.get('contact_person'),
            'iban': post.get('iban'),
            'bank_name': post.get('bank_name'),
            'category': post.get('category') or False,
        }

    def _od_get_doc_types(self):
        return request.env['od.vendor.document.type'].sudo().search(
            [], order='sequence, id')

    def _od_docs_by_type(self, registration):
        """{document_type_id: od.vendor.document record} for prefill /
        showing already-uploaded filenames when the vendor reopens the
        link, and building the doc_types by 'applies_to' bucket used on
        the public template."""
        if not registration:
            return {}
        return {doc.document_type_id.id: doc for doc in registration.sudo().document_ids}

    def _od_save_documents(self, registration, post):
        """Persist any uploaded files / expiry dates against the
        registration's document checklist lines (od.vendor.document),
        matched by the `doc_<document_type_id>` / `doc_<document_type_id>
        _expiry` field names rendered on the public form."""
        registration = registration.sudo()
        registration._sync_document_lines()
        files = request.httprequest.files
        for doc in registration.document_ids:
            file_key = 'doc_%s' % doc.document_type_id.id
            expiry_key = 'doc_%s_expiry' % doc.document_type_id.id
            vals = {}
            upload = files.get(file_key)
            if upload and upload.filename:
                vals['attachment'] = base64.b64encode(upload.read())
                vals['attachment_filename'] = upload.filename
            expiry_val = post.get(expiry_key)
            if expiry_val:
                vals['expiry_date'] = expiry_val
            if vals:
                doc.write(vals)

    def _od_missing_mandatory_docs(self, registration):
        """Mandatory docs (All Vendors + selected Category) that still
        have no file after this submission - a server-side validation
        safety net (the public form also enforces this via required/JS,
        but that can be bypassed)."""
        registration = registration.sudo()
        return registration.document_ids.filtered(
            lambda d: d.level == 'mandatory' and d.state == 'missing'
        ).mapped('document_type_id.name')

    def _od_render_values(self, registration, readonly, error, is_new):
        return {
            'registration': registration,
            'countries': request.env['res.country'].sudo().search([]),
            'states': request.env['res.country.state'].sudo().search([]),
            'doc_types': self._od_get_doc_types(),
            'docs_by_type': self._od_docs_by_type(registration),
            'readonly': readonly,
            'error': error,
            'is_new': is_new,
        }

    # ------------------------------------------------------------------
    # NEW: self-service - create a brand new registration
    # e.g. /vendor/register  (public, generic link, no id/token needed)
    # ------------------------------------------------------------------
    @http.route(
        ['/vendor/register', '/vendor/register/new'],
        type='http', auth='public', csrf=False)
    def od_vendor_registration_new_form(self, **kwargs):
        return request.render(
            'od_vendor_registration.od_vendor_registration_form_template',
            self._od_render_values(False, False, kwargs.get('error'), True))

    @http.route(
        ['/vendor/register/create'],
        type='http', auth='public', methods=['POST'], csrf=True)
    def od_vendor_registration_create(self, **post):
        if not post.get('name') or not post.get('iban') or not post.get('bank_name'):
            values = self._od_render_values(
                False, False, 'Vendor Name, IBAN and Bank Name are required.', True)
            return request.render(
                'od_vendor_registration.od_vendor_registration_form_template', values)

        vals = self._od_vals_from_post(post)
        registration = request.env['od.vendor.registration'].sudo().create(vals)
        self._od_save_documents(registration, post)

        missing = self._od_missing_mandatory_docs(registration)
        if missing:
            values = self._od_render_values(
                registration, False,
                'Please upload the following mandatory document(s): %s'
                % ', '.join(missing), False)
            return request.render(
                'od_vendor_registration.od_vendor_registration_form_template', values)

        return request.render('od_vendor_registration.od_vendor_registration_thankyou_template', {
            'registration': registration,
        })

    # ------------------------------------------------------------------
    # EXISTING: edit a registration via its shared, token-protected link
    # e.g. /vendor/register/<id>/<token>
    # ------------------------------------------------------------------
    @http.route(
        ['/vendor/register/<int:reg_id>/<string:token>'],
        type='http', auth='public', csrf=False)
    def od_vendor_registration_form(self, reg_id, token, **kwargs):
        registration = self._od_get_registration(reg_id, token)
        if not registration:
            return request.render('od_vendor_registration.od_vendor_registration_not_found')

        registration.sudo()._sync_document_lines()
        values = self._od_render_values(
            registration, registration.state != 'register', kwargs.get('error'), False)
        return request.render(
            'od_vendor_registration.od_vendor_registration_form_template', values)

    @http.route(
        ['/vendor/register/<int:reg_id>/<string:token>/submit'],
        type='http', auth='public', methods=['POST'], csrf=True)
    def od_vendor_registration_submit(self, reg_id, token, **post):
        registration = self._od_get_registration(reg_id, token)
        if not registration:
            return request.render('od_vendor_registration.od_vendor_registration_not_found')

        if registration.state != 'register':
            # Locked: silently show the (now read-only) form.
            return request.redirect('/vendor/register/%s/%s' % (reg_id, token))

        if not post.get('name') or not post.get('iban') or not post.get('bank_name'):
            values = self._od_render_values(
                registration, False,
                'Vendor Name, IBAN and Bank Name are required.', False)
            return request.render(
                'od_vendor_registration.od_vendor_registration_form_template', values)

        vals = self._od_vals_from_post(post)
        registration.sudo().write(vals)
        self._od_save_documents(registration, post)

        missing = self._od_missing_mandatory_docs(registration)
        if missing:
            values = self._od_render_values(
                registration, False,
                'Please upload the following mandatory document(s): %s'
                % ', '.join(missing), False)
            return request.render(
                'od_vendor_registration.od_vendor_registration_form_template', values)

        return request.render('od_vendor_registration.od_vendor_registration_thankyou_template', {
            'registration': registration,
        })
