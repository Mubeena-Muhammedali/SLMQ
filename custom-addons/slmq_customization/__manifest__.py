{
    'name': 'SLMQ Customization',
    'version': '19.0.0.1',
    'summary': 'This module contains customizations for the SLMQ project',
    'description': """This module contains customizations for the SLMQ project""",
    'category': 'Event Website, Contacts',
    'website': 'https://slmq.org',
    'author': 'FSI',
    'license': 'LGPL-3',
    'depends': ['contacts','website_event'],
    'data': [ 
        'views/res_partner_view.xml', 
        'views/event_registration_view.xml',
        'views/event_event_view.xml',
        'views/membership_template_view.xml',
        'views/event_registration_template.xml',
    ], 
    'assets': {},
    'test': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True, 
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: