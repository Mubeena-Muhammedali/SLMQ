# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import get_lang


class AccountCommonReport(models.TransientModel):
    _inherit = "account.common.report"


    od_with_closing = fields.Boolean(string = "With Closing", default=True)