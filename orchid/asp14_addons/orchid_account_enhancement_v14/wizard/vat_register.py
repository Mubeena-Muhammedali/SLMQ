from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd
import calendar
from datetime import *
from collections import defaultdict

class OrchidTaxRegister(models.TransientModel):
	_name = 'orchid.tax.register'
	_description = 'Tax Register'
	
	
	from_date = fields.Date(string="Start Date",required=True)	
	to_date = fields.Date(string="End Date",required=True)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	# partner_id = fields.Many2one('res.partner', string="Customer/Vendor")
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)
	register_type = fields.Selection([('sale','Sale'),('purchase','Purchase')], string="Register")


	def get_data(self):
		where_qry = " WHERE aml.exclude_from_invoice_tab is false AND am.state='posted' AND am.company_id="+str(self.company_id.id)+\
		" AND am.date>='"+str(self.from_date)+"'"\
		" AND am.date<='"+str(self.to_date)+"'"
		if self.register_type=='purchase':
			where_qry+=" AND am.move_type in ('in_refund','in_invoice')"
		elif self.register_type=='sale':
			where_qry+=" AND am.move_type in ('out_refund','out_invoice')"

		qry= '''SELECT res.name as partner,
				res.vat as trn,
				am.date as invoice_date,
				am.name as invoice_name,
				aml.name as product_desc,
				aml.balance as c_untaxed,
				-- am.amount_tax_signed as c_tax,
				-- am.amount_total_signed as c_total,
				tax.name as tax_name,
				tax.amount as tax_amt,
				cu.name as currency,
				aml.price_subtotal as f_untaxed,
				-- aml.price as f_tax,
				aml.price_total as f_total

				FROM account_move_line aml
				LEFT JOIN account_move am ON am.id= aml.move_id
				LEFT JOIN res_partner res ON res.id = am.partner_id
				LEFT JOIN res_currency cu ON cu.id = am.currency_id
				LEFT JOIN account_move_line_account_tax_rel tax_rel on tax_rel.account_move_line_id = aml.id
				LEFT JOIN account_tax  tax on tax.id = tax_rel.account_tax_id'''+where_qry+'''GROUP BY
					res.name,
					am.date,
					am.name,
					aml.name,
					aml.balance,
					tax.name,
					am.currency_id,
					aml.price_subtotal,
					aml.price_total,
					aml.product_id,
					res.vat,
					cu.name,
					tax.amount,
					aml.id

				'''
		print(qry)
		self._cr.execute(qry)
		results = self._cr.dictfetchall()
		print("resultssss",results)
		fy_flag = False
		data_ls = []
		count = 0
		for data in results:
			fy_flag_data = False
			if data['currency'] != self.company_id.currency_id.name:
				fy_flag = True
				fy_flag_data = True
			count+=1
			c_tax = c_total = f_tax =c_untaxed=0
			c_untaxed = data['c_untaxed']
			if self.register_type=='sale':
				c_untaxed = c_untaxed*(-1)
			if data['tax_name'] and (data['tax_amt']!=0):
				# c_tax = 0.05*abs(data['c_untaxed'])
				c_tax = 0.05*c_untaxed
				c_total =c_tax+c_untaxed
			vals = {
			'sl_no':count,
			'partner':data['partner'],
			'trn':data['trn'],
			'invoice_date':data['invoice_date'],
			'invoice_name':data['invoice_name'],
			'product_desc':data['product_desc'],
			# 'c_untaxed':abs(data['c_untaxed']),
			# 'c_untaxed':data['c_untaxed'],
			'c_untaxed':c_untaxed,
			'c_tax':c_tax,
			'c_total':c_total,
			'f_untaxed':"",
			'f_tax':"",
			'f_total':"",
			'tax_name':data['tax_name'],
			'currency':"",
			}
			if fy_flag_data:
				vals.update({'f_untaxed':data['f_untaxed'],
				'f_tax':data['f_total']-data['f_untaxed'],
				'f_total':data['f_total'],
				'currency':data['currency'],
				})
			data_ls.append(vals)
		if not data_ls:
			raise UserError(_("No Data!!!"))
		return fy_flag,data_ls



	def generate_excel(self):
		fy_flag,data_ls = self.get_data()
		# if not fy_flag:
		header = ['sl_no','partner','trn','invoice_date','invoice_name','product_desc','c_untaxed','c_tax','tax_name']
		# header=['Sr.No','Party\nName','TRN','Invoice\ndate','Date of\nSupply','Invoice\nnumber'
		# 		,'Product\ndescription','Invoice value\nexcluding VAT AED','Value of VAT\nAED','Total\nincluding VAT AED',
		# 		'VAT Type'
		# 		,'Emirates '
		# 		]
		if fy_flag:
			header+=['currency','f_untaxed','f_tax']
			# header+=['FYC\ncode','Value of supply excluding VAT\nin Foreign currency','Value of VAT\nin Foreign currency']# not__included=['Total Value of\nsupplies in AED','Total Value of VAT\nin AED']

		# dataframe.rename(columns = {
		# 	'sl_no':'Sr.No.',
		# 	'invoice_date':'Invoice Date',
		# 	'invoice_name':'Invoice Number',
		# 	'product_desc':'Product Description',
		# 	'c_tax':'Value of VAT AED',
		# 	}, 
		# 	inplace = True)
		# if fy_flag:
		# 	dataframe.rename(columns = {
		# 	'currency':'FCY Code',
		# 	'c_tax':'Value of VAT in Foreign currency',
		# 	}, 
		# 	inplace = True)
		# if self.register_type=='sale':
		# 	dataframe.rename(columns = {
		# 	'partner':'Customer Name',
		# 	'trn':'Customer TRN',
		# 	'c_untaxed':'Value of supply excluding VAT AED',
		# 	'tax_name':'Tax Code wise reporting\n STD-S(Standard Rate @5%)\n ZRO-S(Zero Rated Supply)\n EXM-S(Exempt Supply)\n OS-IG-S(Intra GCC Supply)\n OA(Amendment to Output tax)\n STD-DZ-S(Supply made by the company to a\n customer located in Designated Zone)',
		# 	}, 
		# 	inplace = True)
		# 	if fy_flag:
		# 		dataframe.rename(columns = {
		# 		'f_untaxed':'Value of Supply excluding VAT\nin\n Foreign currency',
		# 		}, 
		# if self.register_type=='purchase':
		# 	dataframe.rename(columns = {
		# 	'partner':'Vendor Name',
		# 	'trn':'Vendor TRN',
		# 	'c_untaxed':'Value of Purchase excluding VAT AED',
		# 	'tax_name':'Tax Code wise reporting\n STD-S(Standard Rate @5%)\n ZRO-S(Zero Rated Supply)\n EXM-S(Exempt Supply)\n OS-IG-S(Intra GCC Supply)\n OA(Amendment to Output tax)\n STD-DZ-S(Supply made by the company to a\n customer located in Designated Zone)',
		# 	}, 
		# 	inplace = True)
		# 	if fy_flag:
		# 		dataframe.rename(columns = {
		# 		'f_untaxed':'Purchase value excluding VAT\nin\n Foreign currency',
		# 		}, 
		# 		inplace = True)
		

		filename ='SalesRegister.xlsx'
		if self.register_type=='purchase':
			filename ='PurchaseRegister.xlsx'
		from_date =datetime.strptime(str(self.from_date),'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(str(self.to_date),'%Y-%m-%d').strftime('%d-%m-%Y')
		# title="Sales Register- "+ from_date + " "+"to " +to_date
		# header_rage ='A1:S1'
		date_range = from_date+"-"+to_date

		writer = pd.ExcelWriter(filename, engine='xlsxwriter')
		fp = BytesIO()
		writer.book.filename = fp
		dataframe= pd.DataFrame(data_ls,columns=header)
		dataframe.rename(columns = {
			'sl_no':'Sr.No.',
			'invoice_date':'Invoice Date',
			'invoice_name':'Invoice Number',
			'product_desc':'Product Description',
			'c_tax':'Value of VAT AED',
			}, 
			inplace = True)
		if fy_flag:
			dataframe.rename(columns = {
			'currency':'FCY Code',
			'c_tax':'Value of VAT in Foreign currency',
			}, 
			inplace = True)
		if self.register_type=='sale':
			dataframe.rename(columns = {
			'partner':'Customer Name',
			'trn':'Customer TRN',
			'c_untaxed':'Value of supply excluding VAT AED',
			'tax_name':'Tax Code wise reporting\n STD-S(Standard Rate @5%)\n ZRO-S(Zero Rated Supply)\n EXM-S(Exempt Supply)\n OS-IG-S(Intra GCC Supply)\n OA(Amendment to Output tax)\n STD-DZ-S(Supply made by the company to a\n customer located in Designated Zone)',
			}, 
			inplace = True)
			if fy_flag:
				dataframe.rename(columns = {
				'f_untaxed':'Value of Supply excluding VAT\nin\n Foreign currency',
				}, inplace = True)
		if self.register_type=='purchase':
			dataframe.rename(columns = {
			'partner':'Vendor Name',
			'trn':'Vendor TRN',
			'c_untaxed':'Value of Purchase excluding VAT AED',
			'tax_name':'Tax Code wise reporting\n STD-S(Standard Rate @5%)\n ZRO-S(Zero Rated Supply)\n EXM-S(Exempt Supply)\n OS-IG-S(Intra GCC Supply)\n OA(Amendment to Output tax)\n STD-DZ-S(Supply made by the company to a\n customer located in Designated Zone)',
			}, 
			inplace = True)
			if fy_flag:
				dataframe.rename(columns = {
				'f_untaxed':'Purchase value excluding VAT\nin\n Foreign currency',
				}, 
				inplace = True)
		dataframe.to_excel(writer, sheet_name='Sheet1',startrow=14,index=False,header=True)
		# dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)

		workbook  = writer.book
		worksheet = writer.sheets['Sheet1']
		title_format = workbook.add_format({
			'bold': True,
			# 'align': 'center',
			'fg_color': '#c9211e',
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
		
		# worksheet.merge_range(header_rage,title, title_format)
		row=3
		row_merge=row
		col=0
		col_merge=col+2
		head=defaultdict(list)
		head['add'].append(self.company_id.street or "")
		head['add'].append(self.company_id.street2 or "")
		head['add'].append(self.company_id.state_id.name or "")
		head['add'].append(self.company_id.zip or "")
		head['add'].append(self.company_id.country_id.name or "")
		head['vat'].append(self.company_id.vat or "")
		adress=self.company_id.street or ""
		adress+=self.company_id.street2 or ""
		adress+=self.company_id.state_id.name or ""
		adress+=self.company_id.zip or ""
		adress+=self.company_id.country_id.name or ""
		# adress+=self.company_id.vat or ""
		title=['Name of the Company','Address of the Company','TRN of the Company','VAT Return Period']
		for detail in title:
			print("tittttt",detail)
			worksheet.merge_range(row,col,row,col_merge,detail,title_format)
			print("nnnnn",row,row_merge)
			# row_merge = row+1
			row = row+1
			# worksheet.merge_range(row,col,row_merge,col_merge,'Address of the Company',title_format)
			# row = row_merge+1
			# worksheet.merge_range(row,col,row_merge,col_merge,'TRN of the Company',title_format)
			# row = row_merge+1
			# worksheet.merge_range(row,col,row_merge,col_merge,'VAT Return Period',title_format)
		row=3
		col =col_merge+1
		col_merge = col+2
		worksheet.merge_range(row,col,row,col_merge,self.company_id.name,title_format)
		# worksheet.write(row,col,self.company_id.name,title_format)
		row = row+1
		print("hhhdddd",head,head['add'])
		worksheet.merge_range(row,col,row,col_merge,adress,title_format)
		# worksheet.write(row,col,adress,title_format)
		row = row+1
		worksheet.merge_range(row,col,row,col_merge,self.company_id.vat,title_format)
		# worksheet.write(row,col,self.company_id.vat,title_format)
		row = row+1
		worksheet.merge_range(row,col,row,col_merge,date_range,title_format)
		# worksheet.write(row,col,date_range,title_format)
		worksheet.set_column('A:A',5)
		worksheet.set_column('B:B',40)
		worksheet.set_column('C:E',20)
		worksheet.set_column('F:F',40)
		worksheet.set_column('G:I',20)
		worksheet.set_column('J:L',20)
		
		writer.save()
		excel_file = base64.encodestring(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'orchid.tax.register',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }







