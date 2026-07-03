# -*- coding: utf-8 -*-

from odoo import models, fields, api
import math
from datetime import date

class HrContract(models.Model):
    _inherit = "hr.contract"

    od_bonus_percentage = fields.Float(
        string="Bonus Percentage (%)",
        digits=(16, 2),
        help="Annual bonus percentage based on the annual salary."
    )

    od_annual_bonus = fields.Monetary(
        string="Annual Bonus",
        compute="_compute_od_annual_bonus"
    )

    od_contract_year = fields.Integer(
        string="Contract Year",
        compute="_compute_od_contract_year"
    )

    od_years_of_service = fields.Float(
        string="Years of Service",
        compute="_compute_od_years_of_service",
        digits=(16, 1),
    )

    od_gross_annual_salary = fields.Monetary(
        string="Gross Annual Salary",
        compute="_compute_od_gross_annual_salary"
    )

    od_current_year_eosb = fields.Monetary(
        string="Current EOSB Salary",
        compute="_compute_od_eosb"
    )

    od_previous_year_eosb = fields.Monetary(
        string="Previous Year EOSB",
        compute="_compute_od_eosb"
    )

    od_opening_balance = fields.Monetary(
        string="Opening Balance",
        compute="_compute_od_opening_balance"
    )

    def _compute_od_opening_balance(self):
        for contract in self:
            open_contracts = self.env['hr.contract'].search([
                ('state', '=', 'open'),
                ('company_id', '=', self.company_id.id),
                ('employee_id', '!=', False),
            ])
            contract.od_opening_balance = contract.od_previous_year_eosb / sum(open_contracts.mapped('od_previous_year_eosb'))

    @api.depends("wage", "l10n_sa_housing_allowance", "l10n_sa_transportation_allowance", "od_annual_bonus")
    def _compute_od_gross_annual_salary(self):
        for contract in self:
            value1 = contract.wage + contract.l10n_sa_housing_allowance + contract.l10n_sa_transportation_allowance + contract.x_studio_childrens_education_allowance + contract.x_studio_mobile_allowance
            value2 = value1 * 12
            contract.od_gross_annual_salary = value2 + contract.od_annual_bonus + contract.wage

    @api.depends("od_years_of_service", "od_gross_annual_salary")
    def _compute_od_eosb(self):
        for contract in self:
            contract.od_current_year_eosb = round(contract.od_gross_annual_salary / 12)
            contract.od_previous_year_eosb = contract.od_current_year_eosb * contract.od_years_of_service

    @api.depends("od_contract_year", "employee_id.x_studio_joining_date")
    def _compute_od_years_of_service(self):
        for contract in self:
            joining_date = contract.employee_id.x_studio_joining_date

            if contract.od_contract_year and joining_date:
                year_end = date(contract.od_contract_year, 12, 31)

                days = (year_end - joining_date).days
                contract.od_years_of_service = max(days / 365.0, 0.0)
            else:
                contract.od_years_of_service = 0.0

    @api.depends("date_start")
    def _compute_od_contract_year(self):
        for contract in self:
            contract.od_contract_year = (
                contract.date_start.year if contract.date_start else 0
            )

    @api.depends("od_bonus_percentage", "wage")
    def _compute_od_annual_bonus(self):
        for contract in self:
            annual_salary = contract.wage * 13
            contract.od_annual_bonus = math.ceil(annual_salary * (contract.od_bonus_percentage / 100))