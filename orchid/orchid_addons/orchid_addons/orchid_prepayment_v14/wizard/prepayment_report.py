# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from io import BytesIO
import base64
import pandas as pd

class OrchidPrepaymentReportWizard(models.TransientModel):
	_name = 'od.prepayment.report.wiz'
	_description = "Prepayment Report"


	date_from = fields.Date(string="Date From", required=True)
	date_to = fields.Date(string="Date To", required=True)
	company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")

	def get_data(self):
		if self.date_from and self.date_to:
			data = []
			# domain=[('state','=','in_progress'),'|',('date_start', '>=', self.date_from),('date_end', '<=', self.date_to)]
			# prepayment_ids = self.env['orchid.prepayment.lines'].search(domain)

			prepayment_qry = """SELECT  p.id FROM orchid_prepayment_board_history h
								LEFT JOIN orchid_prepayment_lines p ON (p.id=h.prepayment_id)
								WHERE p.state='in_progress' AND h.date>='%s' AND h.date<='%s' AND p.company_id=%s GROUP BY p.id"""%(self.date_from,self.date_to,self.company_id.id)
			self._cr.execute(prepayment_qry)
			prepayment_ids=[z[0] for z in self._cr.fetchall()]
			if not prepayment_ids:
				raise UserError(_("No Data to Generate !!!"))
			count=0
			for pre_payment in prepayment_ids:
				pre_payment_id = self.env['orchid.prepayment.lines'].browse(pre_payment)
				count+=1
				past_amount = current_amount = balance =0
				for prepay_line in pre_payment_id.line_history_ids:
					if prepay_line.date<self.date_from:
						past_amount+=prepay_line.amount
					if prepay_line.date>=self.date_from and prepay_line.date<=self.date_to:
						current_amount+=prepay_line.amount
				original_amount=pre_payment_id.debit
				balance = original_amount-(past_amount+current_amount)
				vals={
				'Sr':count,
				'Date':pre_payment_id.date,
				'Reference':pre_payment_id.move_id.name,
				'Description':pre_payment_id.remark,
				'Period From':pre_payment_id.date_start,
				'Period To':pre_payment_id.date_end,
				'Original Amount':original_amount,
				'Charge to PL (o/b)':past_amount,
				'Charge to PL (current period)':current_amount,
				'Remaining Balance':balance,
				}
				
				data.append(vals)
			# print("jhgccccccccccc",data)
		return data,count
	


	def generate_excel(self):
		# print("hllllll")
		data_ls,count = self.get_data()
		# print("jjjjjjjjjm",data_ls)
		filename ='PrepaymentReport.xlsx'
		from_date =datetime.strptime(str(self.date_from),'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(str(self.date_to),'%Y-%m-%d').strftime('%d-%m-%Y')
		title="Prepayment Report- "+ from_date + " "+"to " +to_date
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

		header = ['Sr','Date','Reference','Description','Period From','Period To','Original Amount','Charge to PL (o/b)','Charge to PL (current period)','Remaining Balance']
		dataframe= pd.DataFrame(data_ls,columns=header)
		dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
		worksheet = writer.sheets['Sheet1']
		worksheet.set_column('A:A')
		worksheet.set_column('B:B',20)
		worksheet.set_column('C:C',20)
		worksheet.set_column('D:D',20)
		worksheet.set_column('E:E',25)
		worksheet.set_column('F:F',30)
		worksheet.set_column('G:G',30,row_num_style)
		worksheet.set_column('H:H',30,row_num_style)
		worksheet.set_column('I:I',30,row_num_style)
		worksheet.set_column('J:J',30,row_num_style)
		col=0
		col_merge=len(header)-1
		row=0
		row_merge=0
		worksheet.merge_range(row,row_merge,col,col_merge,title, title_format)
		row=row+1
		for head in header:
			worksheet.write(row,col,head,header_style)
			col=col+1

		row=count+3
		col=0
		worksheet.write(row,col,"Total",tot_format)
		col=col+6
		for column in ['Original Amount','Charge to PL (o/b)','Charge to PL (current period)','Remaining Balance']:
			total=dataframe[column].sum()
			worksheet.write(row,col,total,tot_format1)
			col+=1

		writer.save()
		excel_file = base64.encodestring(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()

		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.prepayment.report.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }