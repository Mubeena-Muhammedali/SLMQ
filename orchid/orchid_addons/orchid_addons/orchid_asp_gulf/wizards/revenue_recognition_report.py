# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from io import BytesIO
import base64
import pandas as pd

class OrchidRevenueRecognitionReportWizard(models.TransientModel):
	_name = 'od.revenue.recognition.report.wiz'
	_description = "Revenue Recognition Report"


	date_from = fields.Date(string="Date From", required=True)
	date_to = fields.Date(string="Date To", required=True)
	company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")

	def get_data(self):
		if self.date_from and self.date_to:
			data = []
			domain=[('period_from', '>=', self.date_from),('period_from', '<=', self.date_to),('due','=',True)]
			results = self.env['od.contract.monthly.line'].search(domain)
			if not results:
				raise UserError(_("No Data to Generate !!!"))
			line_ls = []
			for line_id in results:
				if line_id.amount>=0:
					payment_lines = self.env['od.contract.payment.line'].search([('period_from','<=',line_id.period_to),('period_to','>=',line_id.period_to),('service_id','=',line_id.service_id.id)])

					invoice_name = ''
					for pl in payment_lines:
						if pl.invoice_line_id:
							invoice_name = invoice_name+pl.invoice_line_id.move_id.name
							date=pl.invoice_line_id.move_id.invoice_date
							invoice_amount=pl.invoice_line_id.credit
					past_period_recognition=self.env['od.contract.monthly.line'].search([('reverse_line_id','=',False),('service_id','=',line_id.service_id.id),('period_from', '<', self.date_from),('due','=',True),('invoiced','=',True)])
					past_period_recognition_amt=0
					for past_line in past_period_recognition:
						past_period_recognition_amt+=past_line.amount
					amount=(line_id.service_id.contract_id.od_exchange_rate*line_id.service_id.total_amount)
					# accrued_income = amount-(past_period_recognition_amt+line_id.amount)
					accrued_income_recognition=self.env['od.contract.monthly.line'].search([('reverse_line_id','=',False),('service_id','=',line_id.service_id.id),('due','=',True),('invoiced','=',False)])
					accrued_income_amt=0
					for f_line in accrued_income_recognition:
						accrued_income_amt+=f_line.amount
					# accrued_income=(line_id.service_id.contract_id.od_exchange_rate*line_id.service_id.total_amount)
					line_vals={
					'Date':date,
					'Customer':line_id.service_id.partner_id.name,
					'Contract Amount': amount,
					'Invoice Amount': invoice_amount,
					'revenue_date_from': line_id.period_from,
					'revenue_date_to': line_id.period_to,
					'Contract period from': line_id.service_id.contract_line_id.billing_from,
					'Contract period to': line_id.service_id.contract_line_id.billing_to,
					'Reference': invoice_name,
					'Product': line_id.service_id.contract_line_id.product_id.name,
					'Account': line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id and line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id.name ,
					"Reve Recongniton Past period":past_period_recognition_amt,
					"Reve Recongniton Current period":line_id.amount,
					"Accrued Income":accrued_income_amt,
					}
				else:
					past_period_recognition=self.env['od.contract.monthly.line'].search([('reverse_line_id','!=',False),('service_id','=',line_id.service_id.id),('period_from', '<', self.date_from),('due','=',True),('invoiced','=',True)])
					past_period_recognition_amt=0
					for past_line in past_period_recognition:
						past_period_recognition_amt+=past_line.amount
					amount=(line_id.service_id.contract_id.od_exchange_rate*line_id.service_id.total_amount)*-1
					# accrued_income = amount-(past_period_recognition_amt+line_id.amount)
					# accrued_income = amount-(past_period_recognition_amt+line_id.amount)
					accrued_income_recognition=self.env['od.contract.monthly.line'].search([('reverse_line_id','!=',False),('service_id','=',line_id.service_id.id),('due','=',True),('invoiced','=',False)])
					accrued_income_amt=0
					for f_line in accrued_income_recognition:
						accrued_income_amt+=f_line.amount
					line_vals={
					'Date':line_id.reverse_line_id.move_id.invoice_date,
					'Customer':line_id.service_id.partner_id.name,
					'Contract Amount': amount,
					'Invoice Amount': line_id.reverse_line_id.debit,
					'revenue_date_from': line_id.period_from,
					'revenue_date_to': line_id.period_to,
					'Contract period from': line_id.service_id.contract_line_id.billing_from,
					'Contract period to': line_id.service_id.contract_line_id.billing_to,
					'Reference': line_id.reverse_line_id.move_id.name,
					'Product': line_id.service_id.contract_line_id.product_id.name,
					'Account': line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id and line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id.name ,
					"Reve Recongniton Past period":past_period_recognition_amt,
					"Reve Recongniton Current period":line_id.amount,
					"Accrued Income":accrued_income_amt,
					}
				data.append(line_vals)
			print("jhgccccccccccc",data)
		return data
	


	def generate_excel(self):
		print("hllllll")
		data_ls = self.get_data()
		print("jjjjjjjjjm",data_ls)
		filename ='RevenueRecognitionReport.xlsx'
		from_date =datetime.strptime(str(self.date_from),'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(str(self.date_to),'%Y-%m-%d').strftime('%d-%m-%Y')
		title="Revenue Recognition Report- "+ from_date + " "+"to " +to_date
		writer = pd.ExcelWriter(filename, engine='xlsxwriter')
		fp = BytesIO()
		writer.book.filename = fp
		workbook  = writer.book
		title_format = workbook.add_format({
			'bold': True,
			'align': 'center',
			'fg_color': '#D7E4BC',
			'border': 0}) 
		header_style = workbook.add_format({
			'bold': True,
			'align': 'center',
			'border':0})
		tot_format = workbook.add_format({
			'bold': True,
			'align': 'left',
			'border': 0})
		tot_format1 = workbook.add_format({
			'bold': True,
			'align': 'right',
			'num_format': '#,##0.00',
			'border': 0})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'})	

		header=["Date","Customer","Reference","Contract Amount","Invoice Amount","Contract period from","Contract period to","Product","Account","Reve Recongniton Past period","Reve Recongniton Current period","Accrued Income"]
		dataframe= pd.DataFrame(data_ls,columns=header)
		dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
		worksheet = writer.sheets['Sheet1']
		worksheet.set_column('A:A',20)
		worksheet.set_column('B:B',30)
		worksheet.set_column('C:C',20)
		worksheet.set_column('D:D',20,row_num_style)
		worksheet.set_column('E:E',20,row_num_style)
		worksheet.set_column('F:F',25)
		worksheet.set_column('G:G',30)
		worksheet.set_column('H:H',30)
		worksheet.set_column('I:I',30)
		worksheet.set_column('J:J',30,row_num_style)
		worksheet.set_column('K:K',30,row_num_style)
		worksheet.set_column('L:L',30,row_num_style)
		col=0
		col_merge=len(header)-1
		row=0
		row_merge=0
		worksheet.merge_range(row,row_merge,col,col_merge,title, title_format)
		row=row+1
		for head in header:
			worksheet.write(row,col,head,header_style)
			col=col+1

		writer.save()
		excel_file = base64.encodestring(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()

		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.revenue.recognition.report.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }