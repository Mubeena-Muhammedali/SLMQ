# -*- coding: utf-8 -*-
import io
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):

        report = self._get_report(report_ref)

        if report.report_name != 'invoice_template.sale_order_document':
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        # Skip 2nd pass
        if data and data.get('is_second_pass'):
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        # ── PASS 1 ──────────────────────────────────────────────────
        data = data or {}
        pdf_content, mime = super()._render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data
        )

        # ── Count pages ──────────────────────────────────────────────
        try:
            try:
                from pypdf import PdfReader
            except ImportError:
                from PyPDF2 import PdfReader

            reader = PdfReader(io.BytesIO(pdf_content))
            total_pages = len(reader.pages)
            _logger.info(">>> TOTAL PAGES: %s", total_pages)

        except Exception as e:
            _logger.error(">>> ERROR: %s", e)
            total_pages = 1

        # ── Write page count directly to records ─────────────────────
        orders = self.env['sale.order'].browse(res_ids or [])
        if orders:
            for order in orders:
                order.report_total_pages = total_pages

        # ── PASS 2 ───────────────────────────────────────────────────
        data['is_second_pass'] = True
        pdf_content, mime = super()._render_qweb_pdf(
            report_ref, res_ids=res_ids, data=data
        )

        return pdf_content, mime