from odoo import http
from odoo.http import request

class MembershipController(http.Controller):

    @http.route('/register/member', type='http', auth='public', website=True, csrf=False)
    def register(self, **post):

        error = False
        success = False
        parent_error = False 

        if post:
            print('post------------->',post)
            existing = request.env['membership.membership'].sudo().search([
                ('is_child', '=', False),
                '|',
                ('email', '=', post.get('email')),
                ('phone', '=', post.get('phone'))
            ], limit=1)

            if existing:
                error = True
            else:
                parent = False

                # ✅ Child validation
                if post.get('is_child'):
                    if not post.get('parent_reg_no'):
                        parent_error = True
                    else:
                        parent = request.env['membership.membership'].sudo().search([
                            ('name', '=', post.get('parent_reg_no'))
                        ], limit=1)

                        if not parent:
                            parent_error = True   # ❗ parent not found

                # ✅ Only create if no errors
                if not parent_error:
                    request.env['membership.membership'].sudo().create({
                        'partner_name': post.get('name'),
                        'email': post.get('email'),
                        'phone': post.get('phone'),
                        'member_type': post.get('member_type'),
                        'is_child': bool(post.get('is_child')),
                        'parent_id': parent.id if parent else False,
                        'member_type':'member',
                    })
                    success = True

        return request.render('website.membership', {
            'error': error,
            'success': success,
            'parent_error': parent_error,   # ✅ pass to template
        })