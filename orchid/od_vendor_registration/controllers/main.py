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
            'category': post.get('category') or False,
        }

    # ------------------------------------------------------------------
    # NEW: self-service - create a brand new registration
    # e.g. /vendor/register  (public, generic link, no id/token needed)
    # ------------------------------------------------------------------
    @http.route(
        ['/vendor/register', '/vendor/register/new'],
        type='http', auth='public', csrf=False)
    def od_vendor_registration_new_form(self, **kwargs):
        return request.render('od_vendor_registration.od_vendor_registration_form_template', {
            'registration': False,
            'countries': request.env['res.country'].sudo().search([]),
            'states': request.env['res.country.state'].sudo().search([]),
            'readonly': False,
            'error': kwargs.get('error'),
            'is_new': True,
        })

    @http.route(
        ['/vendor/register/create'],
        type='http', auth='public', methods=['POST'], csrf=True)
    def od_vendor_registration_create(self, **post):
        if not post.get('name'):
            return request.render('od_vendor_registration.od_vendor_registration_form_template', {
                'registration': False,
                'countries': request.env['res.country'].sudo().search([]),
                'states': request.env['res.country.state'].sudo().search([]),
                'readonly': False,
                'error': 'Vendor Name is required.',
                'is_new': True,
            })

        vals = self._od_vals_from_post(post)
        registration = request.env['od.vendor.registration'].sudo().create(vals)

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

        return request.render('od_vendor_registration.od_vendor_registration_form_template', {
            'registration': registration,
            'countries': request.env['res.country'].sudo().search([]),
            'states': request.env['res.country.state'].sudo().search([]),
            'readonly': registration.state != 'register',
            'error': kwargs.get('error'),
            'is_new': False,
        })

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

        if not post.get('name'):
            return request.render('od_vendor_registration.od_vendor_registration_form_template', {
                'registration': registration,
                'countries': request.env['res.country'].sudo().search([]),
                'states': request.env['res.country.state'].sudo().search([]),
                'readonly': False,
                'error': 'Vendor Name is required.',
                'is_new': False,
            })

        vals = self._od_vals_from_post(post)
        registration.sudo().write(vals)

        return request.render('od_vendor_registration.od_vendor_registration_thankyou_template', {
            'registration': registration,
        })
