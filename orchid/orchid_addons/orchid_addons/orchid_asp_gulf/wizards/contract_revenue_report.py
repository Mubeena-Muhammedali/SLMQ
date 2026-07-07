# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

class OdContractRevenueReportWiz(models.TransientModel):
	_name = 'od.contract.revenue.report.wiz'
	_description = "Current year revenue report"

	year = fields.Selection([(str(y), str(y)) for y in range(2010, (datetime.now().year + 30)+1 )], string="Year", default=str(datetime.now().year))
	date_start = fields.Date(string="Date Start")
	date_end = fields.Date(string="Date End")

	@api.onchange('year')
	def onchange_dates(self):
		for wiz in self:
			date_start = fields.Date.today().replace(day=1, month=7)
			end_year = int(wiz.year) + 1 
			date_end = fields.Date.today().replace(day=30, month=6, year=end_year)
			if wiz.year:
				date_start = date_start.replace(year=int(wiz.year))
				date_end = date_end.replace(year=int(wiz.year)+1)
				wiz.write({'date_start':date_start, 'date_end':date_end})

	def action_view_report(self):

		self._cr.execute('''DELETE FROM od_contract_revenue_report''')

		# data_fetch_qry = ''' SELECT cont_line.id 
		# 					FROM od_asp_contract_line cont_line
		# 					LEFT JOIN od_asp_contract cont ON cont.id= cont_line.order_id
		# 					WHERE cont.renewed is not true AND cont_line.billing_from >='%s' AND cont_line.billing_from <='%s' '''%(self.date_start, self.date_end)

		data_fetch_qry = '''SELECT 
								cont.contract_code as name, cont.partner_id as partner_id, cont.sam_id as user_id, cont_line.product_id as product_id,
								CASE WHEN cont_line.billing_cycle = 'one_time' THEN sum(cont_line.price_subtotal)*cont.od_exchange_rate ELSE 0 END AS expected_revenue,
								CASE WHEN cont_line.billing_cycle <> 'one_time' THEN (sum(cont_line.price_subtotal)/cont_line.frequency)*cont.od_exchange_rate ELSE 0 END AS recurring_revenue_monthly,
								CASE WHEN cont_line.billing_cycle <> 'one_time' THEN sum(cont_line.price_subtotal)*cont.od_exchange_rate ELSE 0 END AS recurring_revenue,
								sum(cont_line.price_subtotal)*cont.od_exchange_rate as total_revenue
								    
								FROM od_asp_contract_line cont_line
								LEFT JOIN od_asp_contract cont ON cont.id= cont_line.order_id
								WHERE cont.renewed is not true AND cont.new_business is true AND cont_line.billing_from >='%s' AND cont_line.billing_from <='%s' AND cont_line.state='active'
								GROUP BY cont.contract_code, cont.partner_id,cont.sam_id,cont_line.product_id,cont_line.billing_cycle, cont_line.frequency, cont_line.id,cont.od_exchange_rate '''%(self.date_start, self.date_end)
										
		self._cr.execute(data_fetch_qry)
		print(data_fetch_qry)
		data = self._cr.dictfetchall()
		if not data:
			raise UserError(_("No Data !!"))
		for res in data:
			vals = {
			'name':res['name'],
			'partner_id':res['partner_id'],
			'user_id':res['user_id'],
			'product_id':res['product_id'],
			'expected_revenue':res['expected_revenue'],
			'recurring_revenue_monthly':res['recurring_revenue_monthly'],
			'recurring_revenue':res['recurring_revenue'],
			'total_revenue':res['total_revenue'],
			}
			data_id = self.env['od.contract.revenue.report'].create(vals)

		return self.env["ir.actions.actions"]._for_xml_id("orchid_asp_gulf.od_contract_revenue_report_action")
