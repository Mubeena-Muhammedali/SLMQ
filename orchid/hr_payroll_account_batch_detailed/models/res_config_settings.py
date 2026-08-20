# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    od_batch_payroll_move_lines_detailed = fields.Boolean(
        related='company_id.od_batch_payroll_move_lines_detailed',
        string="Batch Payroll Move Lines (Detailed by Employee)", readonly=False,
        help="Enable this option to group all the payslips of a period into a single "
             "journal entry, while still keeping a separate account line per employee "
             "for each salary rule (based on the rule's 'Set employee on account line' "
             "setting). If enabled, this takes priority over 'Batch Payroll Move Lines'."
    )
