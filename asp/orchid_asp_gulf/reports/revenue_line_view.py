# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo import tools


class OdRevenueLineView(models.Model):

	_name = 'od.revenue.line.view'
	_description = "Revenue Recognition View"
	_auto = False

	period_from = fields.Date(string="Period From")
	period_to = fields.Date(string="Revenue Date")
	amount = fields.Float(digits='Product Price', string="Amount")
	invoice_line_id = fields.Many2one('account.move.line', string="Invoice Line")
	reverse_line_id = fields.Many2one('account.move.line', string="Reverse Line")
	invoice_date = fields.Date(string="Invoice Date")
	reverse_date = fields.Date(string="Reverse Date")
	invoiced = fields.Boolean(string="Posted", default=False)
	due = fields.Boolean(string="Due", default=False)
	move_id = fields.Many2one('account.move', string="Journal Entry", ondelete='restrict')
	partner_id = fields.Many2one('res.partner', string="Customer")
	# invoice_id = fields.Many2one('account.move', string="Invoice Number")
	# reverse_id = fields.Many2one('account.move', string="Reverse Number")
	invoice_id = fields.Char(string="Invoice Number")
	reverse_id = fields.Char(string="Reverse Number")
	recognition_date = fields.Date(string="Recognition Date")
	contract_id = fields.Many2one('od.asp.contract', string="Contract")



	def init(self):
		cr = self.env.cr   
		tools.drop_view_if_exists(cr, 'od_revenue_line_view')
		cr.execute("""
			CREATE or replace view od_revenue_line_view as (
				SELECT
					ml.id as id,
					ml.period_from as period_from,
					ml.period_to as period_to,
					ml.amount as amount,
					ml.invoice_line_id as invoice_line_id,
					ml.reverse_line_id as reverse_line_id,
					ml.invoice_date as invoice_date,
					ml.reverse_date as reverse_date,
					ml.invoiced as invoiced,
					ml.due as due,
					ml.move_id as move_id,
					pay.partner_id as partner_id,
					am.name as invoice_id,
					rm.name as reverse_id,
					ml.recognition_date as recognition_date,
					pay.contract_id as contract_id
				FROM od_contract_monthly_line ml
				LEFT JOIN od_contract_payment pay ON (pay.id=ml.service_id)
				LEFT JOIN account_move_line mvl ON (mvl.id=ml.invoice_line_id)
				LEFT JOIN account_move_line rvl ON (rvl.id=ml.reverse_line_id)
				LEFT JOIN account_move am ON (am.id=mvl.move_id)
				LEFT JOIN account_move rm ON (rm.id=rvl.move_id)
			)
		""")






















