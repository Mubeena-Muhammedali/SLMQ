# -*- coding: utf-8 -*-
{
    'name': "Orchid ASPGulf",

    'summary': """Customized Module for ASPGulf""",
    'author': "OrchidERP",
    'website': "http://www.orchiderp.com",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['sale_project','sale_crm','purchase'],

    # always loaded
    'data': [
        "data/data.xml",
        "data/schedule_actions.xml",
        "data/contract_seq.xml",
        "data/crm_stage.xml",

        "security/security.xml",
        "security/ir.model.access.csv",

        "wizards/advance_contract_invoice.xml",
        "wizards/merge_revenue.xml",
        "wizards/renew_contract.xml",
        "wizards/terminate_contract_line.xml",
        "wizards/contract_revenue_report.xml",
        "wizards/multiple_contract_invoice.xml",
        "wizards/lead_assign_user.xml",
        "wizards/revenue_recognition.xml",
        "wizards/contract_credit_note.xml",
        "wizards/revenue_recognition_report.xml",
        "wizards/crm_lead_stage_probability_update.xml",

        "views/account_move_view.xml",
        "views/contract_view.xml",
        "views/contract_payment_view.xml",
        "views/account_payment_view.xml",
        "views/cost_booking_view.xml",
        "views/crm.xml",
        "views/fluctuating_contract.xml",
        "views/purchase.xml",
        "views/partner.xml",
        "views/product_correction_utility.xml",
        "views/product.xml",
        "views/provision_form_view.xml",
        "views/provision_masters.xml",
        "views/sale.xml",
        "views/revenue_forecast_assets.xml",
        "views/revenue_forecast_report.xml",
        "views/res_bank.xml",
        "views/crm_stage.xml",
        "views/company_view.xml",
        "views/menus.xml",

        'reports/asp_sale_print.xml',
        'reports/asp_tax_invoice_print.xml',
        'reports/asp_tax_invoice_print_aed.xml',
        'reports/asp_usd_vat_print.xml',
        'reports/sale_paper_format.xml',
        'reports/contract_analysis_report.xml',
        'reports/purchase_costing.xml',
        'reports/revenue_line_view.xml',
        'reports/purchase_requisition.xml',
        'reports/purchase_order.xml',
        'reports/contract_revenue_report.xml',
        'reports/revenue_recognition_report.xml',
        'reports/report_enbd_cheque_print.xml',
        'reports/report_fab_cheque_print.xml',
        'reports/menu.xml',
        
    ],
    'qweb': [
        'static/src/xml/revenue_forecast_report.xml',
    ],

    'assets': {
    'web.assets_backend': [
        'orchid_asp_gulf/static/src/scss/revenue_forecast_report.scss',
        'orchid_asp_gulf/static/src/js/revenue_forecast_report.js',
    ],
},
    
}
