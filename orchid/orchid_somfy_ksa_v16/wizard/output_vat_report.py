from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd

class OrchidVATOutputReport(models.TransientModel):
	
	_name = 'orchid.vat.output.report'
	_description = 'VAT Output Report'
	
	
	from_date = fields.Date(string="Start Date",required=True)	
	to_date = fields.Date(string="End Date",required=True)
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")

	@api.onchange('from_date','to_date')
	def date_check(self):
		if self.from_date and self.to_date:
			if self.from_date > self.to_date:
				raise UserError('Start Date must be anterior to End Date')

	def get_vat_output_data(self, from_date, to_date, company_id):
		vat_output_qry = ('''SELECT 
						ai.number as inv_no,
						to_char(ai.date_invoice, 'DD/MM/YYYY') AS date,
						res.name AS customer,
						pp.default_code as scode,
						tmpl.name as sdes,
						ivl.quantity as qty,
						ivl.price_unit as rate,
						ivl.price_subtotal as amount,
						(((sum(COALESCE(tax.amount,0))*ivl.price_subtotal)/100)/(ivl.price_subtotal))*100 as vat_rate,
						((sum(COALESCE(tax.amount,0))*ivl.price_subtotal)/100) as vat_amount,
				   		ivl.price_subtotal + ((sum(COALESCE(tax.amount,0))*ivl.price_subtotal)/100) as total_amount,
				   		ai.od_exchange_rate as exchange_rate,
				   		(((sum(COALESCE(tax.amount,0))*ivl.price_subtotal)/100)*ai.od_exchange_rate) as sar_vat
						
						FROM account_invoice ai
						LEFT JOIN account_invoice_line ivl ON ivl.invoice_id = ai.id
						LEFT JOIN res_partner res  ON res.id = ai.partner_id
						LEFT JOIN product_product pp ON pp.id = ivl.product_id
						LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
						LEFT JOIN account_invoice_line_tax lt ON lt.invoice_line_id = ivl.id
						LEFT JOIN account_tax tax ON tax.id = lt.tax_id
						WHERE lt.invoice_line_id = ivl.id and ai.type='out_invoice' and ai.state IN ('open','paid')
						 AND ai.date_invoice BETWEEN '%s' AND '%s' AND ai.company_id = %s 
						GROUP BY ai.type,ai.number,ai.date_invoice,res.name,pp.default_code,tmpl.name,ivl.quantity,ivl.price_unit,ivl.price_subtotal,ai.od_exchange_rate
						ORDER BY ai.date_invoice''')%(from_date,to_date,company_id)

		
		self._cr.execute(vat_output_qry)
		vat_output_data = self._cr.dictfetchall()
		if vat_output_data:
			for vat in vat_output_data:
				vat['inv_type'] = "Tax Customer Invoice"
			return vat_output_data
		else:
			raise UserError('There is no data to generate')

	def generate_excel(self):
		
		date_from=datetime.strptime(self.from_date,'%Y-%m-%d').strftime("%d/%m/%y")
		date_to=datetime.strptime(self.to_date,'%Y-%m-%d').strftime("%d/%m/%y")
		title="VAT Output Report - "+date_from+" To "+date_to
		data = self.get_vat_output_data(self.from_date,self.to_date,self.company_id.id)
		dataframe= pd.DataFrame(data,columns=["inv_type","inv_no","date","customer","scode","sdes","qty","rate","amount","vat_rate","vat_amount","total_amount","exchange_rate","sar_vat"])
		dataframe.rename(columns={
				 'inv_type': 'Invoice Type',
				 'inv_no' : 'Invoice No',
				 'date': 'Invoice Date',
				 'customer': 'Customer',
				 'scode': 'Service Code',
				 'sdes': 'Service Description',
				 'qty': 'Qty',
				 'rate': 'Rate €',
				 'amount': 'Amount €',
				 'vat_rate': 'VAT Rate %',
				 'vat_amount': 'VAT Amount €',
				 'total_amount': 'Total Amount €',
				 'exchange_rate': 'Exchange Rate € to SAR',
				 'sar_vat': 'VAT Payable in SAR',
				 }, inplace=True)
		header_range ='A1:N1'
		pd.options.display.float_format = '{:,.2f}'.format
		filename ='VAT Output Report.xlsx'
		writer = pd.ExcelWriter(filename, engine='xlsxwriter')
		fp = BytesIO()
		writer.book.filename = fp
		dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
		workbook  = writer.book
		worksheet = writer.sheets['Sheet1']
		title_format = workbook.add_format({
			'bold': True,
			'text_wrap': True,
			'align': 'center',
			'fg_color': '#1E90FF',
			'font_color': 'white',
			'border': 0}) 
		worksheet.merge_range(header_range,title, title_format)
		header_style = workbook.add_format({
											'bold': True,
											'text_wrap': True,
											'align': 'center',
											'fg_color': '#ECF2E9',
											'border':0})
		style_total= workbook.add_format({'border':0,'fg_color': '#ECF2E9','num_format':'#,##0.00','align':'right','bold':True})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'})
		for col_num, value in enumerate(dataframe.columns.values):
			worksheet.write(2, col_num, value, header_style)
			size=len(value)+8
			worksheet.set_column(col_num,col_num,size)
		row=len(dataframe.index)+3
		total_qty=dataframe['Qty'].sum()
		total_rate=dataframe['Rate €'].sum()
		total_amt=dataframe['Amount €'].sum()
		total_vrate=dataframe['VAT Rate %'].sum()
		total_vamt=dataframe['VAT Amount €'].sum()
		total_tamt=dataframe['Total Amount €'].sum()
		total_vsar=dataframe['VAT Payable in SAR'].sum()
		worksheet.merge_range(row,0,row,5,"Total", style_total)		
		worksheet.write(row, 6, total_qty,style_total)
		worksheet.write(row, 7, total_rate,style_total)
		worksheet.write(row, 8, total_amt,style_total)
		worksheet.write(row, 9,"",style_total)
		worksheet.write(row, 10, total_vamt,style_total)
		worksheet.write(row, 11, total_tamt,style_total)
		worksheet.write(row, 12,"",style_total)
		worksheet.write(row, 13, total_vsar,style_total)
		worksheet.set_column('A:A',25)
		worksheet.set_column('B:B', 25)
		worksheet.set_column('C:C', 25)
		worksheet.set_column('D:D', 50)
		worksheet.set_column('E:E', 20)
		worksheet.set_column('F:F', 50)
		worksheet.set_column('G:G', 25, row_num_style)
		worksheet.set_column('H:H', 25, row_num_style)
		worksheet.set_column('I:I', 25, row_num_style)
		worksheet.set_column('J:J', 25, row_num_style)
		worksheet.set_column('K:K', 25, row_num_style)
		worksheet.set_column('L:L', 25, row_num_style)
		worksheet.set_column('M:M', 25, row_num_style)
		worksheet.set_column('N:N', 25, row_num_style)
		writer.save()
		excel_file = base64.encodestring(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()
		return {
			  "view_mode": 'form',
			  'res_model': 'orchid.vat.output.report',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }