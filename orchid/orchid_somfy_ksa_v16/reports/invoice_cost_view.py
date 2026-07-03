from odoo import fields,models,api,_
from odoo import tools

# OrchidAccountInvoiceCost
class OrchidAccountInvoiceDropShippingCostView(models.Model):
	_name = "orchid.account.invoice.dropshipping.cost"
	_description = 'Orchid Account Invoice Dropshipping Cost'
	_auto = False

	amount_currency_cost = fields.Float(string="Amount Currency Cost")
	cost = fields.Float(string="Cost")
	inv_id = fields.Many2one('account.move', string="Invoice")
	product_id = fields.Many2one('product.product', string="Product")
	quantity = fields.Float(string="Quantity")

	def init(self):
		tools.drop_view_if_exists(self.env.cr, self._table)
		self.env.cr.execute("""
			CREATE OR REPLACE VIEW %s AS (
				SELECT row_number() OVER (ORDER BY inv.id) AS id,
					inv.id AS inv_id,
					mvl.product_id,
					mvl.quantity,
					CASE
						WHEN inv.move_type = 'out_invoice' AND mvl.quantity<>0 THEN (sum(mvl.debit)/sum(mvl.quantity))
						WHEN inv.move_type = 'out_refund' AND mvl.quantity<>0 THEN ((sum(mvl.credit)/sum(mvl.quantity) )* (-1))
						ELSE 0
					END AS cost,
					CASE
						WHEN inv.move_type in ('out_invoice','out_refund') AND mvl.quantity<>0 THEN (sum(mvl.amount_currency)/sum(mvl.quantity))
						ELSE 0
					END AS amount_currency_cost
				FROM account_move_line mvl
				 JOIN account_account acc ON mvl.account_id = acc.id
				 JOIN account_move inv ON inv.od_cos_entry_id = mvl.move_id
				WHERE acc.account_type='expense_direct_cost' AND inv.move_type IN ('out_invoice', 'out_refund')
				GROUP BY inv.move_type, inv.id,mvl.quantity, mvl.product_id
			)
		""" % (self._table,))

class OrchidAccountInvoiceCostView(models.Model):
	_inherit = "orchid.account.invoice.cost"

	# def init(self):
	# 	tools.drop_view_if_exists(self.env.cr, self._table)
	# 	self.env.cr.execute("""
	# 		CREATE OR REPLACE VIEW %s AS (
	# 			SELECT row_number() OVER (ORDER BY inv.id) AS id,
	# 				inv.id AS inv_id,
	# 				mvl.product_id,
	# 				SUM(mvl.quantity+mvl.od_free_qty+mvl.od_adjustment_qty) as quantity,
	# 				CASE
	# 					WHEN inv.move_type = 'out_invoice' THEN abs(mvl.price_unit)
	# 					WHEN inv.move_type = 'out_refund'  THEN abs(sum(mvl.price_unit))* (-1)
	# 					ELSE 0
	# 				END AS cost,
	# 				CASE
	# 					WHEN inv.move_type in ('out_invoice','out_refund') THEN (abs(sum(mvl.price_unit))/inv.od_exchange_rate)
	# 					ELSE 0
	# 				END AS amount_currency_cost
	# 			FROM account_move_line mvl
	# 			 JOIN account_account acc ON mvl.account_id = acc.id
	# 			 JOIN account_move inv ON inv.id = mvl.move_id
	# 			WHERE acc.account_type='expense_direct_cost' AND inv.move_type IN ('out_invoice', 'out_refund')
	# 			GROUP BY inv.move_type, inv.id,mvl.price_unit, mvl.product_id
	# 		)
	# 	""" % (self._table,))

	def init(self):
		tools.drop_view_if_exists(self.env.cr, self._table)
		self.env.cr.execute("""
			CREATE OR REPLACE VIEW %s AS (
				SELECT row_number() OVER (ORDER BY inv.id) AS id,
					inv.id AS inv_id,
					mvl.product_id,
					SUM(mvl.quantity+mvl.od_free_qty+mvl.od_adjustment_qty) as quantity,
					CASE
						WHEN inv.move_type = 'out_invoice' THEN abs(mvl.od_per_cost)
						WHEN inv.move_type = 'out_refund'  THEN abs(sum(mvl.od_per_cost))* (-1)
						ELSE 0
					END AS cost,
					CASE
						WHEN inv.move_type in ('out_invoice','out_refund') THEN (abs(sum(mvl.od_per_cost))/inv.od_exchange_rate)
						ELSE 0
					END AS amount_currency_cost
				FROM account_move_line mvl
				 JOIN account_account acc ON mvl.account_id = acc.id
				 JOIN account_move inv ON inv.id = mvl.move_id
				WHERE mvl.display_type='product' AND inv.move_type IN ('out_invoice', 'out_refund')
				GROUP BY inv.move_type, inv.id,mvl.od_per_cost, mvl.product_id
			)
		""" % (self._table,))













