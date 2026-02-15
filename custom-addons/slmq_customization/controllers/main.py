from odoo import http
from odoo.http import request


class webController(http.Controller):
    
    
    @http.route(['/register/member'], type='http', auth='public', methods=['GET', 'POST'], website=True, csrf=False)
    def member_submit(self, **post):
        # GET request - show form
        if request.httprequest.method == 'GET':
            return request.render('slmq_customization.membership_form', {
                'error': False,
                'success': False
            })
        
        # POST request - your existing logic
        print("Received registration data:", post)
        email = post.get('email')
        phone = post.get('phone')
        
        existing = request.env['res.partner'].sudo().search([
            '|',
            ('email', '=', email),
            ('phone', '=', phone)
        ], limit=1)
        
        if existing:
            return request.render('slmq_customization.membership_form', {
                'error': True,
                'success': False,
                'form_data': post
            })
        
        request.env['res.partner'].sudo().create({
            'name': post.get('name'),
            'email': email,
            'phone': phone,
            'member_category': 'new',
            'is_committee_member': True,
        })
        
        return request.render('slmq_customization.membership_form', {
            'error': False,
            'success': True
        })
