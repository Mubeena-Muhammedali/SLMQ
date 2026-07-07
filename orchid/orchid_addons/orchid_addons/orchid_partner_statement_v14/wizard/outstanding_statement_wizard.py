# Copyright 2018 ForgeFlow, S.L. (http://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class OutstandingStatementWizard(models.TransientModel):
    """Outstanding Statement wizard."""

    _name = "outstanding.statement.wizard"
    _inherit = "statement.common.wizard"
    _description = "Outstanding Statement Wizard"

    @api.model
    def _get_date_start(self):
        return (
            fields.Date.context_today(self).replace(day=1) - relativedelta(days=1)
        ).replace(day=1)

    date_start = fields.Date(required=True, default=_get_date_start)
    
    @api.onchange("aging_type")
    def onchange_aging_type(self):
        if self.mode == 'details':
            super().onchange_aging_type()
            if self.aging_type == "months":
                self.date_start = self.date_end.replace(day=1)
            else:
                self.date_start = self.date_end - relativedelta(days=30)

    def _prepare_statement(self):
        res = super()._prepare_statement()
        if self.mode == 'details':
            res.update({"date_start": self.date_start})
        return res

    def _export(self):
        """Export to PDF."""
        print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")
        print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")
       
        data = self._prepare_statement()
        print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",data)
        if self.mode == 'outstanding':
            return self.env.ref(
                "orchid_partner_statement_v14.action_print_outstanding_statement"
            ).with_context(landscape=True).report_action(self.ids, data=data)

        if self.mode == 'details':
            print("kkkkkkkkkkkkkkkkkkkkkkkkkkkk")
            return self.env.ref(
            "orchid_partner_statement_v14.action_print_activity_statement"
            ).with_context(landscape=True).report_action(self.ids, data=data)

    