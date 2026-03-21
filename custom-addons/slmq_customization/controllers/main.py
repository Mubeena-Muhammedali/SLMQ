from odoo import http
from odoo.http import request

class MembershipController(http.Controller):

    @http.route('/membership/register', type='http', auth='public', website=True)
    def register(self, **post):

        parent = False
        if post.get('is_child') and post.get('parent_reg_no'):
            parent = request.env['membership.membership'].sudo().search([
                ('name','=',post.get('parent_reg_no'))
            ], limit=1)

        request.env['membership.membership'].sudo().create({
            'partner_name': post.get('name'),
            'email': post.get('email'),
            'phone': post.get('phone'),
            'member_type': post.get('member_type'),
            'is_child': bool(post.get('is_child')),
            'parent_id': parent.id if parent else False,
        })

        return "Registered Successfully"