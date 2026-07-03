from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import math
from datetime import datetime


class SalaryProvision(models.Model):
    _name = 'od.salary.provision'
    _description = 'Salary Provision'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    date = fields.Date(
        string='Date',
        required=True,
        tracking=True
    )

    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Posted')
    ], default='draft', tracking=True)

    # Accounts
    thirteenth_debit_account_id = fields.Many2one(
        'account.account',
        string='13th Month Salary Debit Account',check_company=True,
        required=True
    )

    thirteenth_credit_account_id = fields.Many2one(
        'account.account',
        string='13th Month Salary Credit Account',check_company=True,
        required=True
    )

    bonus_debit_account_id = fields.Many2one(
        'account.account',
        string='Bonus Debit Account',check_company=True,
        required=True
    )

    bonus_credit_account_id = fields.Many2one(
        'account.account',
        string='Bonus Credit Account',check_company=True,
        required=True
    )

    eos_debit_account_id = fields.Many2one(
        'account.account',
        string='End Of Service Debit Account',check_company=True,
        required=True
    )

    eos_credit_account_id = fields.Many2one(
        'account.account',
        string='End Of Service Credit Account',check_company=True,
        required=True
    )

    # One2many Lines
    thirteenth_line_ids = fields.One2many(
        'od.salary.provision.thirteenth',
        'provision_id',
        string='13th Month Salary'
    )

    gosi_line_ids = fields.One2many(
        'od.salary.provision.gosi',
        'provision_id',
        string='GOSI'
    )

    bonus_line_ids = fields.One2many(
        'od.salary.provision.bonus',
        'provision_id',
        string='Bonus'
    )

    eos_line_ids = fields.One2many(
        'od.salary.provision.eos',
        'provision_id',
        string='End Of Service'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain="[('type', '=', 'general')]",check_company=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            if vals.get('name', 'New') == 'New':

                seq_date = None

                if vals.get('date'):
                    seq_date = fields.Date.to_date(vals['date'])

                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'od.salary.provision',
                    sequence_date=seq_date
                ) or '/'

        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirm'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_post(self):
        for rec in self:

            if rec.move_id:
                raise ValidationError(_("Journal Entry already created."))

            line_vals = []
            date_from = datetime.strptime(str(rec.date), '%Y-%m-%d').strftime('%Y-%B')

            # 13th Month Salary
            for line in rec.thirteenth_line_ids:
                partner = line.employee_id.address_home_id.id or False

                line_vals.append((0, 0, {
                    'name': f'Provision for 13th Month Salary Booking {date_from} - {line.employee_id.name}',
                    'partner_id': partner,
                    'account_id': rec.thirteenth_debit_account_id.id,
                    'debit': line.amount,
                    'credit': 0.0,
                }))

                line_vals.append((0, 0, {
                    'name': f'Provision for 13th Month Salary Booking {date_from} - {line.employee_id.name}',
                    'partner_id': partner,
                    'account_id': rec.thirteenth_credit_account_id.id,
                    'debit': 0.0,
                    'credit': line.amount,
                }))

            # Bonus
            for line in rec.bonus_line_ids:
                partner = line.employee_id.address_home_id.id or False

                line_vals.append((0, 0, {
                    'name': f'Provision for Bonus Booking {date_from} - {line.employee_id.name}',
                    'partner_id': partner,
                    'account_id': rec.bonus_debit_account_id.id,
                    'debit': line.amount,
                    'credit': 0.0,
                }))

                line_vals.append((0, 0, {
                    'name': f'Provision for Bonus Booking {date_from} - {line.employee_id.name}',
                    'partner_id': partner,
                    'account_id': rec.bonus_credit_account_id.id,
                    'debit': 0.0,
                    'credit': line.amount,
                }))

            # End Of Service
            for line in rec.eos_line_ids:
                partner = line.employee_id.address_home_id.id or False

                line_vals.append((0, 0, {
                    'name': f'Provision for EOSB Booking {date_from} - {line.employee_id.name}',
                    'partner_id': partner,
                    'account_id': rec.eos_debit_account_id.id,
                    'debit': line.amount,
                    'credit': 0.0,
                }))

                line_vals.append((0, 0, {
                    'name': f'Provision for EOSB Booking {date_from} - {line.employee_id.name}',
                    'partner_id': partner,
                    'account_id': rec.eos_credit_account_id.id,
                    'debit': 0.0,
                    'credit': line.amount,
                }))

            move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': rec.date,
                'ref': rec.name,
                'journal_id':rec.journal_id.id,
                'line_ids': line_vals,
            })

            move.action_post()

            rec.write({
                'move_id': move.id,
                'state': 'done'
            })

    def action_fetch_data(self):
        """
        Main fetch button.
        Calls all individual fetch functions.
        """
        self.ensure_one()

        base_domain = [
            ('state', '=', 'open'),
            ('company_id', '=', self.company_id.id),
            ('employee_id', '!=', False),
        ]
        contracts = self.env['hr.contract'].search(base_domain)

        self._fetch_13th_month_salary_lines(contracts)
        self._fetch_gosi_lines(contracts)
        self._fetch_bonus_lines(contracts)
        self._fetch_eos_lines(contracts)

    def _fetch_13th_month_salary_lines(self, contracts):
        """
        Fetch 13th month salary provision lines.
        Amount = x_studio_13th_month_salary / 6
        """
        self.ensure_one()

        line_vals = [
            (0, 0, {
                'employee_id': contract.employee_id.id,
                'amount': contract.x_studio_13th_month_salary / 6,
            })
            for contract in contracts
            if contract.x_studio_13th_month_salary > 0
        ]

        self.write({'thirteenth_line_ids': [(5, 0, 0)] + line_vals})

    def _fetch_gosi_lines(self, contracts):
        """
        GOSI Provision Calculation

        L = min((wage + housing), 45000)
        M = ROUNDUP(L * 2.25%)
        N = ROUNDUP(L * 9%) if Saudi
        O = ROUNDUP(L * 1%) if Saudi
        P = ROUNDUP(L * 10%) if WFH AND Saudi
        Amount = M + N + O + P
        """
        self.ensure_one()

        saudi_country = self.env.ref('base.sa')
        line_vals = []

        for contract in contracts:
            employee = contract.employee_id
            wage = contract.wage or 0.0
            housing = contract.l10n_sa_housing_allowance or 0.0
            is_saudi = employee.country_id == saudi_country

            base_amount = min(wage + housing, 45000)

            m = math.ceil(base_amount * 0.0225)
            n = math.ceil(base_amount * 0.09) if is_saudi else 0
            o = math.ceil(base_amount * 0.01) if is_saudi else 0
            p = (
                math.ceil(base_amount * 0.10)
                if is_saudi and employee.x_studio_employment_type == 'WFH'
                else 0
            )

            amount = m + n + o + p
            if amount <= 0:
                continue

            line_vals.append((0, 0, {
                'employee_id': employee.id,
                'amount': amount,
            }))

        self.write({'gosi_line_ids': [(5, 0, 0)] + line_vals})

    def _fetch_bonus_lines(self, contracts):
        """
        Fetch Bonus provision lines.
        Amount = od_annual_bonus / 12
        """
        self.ensure_one()

        line_vals = [
            (0, 0, {
                'employee_id': contract.employee_id.id,
                'amount': math.ceil(contract.od_annual_bonus / 12),
            })
            for contract in contracts
            if contract.od_annual_bonus > 0
        ]

        self.write({'bonus_line_ids': [(5, 0, 0)] + line_vals})

    def _fetch_eos_lines(self, contracts):
        """
        Fetch End Of Service provision lines.
        Amount = ((od_previous_year_eosb - od_opening_balance) / 12), rounded up to nearest 100
        """
        self.ensure_one()

        line_vals = []
        for contract in contracts:
            raw = (contract.od_previous_year_eosb - contract.od_opening_balance) / 12
            amount = math.ceil(raw / 100) * 100
            if amount <= 0:
                continue

            line_vals.append((0, 0, {
                'employee_id': contract.employee_id.id,
                'amount': amount,
            }))

        self.write({'eos_line_ids': [(5, 0, 0)] + line_vals})
        
