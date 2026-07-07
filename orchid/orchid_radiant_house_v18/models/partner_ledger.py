# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountPartnerLedger(models.TransientModel):
    _inherit = "account.report.partner.ledger"

    partner_ids = fields.Many2many("res.partner", string="Partners")

    def pre_print_report(self, data):
        data = super().pre_print_report(data)
        data["form"].update(self.read(["partner_ids"])[0])
        return data


class ReportPartnerLedger(models.AbstractModel):
    _inherit = "report.base_accounting_kit.report_partnerledger"

    def _get_report_values(self, docids, data=None):
        values = super()._get_report_values(docids, data=data)
        selected_partner_ids = data.get("form", {}).get("partner_ids") if data else False
        if selected_partner_ids:
            selected_partner_ids = set(selected_partner_ids)
            partners = [
                partner for partner in values["docs"]
                if partner.id in selected_partner_ids
            ]
            values.update({
                "doc_ids": [partner.id for partner in partners],
                "docs": partners,
            })
        return values
