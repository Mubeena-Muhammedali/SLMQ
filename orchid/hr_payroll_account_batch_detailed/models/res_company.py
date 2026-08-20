# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    od_batch_payroll_move_lines_detailed = fields.Boolean(
        string="Batch Payroll Move Lines (Detailed by Employee)")
