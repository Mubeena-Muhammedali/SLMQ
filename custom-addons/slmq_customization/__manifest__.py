{
    'name': 'SLMQ Customisation',
    'version': '19.0.0.0',
    'depends': ['website','contacts'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/mail_template.xml',
        'views/membership_views.xml',
        'views/res_partner_views.xml'
    ],
    'installable': True,
    'application': True,
}