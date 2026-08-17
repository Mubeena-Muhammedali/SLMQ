# -*- coding: utf-8 -*-
{
    'name': "Orchid Deferred Revenue",

    'summary': """Custom Deferred Revenue report for ASP Gulf contracts""",
    'description': """
Deferred Revenue reporting built on top of the ASP Gulf contract revenue
schedule (od.contract.payment / od.contract.monthly.line), presented in the
same style as the standard Accounting > Reporting > Deferred Revenue screen:
account rows with Total / Not Started / Before / <period> / Recognized /
Later columns, drill-down to the underlying lines, and PDF/XLSX export.

This is a standalone extension - it does not modify orchid_asp_gulf or the
base Accounting deferred revenue feature in any way.
    """,
    'author': "OrchidERP",
    'website': "http://www.orchiderp.com",
    'category': 'Accounting',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['orchid_asp_gulf', 'account'],

    'data': [
        "security/ir.model.access.csv",

        "views/deferred_revenue_report.xml",
        "reports/deferred_revenue_report.xml",
    ],

    'assets': {
        'web.assets_backend': [
            'orchid_deferred_revenue/static/src/js/deferred_revenue_report.js',
            'orchid_deferred_revenue/static/src/xml/deferred_revenue_report.xml',
            'orchid_deferred_revenue/static/src/scss/deferred_revenue_report.scss',
        ],
    },

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
