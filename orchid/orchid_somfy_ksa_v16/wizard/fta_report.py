from odoo import api, fields, models, _
from datetime import datetime, timedelta
from collections import OrderedDict
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd
import calendar

class OrchidFTAReport(models.TransientModel):
	_name = 'orchid.fta.report.wiz'
	_description = 'FTA Declaration Report'
	
	
	from_date = fields.Date(string="Start Date",required=True)	
	to_date = fields.Date(string="End Date",required=True)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	exchange_rate_id = fields.Many2one('orchid.budget.rate',string="Excange Rate", check_company=True)
	reverse_rate_id = fields.Many2one('orchid.budget.rate',string="Reverse Excange Rate", check_company=True)
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)

	@api.model
	def default_get(self, fields):
		res = super(OrchidFTAReport, self).default_get(fields)
		exchange_rate_id = self.env['orchid.budget.rate'].search([('from_currency_id','=',1),('to_currency_id','=',154)], order="id asc", limit=1)
		r_from_currenncy_id = exchange_rate_id.to_currency_id.id
		r_to_currenncy_id = exchange_rate_id.from_currency_id.id
		r_exchange_rate_id = self.env['orchid.budget.rate'].search([('from_currency_id','=',r_from_currenncy_id),('to_currency_id','=',r_to_currenncy_id)], order="id asc", limit=1)
		values = {
			'exchange_rate_id':exchange_rate_id.id,
			# 'reverse_rate_id':r_exchange_rate_id.id,
		}
		res.update(values)
		return res

	@api.onchange('from_date')
	def last_day_of_month(self):
		if self.from_date:
			any_day=datetime.strptime(str(self.from_date),'%Y-%m-%d')
			next_month = any_day.replace(day=28) + timedelta(days=4)  # this will never fail
			to_date=next_month - timedelta(days=next_month.day)
			to_date=to_date.strftime('%Y-%m-%d')
			self.to_date=to_date

	def detail_fta_data(self):
		detail_data = []
		qry = ('''
				SELECT 
					ai.id,
					ai.date_invoice,
					TO_CHAR(ai.date_invoice, 'Month'),
					extract(year from ai.date_invoice),
					ai.number,
					ai.od_transaction_type,
					res.od_ban_bp,
					res.name,
					res.city,
					sw.name,
					rc.name,
					tc.tax_category

				FROM account_invoice ai
				LEFT JOIN res_partner res  ON res.id = ai.partner_id
				LEFT JOIN stock_warehouse sw  ON sw.id = ai.od_warehouse_id
				LEFT JOIN res_country rc  ON rc.id = res.country_id
				LEFT JOIN orchid_tax_category_master tc  ON tc.warehouse_id = ai.od_warehouse_id AND tc.country_id = res.country_id
			    WHERE ai.company_id=%s AND ai.date_invoice BETWEEN '%s' AND '%s' AND ai.state IN ('open','paid') AND ai.type IN ('out_invoice','out_refund')
			    GROUP BY
			    	ai.id,
					ai.date_invoice,
					ai.number,
					ai.od_transaction_type,
					res.od_ban_bp,
					res.name,
					res.city,
					sw.name,
					rc.name,
					tc.tax_category
			    ORDER BY  ai.name,ai.date_invoice''')%(self.company_id.id, self.from_date,self.to_date)
		self.env.cr.execute(qry)
		data_result = self.env.cr.fetchall()
		if not data_result:
			raise UserError('There is no data to generate')
		count=0
		for data in data_result:
				count=count+1
				invoice_id = self.env['account.invoice'].browse(data[0])
				net_amt=charges_in_euro=tax_amt=0
				r_exchange_rate= self.reverse_rate_id.rate if self.reverse_rate_id	else (1/self.exchange_rate_id.rate)
				tax_amt= invoice_id.amount_tax*r_exchange_rate if invoice_id.currency_id.id!=1 else invoice_id.amount_tax
				for line in invoice_id.invoice_line_ids: 
					if line.product_id.type!='service':
						if invoice_id.currency_id.id!=1:	
							net_amt=net_amt+(line.price_subtotal*r_exchange_rate)
						else:
							net_amt=net_amt+(line.price_subtotal)
					else:
						if invoice_id.currency_id.id!=1:
							# r_exchange_rate= self.reverse_rate_id.rate if self.reverse_rate_id	else (1/self.exchange_rate_id.rate)
							charges_in_euro=charges_in_euro+(line.price_subtotal*r_exchange_rate)
						else:
							charges_in_euro=charges_in_euro+line.price_subtotal 
				gross_amt = net_amt+charges_in_euro
				euro_total=gross_amt+tax_amt
				aed_total=euro_total*self.exchange_rate_id.rate	
				vat_aed=tax_amt*self.exchange_rate_id.rate	
				category=""
				if data[11]=='emirate':
					category="Tax to Declare By Emirate"
				if data[11]=='export':
					category="Exports"
				if data[11]=='out_of_scope':
					category="Out of Scope"
				vals ={
					   'Sl No.':str(count),
					   'Date':datetime.strptime(data[1],'%Y-%m-%d').strftime('%d-%m-%Y') if data[1] else "",
					   'Month':str(data[2])+str(int(data[3])),
					   'Voucher No.':data[4],
					   'Transaction Type':data[5],
					   'Branch':'Saudi Arabia',
					   'Currency':'Euro',
					   'Exchange Rate':1,
					   'Party Alias' : data[6],
					   'Party' : data[7],
					   'Gross Amount':gross_amt,
					   'Net Amount':net_amt,
					   'Charges in Euro':charges_in_euro,
					   'Deducions in Euro':0,
					   'Taxable Other Charges Amount':tax_amt,
					   'Total Value in Euro':euro_total,
					   'Exchange Rate FC':self.exchange_rate_id.rate,
					   'Total Value in SAR':aed_total,
					   'VAT':vat_aed,
					   'City':data[8],
					   'Delivery From':data[9],
					   'Country':data[10],
					   'Tax Category':category,
					   }
				detail_data.append(vals)
		return detail_data


	def generate_excel(self):
		if not self.exchange_rate_id:
			raise UserError('Please define a Budget rate in the Budget master')

		filename ='FTADeclarationReport.xlsx'
		from_date =datetime.strptime(self.from_date,'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(self.to_date,'%Y-%m-%d').strftime('%d-%m-%Y')
		title="FTA Declaration Report- "+ from_date + " "+"to " +to_date
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

		result = self.detail_fta_data()
		header_rage ='A1:W1'
		dataframe= pd.DataFrame(result,columns=["Sl No.","Date","Month","Voucher No.","Transaction Type","Branch","Currency","Exchange Rate","Party Alias","Party",
		"Net Amount","Charges in Euro","Gross Amount","Deducions in Euro","Taxable Other Charges Amount","Total Value in Euro","Exchange Rate FC","Total Value in SAR","VAT","City","Delivery From","Country","Tax Category"])
		dataframe.style.set_properties(subset=["Exchange Rate","Net Amount","Charges in Euro","Gross Amount","Deducions in Euro","Taxable Other Charges Amount","Total Value in Euro","Exchange Rate FC","Total Value in SAR","VAT"], **{'text-align': 'right'})
		dataframe.sort_values(by='Voucher No.')
		dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
		worksheet = writer.sheets['Sheet1']
		worksheet.set_column('B:B',20)
		worksheet.set_column('C:C',20)
		worksheet.set_column('D:D',40)
		worksheet.set_column('E:E',30)
		worksheet.set_column('G:G',20)
		worksheet.set_column('H:H',20)
		worksheet.set_column('I:I',30)
		worksheet.set_column('J:J',50)
		worksheet.set_column('K:K',20,row_num_style)
		worksheet.set_column('L:L',30,row_num_style)
		worksheet.set_column('M:M',30,row_num_style)
		worksheet.set_column('N:N',30,row_num_style)
		worksheet.set_column('O:O',30,row_num_style)
		worksheet.set_column('P:P',30,row_num_style)
		worksheet.set_column('Q:Q',30,row_num_style)
		worksheet.set_column('R:R',30,row_num_style)
		worksheet.set_column('S:S',20,row_num_style)
		worksheet.set_column('T:T',30)
		worksheet.set_column('U:U',30)
		worksheet.set_column('V:V',30)
		worksheet.set_column('W:W',30)
		
		worksheet.merge_range(header_rage,title, title_format)	
		for col_num, value in enumerate(dataframe.columns.values):
			worksheet.write(2, col_num, value, header_style)
		row=len(dataframe.index)+3
		col = 0
		worksheet.write(row,col,"Total",tot_format)
		col= col+10
		total_ls=["Net Amount","Charges in Euro","Gross Amount","Deducions in Euro","Taxable Other Charges Amount","Total Value in Euro","Exchange Rate FC","Total Value in SAR","VAT"]
		for column in dataframe[total_ls]:
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
			  'res_model': 'orchid.fta.report.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }


	# def generate_view(self):

	# 	date_from = self.from_date
	# 	date_to = self.to_date
	# 	domain=[('date_invoice','>=',date_from),('date_invoice','<=',date_to)]
	# 	current_month = datetime.strptime(self.from_date,'%Y-%m-%d').strftime('%m')
	# 	action = self.env.ref('orchid_somfy_ksa_v16.action_orchid_fta_report_tree_view')
	# 	result = action.read()[0]
	# 	result['domain'] = domain
	# 	print("dommmmmmmm",domain)
	# 	print("dommmmmmmm",result)
	# 	return result
		