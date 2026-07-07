# -*- coding: utf-8 -*-
{
    'name': "Orchid Year Closing v14",

    'summary': """Accounts Localization by Orchid Infosys""",
    'author': "Orchid Infosys",
    'website': "http://www.orchidinfosys.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','orchid_account_enhancement_v14'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/od_period_closing_wizard_view.xml',
        'views/menu.xml',
        'views/account_journal.xml',
        'wizard/account_common_report.xml',
    ],
    
}
