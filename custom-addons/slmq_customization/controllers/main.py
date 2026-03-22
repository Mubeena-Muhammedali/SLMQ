from odoo import http
from odoo.http import request

class MembershipController(http.Controller):

    @http.route('/register/member', type='http', auth='public', website=True, csrf=False)
    def register(self, **post):

        error = False
        success = False
        parent_error = False

        if not post:
            return request.render('website.membership', {
                'error': error,
                'success': success,
                'parent_error': parent_error,
            })

        Membership = request.env['membership.membership'].sudo()

        is_child = bool(post.get('is_child'))
        email = post.get('email')
        phone = post.get('phone')
        parent = False

        # -------------------------
        # 1. Parent Validation
        # -------------------------
        if is_child:
            parent_reg_no = post.get('parent_reg_no')

            if not parent_reg_no:
                parent_error = "Parent not found"
            else:
                parent = Membership.search([('name', '=', parent_reg_no)], limit=1)
                if not parent:
                    parent_error = "Parent not found"

        # -------------------------
        # 2. Duplicate Check
        # -------------------------
        if not parent_error:
            domain = ['|', ('email', '=', email), ('phone', '=', phone)]

            if is_child and parent:
                # Allow same as parent, but restrict others
                domain = [('id', '!=', parent.id)] + domain

            existing = Membership.search(domain, limit=1)

            # For parent → always restrict
            # For child → restrict only if conflict (excluding parent)
            if existing:
                error = True

        # -------------------------
        # 3. Create Record
        # -------------------------
        if not error and not parent_error:
            Membership.create({
                'partner_name': post.get('name'),
                'email': email,
                'phone': phone,
                'member_type': 'member',
                'is_child': is_child,
                'parent_id': parent.id if parent else False,
            })
            success = True

        # -------------------------
        # 4. Render
        # -------------------------
        return request.render('website.membership', {
            'error': error,
            'success': success,
            'parent_error': parent_error,
        })