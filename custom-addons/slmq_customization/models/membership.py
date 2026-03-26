from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Membership(models.Model):
    _name = 'membership.membership'
    _description = 'Membership' 
    _order = "id desc"
    _rec_names_search = ['name', 'email', 'partner_name', 'phone']

    name = fields.Char("Registration No.", default='New', readonly=True)
    partner_name = fields.Char("Partner Name", required=True)
    email = fields.Char("Email", required=True)
    phone = fields.Char("Phone", required=True)

    member_type = fields.Selection([
        ('member','Member'),('founder','Founder'),('past','Past')
    ], string="Member Type", default='member', required=True)

    state = fields.Selection([
        ('draft','Draft'),('confirm','Confirmed'),('reject','Rejected')
    ], string="Status", default='draft')

    parent_id = fields.Many2one('membership.membership', string="Parent")
    child_ids = fields.One2many('membership.membership','parent_id', string="Child")
    is_child = fields.Boolean("Is Child?")

    partner_id = fields.Many2one('res.partner', string="Contact")
    child_count = fields.Integer(compute="_compute_child_count")

    @api.depends('name', 'partner_name', 'phone', 'email')
    def _compute_display_name(self):
        for rec in self:
            name = f"{rec.name or ''} - {rec.partner_name or ''}"

            if rec.phone:
                name += f" [{rec.phone}]"
            if rec.email:
                name += f" [{rec.email}]"

            rec.display_name = name.strip()

    def _compute_child_count(self):
        for rec in self:
            rec.child_count = len(rec.child_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_child') and vals.get('parent_id'):
                parent = self.browse(vals['parent_id'])

                # Get existing child numbers
                child_names = parent.child_ids.mapped('name')
                numbers = []
                for name in child_names:
                    if name and '/' in name:
                        try:
                            numbers.append(int(name.split('/')[-1]))
                        except:
                            continue

                next_number = max(numbers) + 1 if numbers else 1
                vals['name'] = f"{parent.name}/{next_number}"

            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('membership.sequence')

        records = super().create(vals_list)

        # 🔹 Send Emails
        group = self.env.ref('slmq_customization.group_membership_manager')
        manager_template = self.env.ref('slmq_customization.email_template_membership_manager')
        partner_template = self.env.ref('slmq_customization.email_template_membership_created')

        emails = ','.join(group.user_ids.filtered(lambda u: u.email).mapped('email'))

        for rec in records:
            # Manager mail (single send per record)
            if emails:
                manager_template.send_mail(
                    rec.id,
                    email_values={'email_to': emails},
                    force_send=True
                )

            # Partner mail
            if rec.email:
                partner_template.send_mail(
                    rec.id,
                    email_values={'email_to': rec.email},
                    force_send=True
                )

            # Parent mail
            if rec.parent_id and rec.parent_id.email:
                partner_template.with_context(is_parent=True).send_mail(
                    rec.id,
                    email_values={'email_to': rec.parent_id.email},
                    force_send=True
                )

        return records

    
    def write(self, vals):
        res = super().write(vals)

        for rec in self:
            # Trigger if:
            # - parent changed OR
            # - is_child set to True
            if (vals.get('parent_id') or vals.get('is_child')) and rec.is_child and rec.parent_id:

                parent = rec.parent_id

                # Exclude current record
                siblings = parent.child_ids.filtered(lambda c: c.id != rec.id)

                numbers = []
                for name in siblings.mapped('name'):
                    if name and '/' in name:
                        try:
                            numbers.append(int(name.split('/')[-1]))
                        except:
                            continue

                next_number = max(numbers) + 1 if numbers else 1

                rec.name = f"{parent.name}/{next_number}"

        return res

    def unlink(self):
        for rec in self:
            if rec.state == 'confirm':
                raise ValidationError("You cannot delete a confirmed membership.")
        return super().unlink()


    @api.constrains('email', 'phone','parent_id')
    def _check_unique_email_phone(self):
        for rec in self:

            domain = [('id', '!=', rec.id)]

            if rec.parent_id:
                domain.append(('id', '!=', rec.parent_id.id))

            if rec.email:
                if self.search(domain + [('email', '=', rec.email)], limit=1):
                    raise ValidationError("Email already exists!")

            if rec.phone:
                if self.search(domain + [('phone', '=', rec.phone)], limit=1):
                    raise ValidationError("Phone already exists!")
                    

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
            partner = self.env['res.partner'].sudo().create(vals)
            rec.write({'partner_id':partner.id,'state':'confirm'})

            user_vals = {
                'name': rec.partner_name,
                'login': rec.name,
                'password':"1234",
                'email': rec.email,
                'partner_id': partner.id,
                'group_ids': [(6, 0, [
                    self.env.ref('slmq_customization.group_membership_user').id,
                    self.env.ref('base.group_user').id  
                ])]
            }
            user = self.env['res.users'].sudo().create(user_vals)

            template = self.env.ref('slmq_customization.email_template_membership_confirm')
            template.with_context(
                        login=user.login,
                        password="1234"
                        ).send_mail(rec.id, 
                                email_values={'email_to': rec.email},
                                force_send=True)
                                

    def action_draft(self):
        for rec in self:
            rec.write({'state':'draft'})
    
    def action_reject(self):
        for rec in self:
            rec.write({'state':'reject'})

            template = self.env.ref('slmq_customization.email_template_membership_reject')
            template.send_mail(rec.id, 
                                email_values={'email_to': rec.email},
                                force_send=True)


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