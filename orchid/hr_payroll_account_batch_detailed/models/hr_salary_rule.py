# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    od_batch_payroll_move_lines_detailed = fields.Boolean(
        compute='_od_compute_batch_payroll_move_lines_detailed')

    @api.depends_context('company')
    def _od_compute_batch_payroll_move_lines_detailed(self):
        for rule in self:
            rule.od_batch_payroll_move_lines_detailed = self.env.company.od_batch_payroll_move_lines_detailed
