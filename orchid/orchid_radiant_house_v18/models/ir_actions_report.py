# -*- coding: utf-8 -*-

from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report = self._get_report(report_ref)
        if (
            not self.env.context.get('rhl_qatar_invoice_paperformat')
            and report.report_name == 'account.report_invoice'
            and report.model == 'account.move'
            and res_ids
        ):
            moves = self.env['account.move'].browse(res_ids)
            if moves and all('Radiant House Labels Trading' in move.company_id.name for move in moves):
                return super(
                    IrActionsReport,
                    self.with_context(rhl_qatar_invoice_paperformat=True),
                )._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)

    def get_paperformat(self):
        if (
            self.env.context.get('rhl_qatar_invoice_paperformat')
            and self.report_name == 'account.report_invoice'
        ):
            paperformat = self.env.ref(
                'orchid_radiant_house_v18.rhl_qatar_invoice_paper_format',
                raise_if_not_found=False,
            )
            if paperformat:
                return paperformat
        return super().get_paperformat()