class SalaryProvisionThirteenth(models.Model):
    _name = 'od.salary.provision.thirteenth'
    _description = '13th Month Salary Lines'

    provision_id = fields.Many2one(
        'od.salary.provision',
        ondelete='cascade'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )

    amount = fields.Float(
        string='Amount',
        required=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='provision_id.company_id',
        store=True,
        readonly=True
    )


class SalaryProvisionBonus(models.Model):
    _name = 'od.salary.provision.bonus'
    _description = 'Bonus Lines'

    provision_id = fields.Many2one(
        'od.salary.provision',
        ondelete='cascade'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )

    amount = fields.Float(
        string='Amount',
        required=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='provision_id.company_id',
        store=True,
        readonly=True
    )

class SalaryProvisionGosi(models.Model):
    _name = 'od.salary.provision.gosi'
    _description = 'GOSI Lines'

    provision_id = fields.Many2one(
        'od.salary.provision',
        ondelete='cascade'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )

    amount = fields.Float(
        string='Amount',
        required=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='provision_id.company_id',
        store=True,
        readonly=True
    )


class SalaryProvisionEOS(models.Model):
    _name = 'od.salary.provision.eos'
    _description = 'End Of Service Lines'

    provision_id = fields.Many2one(
        'od.salary.provision',
        ondelete='cascade'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )

    amount = fields.Float(
        string='Amount',
        required=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='provision_id.company_id',
        store=True,
        readonly=True
    )