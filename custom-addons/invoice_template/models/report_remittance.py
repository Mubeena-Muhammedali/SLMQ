from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _run_wkhtmltopdf(self, bodies, report_ref=False, header=None, footer=None,
                         landscape=False, specific_paperformat_args=None,
                         set_viewport_size=False):


        report_name = ''
        if report_ref:
            try:
                report = self._get_report(report_ref)
                report_name = report.report_name or ''
            except Exception:
                if isinstance(report_ref, str):
                    report_name = report_ref

        #is_tax_invoice = report_name == 'invoice_template.tax_invoice_document'
        is_tax_invoice = report_name in [
            'invoice_template.tax_invoice_document',
            'invoice_template.sale_order_document',
        ]

        if not is_tax_invoice:
            return super()._run_wkhtmltopdf(
                bodies, report_ref=report_ref, header=header, footer=footer,
                landscape=landscape,
                specific_paperformat_args=specific_paperformat_args,
                set_viewport_size=set_viewport_size,
            )

        company = self.env.company
        tax_id = company.vat or ''
        #doc_title = 'TAX INVOICE'
        if report_name == 'invoice_template.tax_invoice_document':
            doc_title = 'TAX INVOICE'

        elif report_name == 'invoice_template.sale_order_document':
            doc_title = 'QUOTE'

        else:
            doc_title = ''
        phone = company.phone or ''
        fax_part = (', Fax: ' + company.fax_no) if (hasattr(company, 'fax_no') and company.fax_no) else ''

        # Build logo tag separately to avoid f-string issues with long base64
        if company.logo:
            logo_b64 = company.logo.decode('utf-8') if isinstance(company.logo, bytes) else company.logo
            logo_tag = '<img src="data:image/png;base64,' + logo_b64 + '" style="height:60px; max-width:100%; display:block; margin:0 auto;"/>'
        else:
            logo_tag = ''

        # Header HTML
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        vat = company.vat or ''
        header_html = '\n'.join([
                                    '<!DOCTYPE html><html><head><meta charset="UTF-8"/>',
                                    '<style>',

                                    '@font-face { font-family: Magneto; src: url("' + base_url + '/remittance_advice/static/src/fonts/MAGNETOB.TTF") format("truetype"); font-weight: bold; }',
                                    '@font-face { font-family: Calibri; src: url("' + base_url + '/remittance_advice/static/src/fonts/CALIBRI.TTF") format("truetype"); font-weight: normal; }',
                                    '@font-face { font-family: Calibri; src: url("' + base_url + '/remittance_advice/static/src/fonts/CALIBRIB.TTF") format("truetype"); font-weight: bold; }',

                                    '* { margin:0; padding:0; box-sizing:border-box; }',

                                    'body { margin:0; padding:0; font-family: Arial, sans-serif;'
                                    '}',
        '.page-border {'
            '               position: fixed;',
            '               top: 0px;',
            '               bottom: 0px;',
            '               left: 0px;',
            '               right: 0px;',
            '               height: 1220px;',
            '               border: 3px solid #3fb5d4;',
            '               box-sizing: border-box;',
            '               pointer-events: none;',
                    '}',

        '.hw { width:100%; border:1px solid #aaa;'
        '       background:white; display:table; table-layout:fixed; }',

        '.c1, .c2, .c3 { display:table-cell; vertical-align:middle; padding:6px; }',

        '.c1 { width:33%; border-right:1px solid #aaa; text-align:left; }',

        '.c2 { width:26%; border-right:1px solid #aaa; text-align:center; }',
        '.c2 div { font-weight:bold; font-size:13pt; }',

        '.c3 { width:37%; text-align:right; }',

        '.c3 .d { font-size:8pt; color:#333; font-weight:bold; margin-top:3px; }',

        '</style></head><body>',
        '<div class="page-border"></div>',

        '<div class="hw">',

            # Logo
        '  <div class="c1">' + logo_tag + '</div>',

            # Title
        '  <div class="c2"><div>' + doc_title + '</div></div>',

            # Right Section
        '  <div class="c3">',

            # Company Name (Styled)
        '    <div style="line-height:1.3;">'
        '        <span style="font-family:Magneto,\'Brush Script MT\',cursive;'
        '                     font-weight:bold; letter-spacing:2px; font-size:15pt;">AVS</span>'
        '        <span style="font-family:Calibri,Arial,sans-serif;'
        '                     font-weight:bold; font-size:11pt; margin-left:6px;">Security Systems LLC</span>'
        '    </div>',

            # Contact + TRN
        '    <div class="d">Tel: ' + phone + fax_part +
        (('<br/>TRN: ' + vat) if vat else '') +
        '<br/>www.avssgroup.com</div>',

        '  </div>',

        '</div>',
        '</body></html>',
        ])

        # Footer HTML
        footer_html = '\n'.join([
            '<!DOCTYPE html><html><head><meta charset="UTF-8"/>',
            '<script>',
            'function subst() {',
            '    var vars = {};',
            '    var q = document.location.search.substring(1).split("&");',
            '    for (var i in q) { var t = q[i].split("=", 2); vars[t[0]] = decodeURI(t[1]); }',
            '    var p = document.getElementById("page");',
            '    var tp = document.getElementById("topage");',
            '    if (p) p.innerHTML = vars["page"];',
            '    if (tp) tp.innerHTML = vars["topage"];',
            '}',
            '</script>',
            '<style>',
            '* { margin:0; padding:0; box-sizing:border-box; }',
            'body { margin:0; padding:0; font-family: Arial, sans-serif;'
            'font-size:9pt; color:#444; text-align:center;'
            ' }',
            '.fw {',
            '    padding:3px 0; background:transparent;',
            '}',
            '</style>',
            '</head>',
            '<body onload="subst()">',
            '<div class="fw">Page <span id="page"></span> / <span id="topage"></span></div>',
            '</body></html>',
        ])

        if specific_paperformat_args is None:
            specific_paperformat_args = {}
        specific_paperformat_args['data-report-header-spacing'] = '5'
        specific_paperformat_args['data-report-margin-top'] = '30'
        specific_paperformat_args['data-report-margin-bottom'] = '10'



        return super()._run_wkhtmltopdf(
            bodies,
            report_ref=report_ref,
            header=header_html,
            footer=footer_html,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
