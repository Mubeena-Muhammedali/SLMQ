# -*- coding: utf-8 -*-

from odoo import models, api


class ReportInvoiceMultiple(models.AbstractModel):
    _name = 'report.orchid_account_enhancement_v14.report_multiple_invoice'
    _inherit = 'report.account.report_invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        rslt = super()._get_report_values(docids, data)

        inv = rslt['docs']
        layout = inv.journal_id.company_id.external_report_layout_id.key

        if layout == 'web.external_layout_boxed':
            new_layout = 'orchid_account_enhancement_v14.boxed'

        elif layout == 'web.external_layout_clean':
            new_layout = 'orchid_account_enhancement_v14.clean'

        elif layout == 'web.external_layout_background':
            new_layout = 'orchid_account_enhancement_v14.background'

        else:
            new_layout = 'orchid_account_enhancement_v14.standard'

        rslt['mi_type'] = inv.journal_id.multiple_invoice_type
        rslt['mi_ids'] = inv.journal_id.multiple_invoice_ids
        rslt['txt_position'] = inv.journal_id.text_position
        rslt['body_txt_position'] = inv.journal_id.body_text_position
        rslt['txt_align'] = inv.journal_id.text_align
        rslt['layout'] = new_layout

        rslt['report_type'] = data.get('report_type') if data else ''
        return rslt
