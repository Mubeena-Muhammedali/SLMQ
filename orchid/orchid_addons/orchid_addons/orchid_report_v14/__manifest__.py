# -*- coding: utf-8 -*-
{
    'name': "orchid_report_v14",
    'description': """
        OrchidERP Reporting Template
    """,
    'author': "OrchidERP",
    'website': "http://www.orchiderp.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Base',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'reports/od_ir_actions_report_xml_view.xml',
        'reports/od_ir_ui_view_view.xml',
        'reports/company_view.xml',
    ],
    
}
