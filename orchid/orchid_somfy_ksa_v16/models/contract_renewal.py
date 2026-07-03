from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError

class OdContractRenewal(models.Model):
    _name = 'od.contract.renewal'
    _description = 'Contract Renewal'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    start_date = fields.Date("New Contract Start Date", required=True, tracking=True)
    previous_contract_end_date = fields.Date("Previous Contract End Date", required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('validated', 'Validated')
    ], default='draft', tracking=True)

    line_ids = fields.One2many('od.contract.renewal.line', 'renewal_id', tracking=True)

    def action_reset_draft(self):
        self.state = 'draft'

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft items can be deleted!!"))
        return super(OdContractRenewal, self).unlink()


    def action_fetch_contracts(self):
        self.line_ids.unlink()
        contracts = self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('company_id', '=', self.company_id.id)
        ])

        lines = []
        for c in contracts:
            lines.append((0, 0, {
                'employee_id': c.employee_id.id,
                'old_contract_id': c.id,
                'wage': c.wage,
                'hra': c.l10n_sa_housing_allowance,
                'da': c.x_studio_childrens_education_allowance,
                'travel_allowance': c.l10n_sa_other_allowances,
                'mobile_allowance': c.x_studio_mobile_allowance,
                'month_13': c.x_studio_13th_month_salary,
                'other_allowance': c.l10n_sa_other_allowances,
            }))

        self.line_ids = lines

    def action_confirm(self):
        self.state = 'confirm'

    def action_validate(self):
        for rec in self:

            # Remove lines where renew = False
            rec.line_ids.filtered(lambda l: not l.renew).unlink()

            for line in rec.line_ids.filtered(lambda x:x.renew):

                old = line.old_contract_id

                # Expire old contract
                old.write({
                    'state': 'close',
                    'date_end': rec.previous_contract_end_date
                })

                # Create new contract
                new_contract = old.copy({
                    'date_start': rec.start_date,
                    'date_end': False,
                    'state': 'open',
                    'wage': line.wage,
                    'l10n_sa_housing_allowance': line.hra,
                    'x_studio_childrens_education_allowance': line.da,
                    'l10n_sa_other_allowances': line.travel_allowance,
                    'x_studio_mobile_allowance': line.mobile_allowance,
                    'x_studio_13th_month_salary': line.month_13,
                    'l10n_sa_other_allowances': line.other_allowance,
                })

                line.new_contract_id = new_contract.id

            rec.state = 'validated'


class OdContractRenewalLine(models.Model):
    _name = 'od.contract.renewal.line'
    _description = 'Contract Renewal Line'
    _inherit = ['mail.thread']

    renewal_id = fields.Many2one('od.contract.renewal')

    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    old_contract_id = fields.Many2one('hr.contract', tracking=True)
    new_contract_id = fields.Many2one('hr.contract', tracking=True)

    renew = fields.Boolean(default=True, tracking=True)

    wage = fields.Float(tracking=True)
    hra = fields.Float("Housing Allowance", tracking=True)
    da = fields.Float("Children Education Allowance", tracking=True)
    travel_allowance = fields.Float(tracking=True)
    mobile_allowance = fields.Float("Mobile/Internet", tracking=True)
    month_13 = fields.Float("13 Month Salary", tracking=True)
    other_allowance = fields.Float(tracking=True)
    company_id = fields.Many2one('res.company', related="renewal_id.company_id", store=True)