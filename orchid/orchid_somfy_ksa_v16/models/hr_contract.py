# -*- coding: utf-8 -*-

from odoo import models, fields, api
import math

class HrContract(models.Model):
    _inherit = "hr.contract"

    od_bonus_percentage = fields.Float(
        string="Bonus Percentage (%)",
        digits=(16, 2),
        help="Annual bonus percentage based on the annual salary."
    )

    od_annual_bonus = fields.Monetary(
        string="Annual Bonus",
        compute="_compute_annual_bonus"
    )

    @api.depends("od_bonus_percentage", "wage")
    def _compute_annual_bonus(self):
        for contract in self:
            annual_salary = contract.wage * 13
            contract.od_annual_bonus = math.ceil(annual_salary * (contract.od_bonus_percentage / 100))