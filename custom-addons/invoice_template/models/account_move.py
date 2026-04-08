# -*- coding: utf-8 -*-
from odoo import models, api
from num2words import num2words
import math


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_amount_in_words(self):
        """Return the invoice total in English words, formatted like:
        Four Thousand Two Hundred Seventy-Three And Fifty Fils Only
        """
        self.ensure_one()
        amount = self.amount_total
        currency_name = self.currency_id.name if self.currency_id else 'AED'

        whole = int(amount)
        fils = round((amount - whole) * 100)

        words_whole = num2words(whole, lang='en').replace('-', ' ').title()

        if fils > 0:
            words_fils = num2words(fils, lang='en').replace('-', ' ').title()
            result = f"{words_whole} And {words_fils} Fils Only"
        else:
            result = f"{words_whole} Only"

        return result
