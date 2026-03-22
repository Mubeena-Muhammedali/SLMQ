from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Membership(models.Model):
    _name = 'membership.membership'

    name = fields.Char(default='New', readonly=True)
    partner_name = fields.Char(required=True)
    email = fields.Char(required=True)
    phone = fields.Char(required=True)

    member_type = fields.Selection([
        ('member','Member'),('founder','Founder'),('past','Past')
    ], default='member', required=True)

    state = fields.Selection([
        ('draft','Draft'),('confirm','Confirm')
    ], default='draft')

    parent_id = fields.Many2one('membership.membership')
    child_ids = fields.One2many('membership.membership','parent_id')
    is_child = fields.Boolean()

    partner_id = fields.Many2one('res.partner', string="Contact")
    child_count = fields.Integer(compute="_compute_child_count")

    def _compute_child_count(self):
        for rec in self:
            rec.child_count = len(rec.child_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_child') and vals.get('parent_id'):
                parent = self.browse(vals['parent_id'])
                count = len(parent.child_ids) + 1
                vals['name'] = f"{parent.name}/{count}"
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('membership.sequence')

        return super().create(vals_list)

    @api.constrains('email','phone','is_child')
    def _check_unique(self):
        for rec in self:
            if not rec.is_child:
                existing = self.search([
                    ('id','!=',rec.id),
                    ('is_child','=',False),
                    '|',('email','=',rec.email),('phone','=',rec.phone)
                ])
                if existing:
                    raise ValidationError("Email or Phone exists!")

    def action_confirm(self):
        for rec in self:
            vals = {
                'name': rec.partner_name,
                'email': rec.email,
                'phone': rec.phone,
                'is_member': True,
                'member_type': rec.member_type,
                'membership_id': rec.id,
            }
            if rec.parent_id:
                vals.update({
                    'parent_id': rec.parent_id.partner_id.id,
                    'type': 'other'
                })
            partner = self.env['res.partner'].create(vals)
            rec.partner_id = partner.id
            rec.state = 'confirm'

    def action_view_children(self):
        self.ensure_one()

        return {
            'name': 'Child Members',
            'type': 'ir.actions.act_window',
            'res_model': 'membership.membership',
            'view_mode': 'list,form',
            'domain': [('parent_id', '=', self.id)],
            'context': {
                'default_parent_id': self.id,
                'default_is_child': True
            }
        }