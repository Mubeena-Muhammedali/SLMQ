from odoo import api, fields, models

try:
    from num2words import num2words
except ImportError:
    num2words = None

# Invoice types that share the "Registration/Sponsorship" style Terms &
# Conditions block and the second Mashreq bank-account pair.
BANK_GROUP_B_TYPES = ('AF Registeration', 'AF Sponsorship')

# (account_no, iban) per bank group / currency - fill in / adjust to match
# your actual bank mandate letters.
BANK_ACCOUNTS = {
    ('A', 'AED'): ('0104-93-15691-4', 'AE280330000010493156914'),
    ('A', 'USD'): ('0104-48-47064-5', 'AE290330000010448470645'),
    ('B', 'AED'): ('0190-00-05007-6', 'AE630330000019000050076'),
    ('B', 'USD'): ('0190-00-05007-7', 'AE360330000019000050077'),
}

# Invoice types that print the delegate-cancellation Terms & Conditions.
TYPES_WITH_TERMS = ('Event', 'AF Registeration')


class AccountMove(models.Model):
    _inherit = 'account.move'

    od_invoice_type = fields.Selection([('Event','Event'),('Membership','Membership'),('AF Registeration','AF Registeration'),('AF Sponsorship','AF Sponsorship')],string="Invoice print Type", tracking=True)

    od_amount_in_local_currency = fields.Monetary(
        string='Amount in Local Currency (AED)',
        currency_field='company_currency_id',
        compute='_compute_od_amount_in_local_currency',
        store=True,
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id', string='Company Currency'
    )

    @api.depends('amount_total', 'currency_id', 'invoice_date', 'company_id')
    def _compute_od_amount_in_local_currency(self):
        for move in self:
            company = move.company_id
            if move.currency_id and company.currency_id and move.currency_id != company.currency_id:
                move.od_amount_in_local_currency = move.currency_id._convert(
                    move.amount_total,
                    company.currency_id,
                    company,
                    move.invoice_date or fields.Date.context_today(move),
                )
            else:
                move.od_amount_in_local_currency = move.amount_total

    def od_get_amount_in_words(self):
        self.ensure_one()
        if not num2words:
            return ''
        try:
            words = num2words(self.amount_total, lang='en')
        except NotImplementedError:
            words = num2words(self.amount_total, lang='en_US')
        return words.replace(',', '').capitalize()

    def od_get_bank_details(self):
        """Return (account_no, iban) for this invoice's group + currency."""
        self.ensure_one()
        currency = self.currency_id.name if self.currency_id.name == 'USD' else 'AED'
        return BANK_ACCOUNTS.get((self.od_get_bank_group(), currency), ('', ''))

    
    def od_get_bank_group(self):
        """'A' for Event/Membership, 'B' for AF Registration/Sponsorship."""
        self.ensure_one()
        return 'B' if self.od_invoice_type in BANK_GROUP_B_TYPES else 'A'

    def od_show_terms(self):
        self.ensure_one()
        return self.od_invoice_type in TYPES_WITH_TERMS

    def od_convert_usd(self, amount):
        """Convert `amount` (in this invoice's currency) into USD."""
        self.ensure_one()
        usd = self.env.ref('base.USD', raise_if_not_found=False)
        if not usd or self.currency_id == usd:
            return amount
        return self.currency_id._convert(
            amount, usd, self.company_id,
            self.invoice_date or fields.Date.context_today(self),
        )



    

    

    
