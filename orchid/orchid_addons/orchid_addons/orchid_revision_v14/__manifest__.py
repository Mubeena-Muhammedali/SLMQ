# -*- encoding: utf-8 -*-
{
	"name": "Orchid Revision v14",
	"version": "0.1",
	"author": "OrchidERP",
	"website": "http://www.orchiderp.com",
	"sequence": 0,
	"depends": ["sale","sale_stock","sale_management","purchase"],
	"category": "Sales,Invoicing",
	"description": """ revision history""",
	"data": [
		'views/sale_order_views.xml',
		'views/purchase_order_views.xml',
		],
	"auto_install": False,
	"installable": True,
	"application": False,
    'images': ['static/description/banner.png'],

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
