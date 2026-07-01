# -*- coding: utf-8 -*-
{
    "name" : "Orchid GPCA",
    "version" : "0.1",
    "author": "OrchidERP",
    "category" : "Human Resources",
    "description": """Orchid GPCA """,
    "website": "http://www.orchiderp.com",
    "depends": ['base','sale_management','account'],
    "data" : [
            'security/ir.model.access.csv',
            'views/product.xml',
            'views/account_move.xml',
            'views/masters.xml',
            'views/menu.xml',
            'report/report_invoice_templates.xml',
            'report/report_actions.xml',

            
        
            ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
