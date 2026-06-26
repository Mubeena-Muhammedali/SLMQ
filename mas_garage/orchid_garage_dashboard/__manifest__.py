{
    'name': 'Garage Dashboard',
    'summary': 'KPI Dashboard: Pending Jobs, Closed Jobs, Invoice Pending',
    'version': '19.0.1.0.0',
    'category': 'Services',
    'author': 'OrchidInfosys',
    'website': 'https://orchiderp.com',
    'license': 'LGPL-3',

    'depends': [
        'orchid_garage',
        'web',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/garage_dashboard.xml',
        'views/menu_dashboard.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'orchid_garage_dashboard/static/src/scss/garage_dashboard.scss',
            'orchid_garage_dashboard/static/src/xml/garage_dashboard.xml',
            'orchid_garage_dashboard/static/src/js/garage_dashboard.js',
        ],
    },

    'application': False,
    'installable': True,
    'auto_install': False,
}
