{
    'name': 'Remittance Advice Report',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Custom Remittance Advice Report for AVS Security Systems LLC',
    'description': """
        Custom Remittance Advice report for AVS Security Systems LLC.
    """,
    'author': '',
    'website': '',
    'depends': [
        'invoice_template',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/remittance_advice_report.xml',
        'report/remittance_advice_action.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
