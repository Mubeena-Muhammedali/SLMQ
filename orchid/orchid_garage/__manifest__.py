{
    'name': 'Garage Management',

    'summary': 'Garage Workshop and Vehicle Service Management',

    'description': """
        Garage Management System for:
        - Vehicle Estimation
        - Quotations
        - Job Cards
        - Purchase Management
        - Workshop Operations
        - Invoice Management
        - Analytic Cost Tracking
    """,

    'author': 'OrchidInfosys',
    'website': 'https://orchiderp.com',

    'category': 'Services',
    'version': 'saas~19.2.1.0',

    'license': 'LGPL-3',

    'depends': [
        'sale_management',
        'purchase',
        'hr',
        'stock',
    ],

    'data': [

        # SECURITY
        'security/ir.model.access.csv',

        # DATA
        'data/sequence.xml',

        # VIEWS
        'views/masters.xml',
        'views/garage_estimation.xml',
        # 'views/garage_job.xml',
        'views/sale.xml',
        'views/account_payment.xml',
        'views/purchase_order_view.xml',
        'views/res_company_view.xml',
        'views/garage_dashboard.xml',
        'views/menu.xml',
        

        # WIZARDS
        'wizard/garage_discount_wizard_views.xml',

        # REPORTS
        'reports/report_garage_estimation.xml',
        'reports/report_garage_job.xml',
        'reports/report_invoice.xml',
        'reports/menu.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'orchid_garage/static/src/scss/garage_dashboard.scss',
            'orchid_garage/static/src/xml/garage_dashboard.xml',
            'orchid_garage/static/src/js/garage_dashboard.js',
        ],
    },


    'application': True,

    'installable': True,

    'auto_install': False,
}