# Copyright 2018 Graeme Gellatly
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class StatementCommon(models.AbstractModel):

    _name = "statement.common.wizard"
    _description = "Statement Reports Common Wizard"

    def _get_company(self):
        return (
            self.env["res.company"].browse(self.env.context.get("force_company"))
            or self.env.user.company_id
        )

    name = fields.Char()
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=_get_company,
        string="Company",
        required=True,
    )
    date_end = fields.Date(required=True, default=fields.Date.context_today)
    show_aging_buckets = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
    # number_partner_ids = fields.Integer(
    #     default=lambda self: len(self._context["active_ids"])
    # )
    number_partner_ids = fields.Integer(
        default=1
    )
    filter_partners_non_due = fields.Boolean(
        string="Don't show partners with no due entries", default=True
    )
    filter_negative_balances = fields.Boolean("Exclude Negative Balances", default=True)

    aging_type = fields.Selection(
        [("days", "Age by Days"), ("months", "Age by Months")],
        string="Aging Method",
        default="days",
        required=True,
    )

    account_type = fields.Selection(
        [("receivable", "Receivable"), ("payable", "Payable")],
        string="Account type",
        default="receivable",
    )

    mode = fields.Selection(
        [("details", "Details"), ("outstanding", "Outstanding")],
        string="Mode",
        default="outstanding",
    )
    company_currency = fields.Boolean(string="Company Currency")#newly added
    

    @api.onchange("aging_type")
    def onchange_aging_type(self):
        if self.aging_type == "months":
            self.date_end = fields.Date.context_today(self).replace(
                day=1
            ) - relativedelta(days=1)
        else:
            self.date_end = fields.Date.context_today(self)

    def button_export_pdf(self):
        self.ensure_one()
        return self._export()

    def _prepare_statement(self):
        self.ensure_one()
        print("gggggggggggggggggggggggggggg",[self.partner_id.id])
        return {
            "date_end": self.date_end,
            "company_id": self.company_id.id,
            # "partner_ids": self._context["active_ids"],
            "partner_ids": [self.partner_id.id],
            "show_aging_buckets": self.show_aging_buckets,
            "filter_non_due_partners": self.filter_partners_non_due,
            "account_type": self.account_type,
            "aging_type": self.aging_type,
            "mode": self.mode,
            "filter_negative_balances": self.filter_negative_balances,
            "company_currency": self.company_currency,
        }

    def _export(self):
        raise NotImplementedError

    