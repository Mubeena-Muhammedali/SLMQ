# -*- coding: utf-8 -*-
{
    'name': "orchid_prepayment_v14",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account','orchid_account_enhancement_v14'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/account_view.xml',
        'views/prepaid_analysis_view.xml',
        # 'views/prepayment_lines_board_view.xml',
        'wizard/prepayment_wizard_view.xml',
        'wizard/prepayment_report.xml', 
        'views/prepayment_lines_view.xml',

    ],
    
}