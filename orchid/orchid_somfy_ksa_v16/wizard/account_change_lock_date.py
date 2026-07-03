from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.addons import decimal_precision as dp
from odoo.tools import date_utils
from datetime import datetime, date
from odoo.tools import format_date

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:
            lock_date = picking.company_id.od_inventory_lock_date
            date_to_check = picking.date_done or picking.scheduled_date

            # Normalize both to date
            if isinstance(date_to_check, datetime):
                date_to_check = date_to_check.date()

            # lock_date should already be a date, but just in case:
            if isinstance(lock_date, datetime):
                lock_date = lock_date.date()

            if lock_date and date_to_check and date_to_check <= lock_date:
                raise UserError(_(
                    "You cannot validate this transfer because its date (%(date)s) "
                    "is prior to the inventory lock date (%(lock)s).",
                    date=format_date(self.env, date_to_check),
                    lock=format_date(self.env, lock_date)
                ))

        return super(StockPicking, self).button_validate()


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_violated_lock_dates(self, invoice_date, has_tax):
        # Get standard Odoo lock dates
        locks = super()._get_violated_lock_dates(invoice_date, has_tax)

        journal_type = self.journal_id.type  # 'sale', 'purchase', 'cash', 'bank'

        # -----------------------------
        # Add custom lock dates
        # -----------------------------

        sale_lock = self.company_id.od_sale_lock_date
        if sale_lock and invoice_date and journal_type == 'sale' and invoice_date <= sale_lock:
            locks.append((sale_lock, _('sales')))

        purchase_lock = self.company_id.od_purchase_lock_date
        if purchase_lock and invoice_date and journal_type == 'purchase' and invoice_date <= purchase_lock:
            locks.append((purchase_lock, _('purchase')))

        cashbank_lock = self.company_id.od_cashbank_lock_date
        if cashbank_lock and invoice_date and journal_type in ('cash', 'bank') and invoice_date <= cashbank_lock:
            locks.append((cashbank_lock, _('cash/bank')))

        # Sort chronologically (super may have added items too)
        locks.sort()
        return locks


class ResCompany(models.Model):
    _inherit = "res.company"

    od_sale_lock_date = fields.Date(
        string='Sales Lock Date',
        tracking=True,
        help="Any sales entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    od_purchase_lock_date = fields.Date(
        string='Purchase Lock date',
        tracking=True,
        help="Any purchase entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    od_cashbank_lock_date = fields.Date(
        string='Cash/Bank Lock date',
        tracking=True,
        help="Any Cash/Bank entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    od_inventory_lock_date = fields.Date(
        string='Inventory Lock date',
        tracking=True,
        help="Any inventory operations prior to and including this date will be postponed to a later date.",
    )

