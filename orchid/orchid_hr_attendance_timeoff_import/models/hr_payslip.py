# -*- coding: utf-8 -*-
from itertools import zip_longest

from odoo import models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # ------------------------------------------------------------------
    # Helpers used by the "Orchid" pay slip report (report/hr_payslip_report.xml)
    # ------------------------------------------------------------------
    def _od_earning_lines(self):
        """Payslip lines shown on the left (Earnings) side of the report."""
        self.ensure_one()
        return self.line_ids.filtered(
            lambda l: l.appears_on_payslip
            and l.category_id.code not in ('DED', 'NET')
            and (l.total or 0.0) >= 0
            and not self._od_exclude_line(l)
        ).sorted(key=lambda l: l.sequence)

    def _od_deduction_lines(self):
        """Payslip lines shown on the right (Deductions) side of the report."""
        self.ensure_one()
        return self.line_ids.filtered(
            lambda l: l.appears_on_payslip
            and (l.category_id.code == 'DED' or (l.total or 0.0) < 0)
        ).sorted(key=lambda l: l.sequence)

    def _od_line_pairs(self):
        """Zip Earnings/Deductions side by side, one table row each, even
        when the two lists have a different number of lines."""
        self.ensure_one()
        return list(zip_longest(self._od_earning_lines(), self._od_deduction_lines()))

    def _od_exclude_line(self, line):
        name = (line.name or '').strip().lower()
        code = (line.category_id.code or '').strip().upper()
        excluded_names = ('gross', 'taxable amount', 'taxable', 'gross amount')
        excluded_codes = ('GROSS',)
        return any(item in name for item in excluded_names) or code in excluded_codes

    def _od_worked_days_value(self):
        self.ensure_one()
        worked_days = self.worked_days_line_ids.filtered(lambda wd: (wd.number_of_days or 0.0) > 0)
        if worked_days:
            return worked_days[0].number_of_days
        if self.worked_days_line_ids:
            return self.worked_days_line_ids[0].number_of_days
        return ''

    def _od_total_earnings(self):
        self.ensure_one()
        return sum((line.total or 0.0) for line in self._od_earning_lines())

    def _od_total_deductions(self):
        self.ensure_one()
        return sum(abs(line.total or 0.0) for line in self._od_deduction_lines())

    @staticmethod
    def _od_fmt(value):
        """Plain thousand-separated number, no currency symbol
        (e.g. 2113.5 -> '2,113.50'), matching the sample layout."""
        return '{:,.2f}'.format(value or 0.0)

    def _od_amount_in_words(self):
        """Net payable amount spelled out, e.g.:
        'Dirhams: Two Thousand One Hundred Thirteen And Fils Fifty Only'
        Assumes AED (Dirhams/Fils); any other currency falls back to its
        currency name and 'Cents' as the subunit label."""
        self.ensure_one()

        ones = ('', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
                'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
                'Seventeen', 'Eighteen', 'Nineteen')
        tens = ('', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety')

        def below_1000(n):
            if n < 20:
                return ones[n]
            if n < 100:
                return (tens[n // 10] + ' ' + ones[n % 10]).strip()
            return (ones[n // 100] + ' Hundred ' + below_1000(n % 100)).strip()

        def to_words(n):
            if n == 0:
                return 'Zero'
            words = ''
            for value, name in ((1000000000, 'Billion'), (1000000, 'Million'), (1000, 'Thousand')):
                if n >= value:
                    words += below_1000(n // value) + ' ' + name + ' '
                    n %= value
            return (words + below_1000(n)).strip()

        amount = self.net_wage or 0.0
        currency = self.company_id.currency_id
        is_aed = (currency.name or '').upper() == 'AED'
        main_label = 'Dirhams' if is_aed else (currency.name or 'Amount')
        sub_label = 'Fils' if is_aed else 'Cents'

        rupees, paisa = divmod(int(round(amount * 100)), 100)
        text = '%s: %s' % (main_label, to_words(rupees))
        if paisa:
            text += ' And %s %s' % (sub_label, to_words(paisa))
        return text + ' Only'

