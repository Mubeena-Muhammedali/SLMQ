from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd

class OrchidPurchaseRegister(models.TransientModel):
	_name = 'orchid.purchase.register.wiz'
	_description = 'Purchase Register'
	
	
	from_date = fields.Date(string="Start Date",required=True)	
	to_date = fields.Date(string="End Date",required=True)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)
	include_pjr = fields.Boolean(string="PJR/Service Invoices")

	@api.onchange('from_date')
	def last_day_of_month(self):
		if self.from_date:
			any_day=datetime.strptime(self.from_date,'%Y-%m-%d')
			next_month = any_day.replace(day=28) + timedelta(days=4)  # this will never fail
			to_date=next_month - timedelta(days=next_month.day)
			to_date=to_date.strftime('%Y-%m-%d')
			self.to_date=to_date

	def purchase_data(self):
		purchase_data = []
		where_qry=""
		if self.include_pjr:
			where_qry=" AND ai.journal_id= 16"
		else:
			where_qry=" AND ai.journal_id<> 16"
		qry = ('''SELECT 
						 tmpl.default_code,
						 tmpl.name,
						 ru.name,
						 date_part('year',ai.date_invoice),
						 date_part('month',ai.date_invoice),

						 CASE WHEN ((ai.type)::text = 'in_refund'::text) THEN (ail.quantity) * (-1)
						 ELSE (ail.quantity) END,

						 CASE WHEN ((ai.type)::text = 'in_refund'::text) THEN (ail.price_subtotal) * (-1)
						 ELSE (ail.price_subtotal) END,

						 ai.date_invoice,
						 ai.number,
						
						 CASE WHEN ((ai.type)::text = 'in_refund'::text) THEN (ail.price_unit) * (-1)
						 ELSE ail.price_unit END,
						 
						 CASE WHEN ((ai.type)::text = 'in_refund'::text) THEN vend_in.origin
						 ELSE ai.origin END,
						 ai.reference,
						 CASE WHEN ((ai.type)::text = 'in_refund'::text) THEN (ail.price_total-ail.price_subtotal) * (-1)
						 ELSE (ail.price_total-ail.price_subtotal) END,
						 CASE WHEN ((ai.type)::text = 'in_refund'::text) THEN (ail.price_total) * (-1)
						 ELSE (ail.price_total) END
						FROM account_invoice ai
						LEFT JOIN account_invoice_line ail ON ail.invoice_id = ai.id
						LEFT JOIN res_partner res  ON res.id = ai.partner_id
						LEFT JOIN product_product pp ON pp.id = ail.product_id
						LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
						LEFT JOIN res_currency ru ON ru.id = ai.currency_id
						LEFT JOIN account_invoice vend_in ON vend_in.id = ai.refund_invoice_id AND ai.type = 'in_refund'
					  WHERE ai.company_id=%s AND ai.type IN ('in_invoice','in_refund') AND  ai.state IN ('open','paid') AND ai.date_invoice BETWEEN '%s' AND '%s'
					  '''+where_qry+'''
					  GROUP BY
					  	tmpl.default_code,
						tmpl.name,
						ru.name,
						ail.quantity,
						ail.price_unit,
						ai.type,
						vend_in.origin,
						ai.origin,
						ai.date_invoice,
						ai.number,
						ail.price_subtotal,
						ail.id,
						ai.reference

					  ORDER BY ai.date_invoice
			''')%(self.company_id.id,self.from_date,self.to_date)
		self.env.cr.execute(qry)
		data_result = self.env.cr.fetchall()
		if not data_result:
			raise UserError('There is no data to generate')
		for data in data_result:
			date=data[7]
			if date:
				date =datetime.strptime(date,'%Y-%m-%d').strftime('%d-%m-%Y')
			vals ={'Product Code':data[0],
				   'Product Name':data[1],
				   'Local Currency':data[2],
				   'Year':data[3],
				   'Month':data[4],
				   'Quantity':data[5] or 0,
				   'Purchase':data[6] or 0,
				   'Bill Date':date,
				   'Bill Number':data[8],
				   'Unit Price':data[9] or 0,
				   'Purchase Order':data[10],
				   'Vendor Reference':data[11] if data[11]!=None else '',
				   'Purchase Tax':data[12] or 0,
				   'Purchase Total':data[13] or 0,
				   }
			purchase_data.append(vals)
		return purchase_data

	def generate_excel(self):

		result = self.purchase_data()
		if self.include_pjr:
			dataframe= pd.DataFrame(result,columns=["Bill Date","Bill Number","Purchase Order","Vendor Reference","Product Code","Product Name","Local Currency","Year","Month","Quantity","Unit Price","Purchase","Purchase Tax","Purchase Total"])
			dataframe.style.set_properties(subset=["Unit Price","Purchase","Purchase Tax","Purchase Total"], **{'text-align': 'right'})
		else:
			dataframe= pd.DataFrame(result,columns=["Bill Date","Bill Number","Purchase Order","Vendor Reference","Product Code","Product Name","Local Currency","Year","Month","Quantity","Unit Price","Purchase"])
			dataframe.style.set_properties(subset=["Unit Price","Purchase"], **{'text-align': 'right'})
		dataframe.sort_values(by='Bill Date')
		filename ='PurchaseRegister.xlsx'
		from_date =datetime.strptime(self.from_date,'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(self.to_date,'%Y-%m-%d').strftime('%d-%m-%Y')
		title="Purchase Register- "+ from_date + " "+"to " +to_date
		if self.include_pjr:
			header_rage ='A1:N1'
		else:
			header_rage ='A1:L1'

		writer = pd.ExcelWriter(filename, engine='xlsxwriter')
		fp = BytesIO()
		writer.book.filename = fp
		dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
		workbook  = writer.book
		worksheet = writer.sheets['Sheet1']
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
		
		worksheet.merge_range(header_rage,title, title_format)	
		for col_num, value in enumerate(dataframe.columns.values):
			worksheet.write(2, col_num, value, header_style)
			size=len(value)+8
			worksheet.set_column(col_num,col_num,size)
		worksheet.set_column('F:F',40)
		worksheet.set_column('K:K',20,row_num_style)
		worksheet.set_column('L:L',20,row_num_style)
		worksheet.set_column('M:M',20,row_num_style)
		worksheet.set_column('N:N',20,row_num_style)

		row=len(dataframe.index)+3
		col = 0
		worksheet.write(row,col,"Total",tot_format)
		col= col+9
		if self.include_pjr:
			for column in dataframe[['Quantity', 'Unit Price','Purchase','Purchase Tax','Purchase Total']]:
				total=dataframe[column].sum()
				worksheet.write(row,col,total,tot_format1)
				col = col + 1
		else:
			for column in dataframe[['Quantity', 'Unit Price','Purchase']]:
				total=dataframe[column].sum()
				worksheet.write(row,col,total,tot_format1)
				col = col + 1

		writer.save()
		excel_file = base64.encodestring(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'orchid.purchase.register.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.do_nothing',
			  'target': 'new'
			  }

	def generate_view(self):
		
		date_from = self.from_date
		date_to = self.to_date
		domain=[('company_id','=',self.company_id.id),('date_invoice','>=',date_from),('date_invoice','<=',date_to),('invoice_type','in',('in_refund','in_invoice')),('state','in',('open','paid'))]
		action = self.env.ref('orchid_somfy_ksa_v16.action_orchid_purchase_register_tree_view')
		result = action.read()[0]
		result['domain'] = domain
		return result