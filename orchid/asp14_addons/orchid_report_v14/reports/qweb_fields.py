# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models, _
from num2words import num2words
import logging
_logger = logging.getLogger(__name__)


class Num2wordsConverter(models.AbstractModel):
    _name = 'ir.qweb.field.num2words'
    _inherit = 'ir.qweb.field'

    def value_to_html(self, value, options):
        if not value:
            return False
        return num2words(round(value,2))
