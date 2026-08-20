# -*- coding: utf-8 -*-
{
    'name': "Partner Statement",

    'summary': """Financial Reports""",
    'author': "Orchiderp",
    'website': "http://www.orchiderp.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting & Finance',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account'],
    'external_dependencies': {'python': ['dateutil']},

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/statement_security.xml',
        'views/activity_statement.xml',
        'views/outstanding_statement.xml',
        'views/assets.xml',
        'views/aging_buckets.xml',
        'views/res_config_settings.xml',
        # 'views/partner_statement_paper_format.xml',
        'wizard/statement_wizard.xml',
    ],
    
}
