# -*- coding: utf-8 -*-
{
    'name': "Radiant House - Customizations (Odoo 18)",

    'summary': "Odoo Customizations for Radiant House",

    'description': """
This module provides custom features for Radiant House including:
- Proof request management
- Product & partner enhancements
- Manufacturing integration
- Customized workflows
    """,

    'author': "Orchidinfosys",
    'website': "https://www.orchiderp.com",

    'category': 'Sales',
    'version': '1.0',

    'depends': [
        'base',
        'sale_management',
        'sale',
        'mrp',
        'purchase',
        'stock',
        'account',
        'sale_mrp',
        'stock_landed_costs',
        'stock_account',
        'hr',
        'base_accounting_kit',
        'orchid_reports_v18',
    ],

    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/sequence.xml',
        'data/estimation_product_data.xml',
        'data/estimation_teeth_size_data.xml',

        'views/product_view.xml',
        'views/partner_view.xml',
        'views/proof_request_view.xml',
        'views/sale_view.xml',
        'views/mrp_view.xml',
        'views/ir_config.xml',
        'views/jumbo_roll_slitting.xml',
        'views/packing_list_view.xml',
        'views/issue_raw_material_view.xml',
        'views/account_move.xml',
        'views/res_company.xml',
        'views/intercompany_transfer.xml',
        'views/bundle_operation.xml',
        'views/inventory_adjustment.xml',
        'views/purchase.xml',
        'views/stock_scrap.xml',
        'views/estimation_view.xml',
        'views/partner_ledger.xml',
        'views/menus.xml',

        'reports/paper_format.xml',
        'reports/report_rhl_letterhead.xml',
        'reports/report_qatar_prints.xml',
        'reports/report_proof_request.xml',
        'reports/report_joborder.xml',
        'reports/report_deliveryorder.xml',
        'reports/report_packinglist.xml',
        'reports/report_sales_order.xml',
        'reports/report_purchaseorder.xml',
        'reports/report_invoice_document.xml',
        'reports/report_stockscrap.xml',
        'reports/report_estimation.xml',
        'reports/report_menu.xml',
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
