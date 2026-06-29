# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo import tools


class OdPoCostingView(models.Model):

	_name = 'od.po.costing.view'
	_description = "Purchase Costing View"
	_auto = False

	product_id = fields.Many2one('product.product', string="Product")
	period_from = fields.Date(string="Period From")
	period_to = fields.Date(string="Period To")
	amount = fields.Float(digits='Product Price', string="Cost")
	invoiced = fields.Boolean(string="Posted", default=False)
	move_id = fields.Many2one('account.move', string="Journal Entry", ondelete='restrict')
	purchase_line_id = fields.Many2one('purchase.order.line', string="Purchase Line")




	def init(self):
		cr = self.env.cr   
		tools.drop_view_if_exists(cr, 'od_po_costing_view')
		cr.execute("""
			CREATE or replace view od_po_costing_view as (
				SELECT
				pcl.id as id,
				pcl.period_from as period_from,
				pcl.period_to as period_to,
				pcl.amount as amount,
				pcl.invoiced as invoiced,
				pcl.move_id as move_id,
				pcl.product_id as product_id,
				pl.id as purchase_line_id

				FROM od_po_costing_line pcl
				LEFT JOIN purchase_order_line pl ON pl.id = pcl.purchase_line_id
				
				ORDER BY pcl.period_to ASC
				)
		""")

	
