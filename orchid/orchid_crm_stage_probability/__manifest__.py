# -*- coding: utf-8 -*-
{
    'name': "Orchid CRM stage probability",
    'summary': """Define fixed probability on the stages""",
    'author': "OrchidERP",
    'website': "http://www.orchiderp.com",
    'category': 'Sales/CRM',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['crm'],

    # always loaded
    'data': [
        "data/crm_stage.xml",
        'security/ir.model.access.csv',
        "views/crm_lead.xml",
        "views/crm_stage.xml",
        "wizard/crm_lead_stage_probability_update.xml",
    ],
    
}
