# -*- coding: utf-8 -*-
{
    'name': 'Tax Invoice',
    'version': '19.0.1.0.0',
    'summary': 'Custom Tax Invoice format',
    'description': 'Replaces the default invoice PDF report with the Tax Invoice format.',
    'category': 'Accounting',
    'depends': ['sale_project'],
    'data': [
        'security/ir.model.access.csv',
        'report/report_tax_invoice.xml',
        'report/report_action.xml',
        'report/sale_order_report.xml',
        'report/sale_order_report_action.xml',
        'views/res_company_view.xml',
        'views/res_bank.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