class AccountChangeLockDate(models.TransientModel):
    """
    This wizard is used to change the lock date
    """
    _inherit = 'account.change.lock.date'

    od_account_ids = fields.Many2many('account.account', string="Control Accounts")
    od_sale_lock_date = fields.Date(
        string='Lock Sales',
        default=lambda self: self.env.company.od_sale_lock_date,
        help="Any sales entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    od_purchase_lock_date = fields.Date(
        string='Lock Purchases',
        default=lambda self: self.env.company.od_purchase_lock_date,
        help="Any purchase entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )

    od_cashbank_lock_date = fields.Date(
        string='Lock Cash/Bank',
        default=lambda self: self.env.company.od_cashbank_lock_date,
        help="Any cash/Bank entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )

    od_inventory_lock_date = fields.Date(
        string='Lock Inventory',
        default=lambda self: self.env.company.od_inventory_lock_date,
        help="Any Inventory operations prior to and including this date will be postponed to a later date.",
    )

    def _prepare_lock_date_values(self):
        res = super(AccountChangeLockDate, self)._prepare_lock_date_values()
        res.update({
            'od_sale_lock_date': self.od_sale_lock_date,
            'od_purchase_lock_date': self.od_purchase_lock_date,
            'od_cashbank_lock_date': self.od_cashbank_lock_date,
            'od_inventory_lock_date': self.od_inventory_lock_date,
        })
        return res

    @api.model
    def default_get(self, fields):
        res = super(AccountChangeLockDate,self).default_get(fields)
        # default stock outbound and stock inbound accounts
        res['od_account_ids'] = [(6,0,[4466,4467])]
        return res

    @api.onchange('period_lock_date')
    def od_onchange_lock_date(self):
        for rec in self:
            rec.fiscalyear_lock_date = rec.period_lock_date
    
    # -------------------------------------------------------------
    # 1) Onchange: synchronize other locks if fiscal lock is updated
    # -------------------------------------------------------------
    @api.onchange('fiscalyear_lock_date')
    def _onchange_fiscalyear_lock_date(self):
        """
        Update sale, purchase, cash-bank lock dates only if the fiscal lock
        date is changed by the user. Inventory lock is skipped.
        """
        company = self.env.company
        # Only update if fiscal lock is actually changed
        if self.fiscalyear_lock_date and self.fiscalyear_lock_date != company.fiscalyear_lock_date:
            fiscal_date = self.fiscalyear_lock_date

            # Sale lock
            if not self.od_sale_lock_date or self.od_sale_lock_date < fiscal_date:
                self.od_sale_lock_date = fiscal_date

            # Purchase lock
            if not self.od_purchase_lock_date or self.od_purchase_lock_date < fiscal_date:
                self.od_purchase_lock_date = fiscal_date

            # Cash / Bank lock
            if not self.od_cashbank_lock_date or self.od_cashbank_lock_date < fiscal_date:
                self.od_cashbank_lock_date = fiscal_date

            # Inventory lock
            if not self.od_inventory_lock_date or self.od_inventory_lock_date < fiscal_date:
                self.od_inventory_lock_date = fiscal_date

    # -------------------------------------------------------------
    # 2) Build domain for draft account moves
    # -------------------------------------------------------------
    def od_build_lock_date_domain(self):
        """
        Build a domain to search for draft account.move entries
        affected by lock dates.
        """
        or_blocks = []

        # Sale lock
        if self.od_sale_lock_date:
            or_blocks.append([
                ('date', '<=', self.od_sale_lock_date),
                ('journal_id.type', '=', 'sale')
            ])

        # Purchase lock
        if self.od_purchase_lock_date:
            or_blocks.append([
                ('date', '<=', self.od_purchase_lock_date),
                ('journal_id.type', '=', 'purchase')
            ])

        # Cash/Bank lock
        if self.od_cashbank_lock_date:
            or_blocks.append([
                ('date', '<=', self.od_cashbank_lock_date),
                ('journal_id.type', 'in', ('cash', 'bank'))
            ])

        # Fiscal lock (applies globally)
        if self.fiscalyear_lock_date:
            or_blocks.append([
                ('date', '<=', self.fiscalyear_lock_date)
            ])

        if not or_blocks:
            return []

        # Build OR domain
        domain = or_blocks[0]
        for block in or_blocks[1:]:
            domain = ['|'] + domain + block

        # AND conditions
        domain += [
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'draft')
        ]

        return domain

    # -------------------------------------------------------------
    # 3) Change lock date: validation before applying
    # -------------------------------------------------------------
    def change_lock_date(self):

        # Ensure fiscal lock is chosen if period lock is set
        if self.period_lock_date and not self.fiscalyear_lock_date:
            raise UserError(_("Please choose All Users Lock Date !!!"))

        # Inventory lock validation (check inbound/outbound accounts)
        if self.od_inventory_lock_date:
            get_qry = """
                SELECT COALESCE(SUM(aml.balance), 0)
                FROM account_move_line aml
                LEFT JOIN account_move am ON am.id = aml.move_id
                WHERE aml.company_id IN %s
                  AND aml.account_id IN %s
                  AND aml.date <= %s
                  AND am.state = 'posted'
            """
            params = [
                tuple([self.env.company.id]),
                tuple(self.od_account_ids.ids),
                str(self.od_inventory_lock_date)
            ]
            self._cr.execute(get_qry, params)
            balance = self._cr.fetchone()[0]

            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if not float_is_zero(balance, precision_digits=precision):
                if balance > 0.7:
                    raise UserError(_("The stock inbound and stock outbound accounts are not closed!!!"))

        # Draft entry validation using lock date domain
        domain = self.od_build_lock_date_domain()
        print("DOMAIN:", domain)
        draft_entries = self.env['account.move'].search(domain)
        if draft_entries:
            raise UserError(_("There are draft entries for this period. Please post or cancel them to continue."))

        # Call super to actually apply changes
        return super(AccountChangeLockDate, self).change_lock_date()
