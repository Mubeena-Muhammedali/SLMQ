from odoo import api, fields, models, _
from datetime import datetime, timedelta
from collections import OrderedDict
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd
import calendar

class OrchidCreditInsuranceReport(models.TransientModel):
	_name = 'orchid.credit.insurance.report.wiz'
	_description = 'Credit Insurance Declaration Report'
	
	
	from_date = fields.Date(string="Start Date",required=True)	
	to_date = fields.Date(string="End Date",required=True)
	coverage_type =fields.Selection([('named','Named Coverage'),('un_named','Unnamed Coverage')],string='Credit Insurance Coverage Type')
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	credit_note = fields.Boolean(string="With Credit Note")
	# summary = fields.Boolean(string="Summary")
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)


	@api.onchange('from_date')
	def last_day_of_month(self):
		if self.from_date:
			any_day=datetime.strptime(self.from_date,'%Y-%m-%d')
			next_month = any_day.replace(day=28) + timedelta(days=4)  # this will never fail
			to_date=next_month - timedelta(days=next_month.day)
			to_date=to_date.strftime('%Y-%m-%d')
			self.to_date=to_date

	def detail_coverage_data(self):
		detail_data = []
		where_qry = " ai.type = 'out_invoice' AND  ai.state IN ('open','paid')"
		if self.credit_note:
			where_qry = " ai.type IN ('out_invoice','out_refund') AND  ai.state IN ('open','paid') "
		if self.coverage_type:
			where_qry = where_qry + " AND res.od_name_unamed="+"'"+str(self.coverage_type)+"'"
		qry = ('''
				SELECT 
					res.id,
					ai.date_invoice,
					-- ai.number,
					res.name,
					COALESCE(res.od_insured_credit_limit,0),
					res.od_name_unamed,
					-- COALESCE(res.od_coverage_value,0),
					CASE WHEN ai.type ='out_invoice'
					THEN ai.amount_total
					ELSE ai.amount_total*(-1) END
				FROM account_invoice ai
				LEFT JOIN res_partner res  ON res.id = ai.partner_id
			    WHERE ai.company_id=%s AND ai.date_invoice BETWEEN '%s' AND '%s' AND ''' + where_qry +'''
			    GROUP BY
			    	res.id,
				  	ai.date_invoice,
					res.name,
					res.od_insured_credit_limit,
					res.od_name_unamed,
					ai.amount_total,
					ai.type
			    ORDER BY  ai.date_invoice''')%(self.company_id.id, self.from_date,self.to_date)
		self.env.cr.execute(qry)
		data_result = self.env.cr.fetchall()
		if not data_result:
			raise UserError('There is no data to generate')
		partners =list(set([z[0] for z in data_result]))
		inv_data=[]
		date1 = str(self.from_date)  # input start date
		date2 = str(self.to_date)  # input end date
		month_list = [i.strftime("%b-%y") for i in pd.date_range(start=date1, end=date2, freq='MS')]
		for partner in partners:
			grand_total=0
			p_dict={}
			partner_id = self.env['res.partner'].search([('id','=',partner)])
			if partner_id.property_payment_term_id.id != 28:
				p_dict[partner]={}
				for m in month_list:
					month_sum=0
					for data in data_result:
						date=data[1]
						if date:
							date =datetime.strptime(data[1],'%Y-%m-%d').strftime('%b-%y')
						if data[0]==partner:
							if m==date:
								month_sum=month_sum+data[5]
								p_dict[partner][m]=month_sum or 0,
								p_dict[partner]['Customer']=data[2],
								p_dict[partner]['Credit Limit']=data[3] or 0,
								p_dict[partner]['Credit Insurance Company']='Named Coverage' if data[4]=='named' else 'Unnamed Coverage',
								p_dict[partner]['City']=partner_id.city or '',
								p_dict[partner]['Country']=partner_id.country_id and partner_id.country_id.name  or '',
								p_dict[partner]['Terms of Payment']=partner_id.property_payment_term_id and partner_id.property_payment_term_id.note  or '',
					grand_total=grand_total+month_sum
					p_dict[partner]['Grand Total']=grand_total
				inv_data.append(p_dict)
		
		for data in inv_data:
			for value in data.values():
				value['Customer']=value['Customer'][0]
				value['Credit Limit']=value['Credit Limit'][0]
				value['City']=value['City'][0]
				value['Country']=value['Country'][0]
				value['Terms of Payment']=value['Terms of Payment'][0]
				value['Credit Insurance Company']=value['Credit Insurance Company'][0]
				for m in month_list:
					if m in value.keys():
						value[m]=value[m][0]
				detail_data.append(value)
		return detail_data

	# def named_coverage_data_summary(self):
	# 	named_summary_data = []
		
	# 	qry = ('''
	# 			SELECT 
	# 				res.id as res,
	# 				res.name as customer,
	# 				COALESCE(res.od_insured_credit_limit,0) as credit_limit,
	# 				res.od_name_unamed as c_type,
	# 				COALESCE(res.od_coverage_value,0) as c_value,
	# 				sum(ai.amount_total) as amt
	# 			FROM account_invoice ai
	# 			LEFT JOIN res_partner res  ON res.id = ai.partner_id
	# 		    WHERE ai.date_invoice BETWEEN '%s' AND '%s' 
	# 		    AND ai.type = 'out_invoice' AND  ai.state IN ('open','paid') AND res.od_name_unamed='named'
	# 		    GROUP BY
	# 		    	res.id,
	# 				res.name,
	# 				res.od_insured_credit_limit,
	# 				res.od_name_unamed,
	# 				res.od_coverage_value
	# 		    ORDER BY  res.name''')%(self.from_date,self.to_date)

	# 	self.env.cr.execute(qry)
	# 	out_data_result = self.env.cr.dictfetchall()
	# 	refund_data_result = []
	# 	if self.credit_note:
	# 		r_qry = ('''
	# 				SELECT 
	# 					res.id as res,
	# 					res.name as customer,
	# 					COALESCE(res.od_insured_credit_limit,0) as credit_limit,
	# 					COALESCE(res.od_coverage_value,0) as c_value,
	# 					sum(ai.amount_total) as amt
	# 				FROM account_invoice ai
	# 				LEFT JOIN res_partner res  ON res.id = ai.partner_id
	# 			    WHERE ai.date_invoice BETWEEN '%s' AND '%s' 
	# 			    AND ai.type = 'out_refund' AND  ai.state IN ('open','paid') AND res.od_name_unamed='named'
	# 			    GROUP BY
	# 			    	res.id,
	# 					res.name,
	# 					res.od_insured_credit_limit,
	# 					res.od_name_unamed,
	# 					res.od_coverage_value
	# 			    ORDER BY  res.name''')%(self.from_date,self.to_date)
	# 		self.env.cr.execute(r_qry)
	# 		refund_data_result = self.env.cr.dictfetchall()


	# 	if (not out_data_result) and (not refund_data_result):
	# 		raise UserError('There is no data to generate')
	# 	for data in out_data_result:
	# 		data['inv_amt'] = data['amt']
	# 		for d in refund_data_result:
	# 			if data['customer']==d['customer']:
	# 				inv_amt = data['amt']-d['amt']
	# 				data['inv_amt'] = inv_amt
	# 				i = refund_data_result.index(d)
	# 				del refund_data_result[i]

	# 	for data in out_data_result:
	# 		partner_id = self.env['res.partner'].search([('id','=',data['res'])])
	# 		if partner_id.property_payment_term_id.id != 28: 
	# 			vals ={'Customer':data['customer'],
	# 				   'Credit Limit':data['credit_limit'] or 0,
	# 				   'Credit Insurance Coverage Type':'Named Coverage',
	# 				   'Credit Insurance Coverage Value':data['c_value'] or 0,
	# 				   'Invoice Value  to be extracted':data['inv_amt'],
	# 				   }
	# 			named_summary_data.append(vals)

	# 	for data in refund_data_result:
	# 		partner_id = self.env['res.partner'].search([('id','=',data['res'])])
	# 		if partner_id.property_payment_term_id.id != 28: 
	# 			vals ={'Customer':data['customer'],
	# 				   'Credit Limit':data['credit_limit'] or 0,
	# 				   'Credit Insurance Coverage Type':'Named Coverage',
	# 				   'Credit Insurance Coverage Value':data['c_value'] or 0,
	# 				   'Invoice Value  to be extracted':data['amt']*(-1),
	# 				   }
	# 			named_summary_data.append(vals)

	# 	return named_summary_data

	# def unnamed_coverage_data_summary(self):
	# 	unnamed_summary_data = []
	# 	qry = ('''
	# 			SELECT 
	# 				res.id as res,
	# 				rc.name as country,
	# 				COALESCE(res.od_insured_credit_limit,0) as credit_limit,
	# 				COALESCE(res.od_coverage_value,0) as c_value,
	# 				sum(ai.amount_total) as amt
	# 			FROM account_invoice ai
	# 			LEFT JOIN res_partner res  ON res.id = ai.partner_id
	# 			LEFT JOIN res_country rc  ON rc.id = res.country_id
	# 		    WHERE ai.date_invoice BETWEEN '%s' AND '%s' 
	# 		    AND ai.type = 'out_invoice' AND  ai.state IN ('open','paid') AND res.od_name_unamed='un_named'
	# 		    GROUP BY
	# 		    	res.id,
	# 				rc.name,
	# 				res.od_insured_credit_limit,
	# 				res.od_name_unamed,
	# 				res.od_coverage_value
	# 		    ORDER BY  rc.name''')%(self.from_date,self.to_date)

	# 	self.env.cr.execute(qry)
	# 	out_data_result = self.env.cr.dictfetchall()
	# 	refund_data_result = []
	# 	if self.credit_note:
	# 		r_qry = ('''
	# 				SELECT 
	# 					res.id as res,
	# 					rc.name as country,
	# 					COALESCE(res.od_insured_credit_limit,0) as credit_limit,
	# 					COALESCE(res.od_coverage_value,0) as c_value,
	# 					sum(ai.amount_total) as amt
	# 				FROM account_invoice ai
	# 				LEFT JOIN res_partner res  ON res.id = ai.partner_id
	# 				LEFT JOIN res_country rc  ON rc.id = res.country_id
	# 			    WHERE ai.date_invoice BETWEEN '%s' AND '%s'  
	# 			    AND ai.type = 'out_refund' AND ai.state IN ('open','paid') AND res.od_name_unamed='un_named'
	# 			    GROUP BY
	# 			    	res.id,
	# 					rc.name,
	# 					res.od_insured_credit_limit,
	# 					res.od_name_unamed,
	# 					res.od_coverage_value
	# 			    ORDER BY  rc.name''')%(self.from_date,self.to_date)
	# 		self.env.cr.execute(r_qry)
	# 		refund_data_result = self.env.cr.dictfetchall()


	# 	if (not out_data_result) and (not refund_data_result):
	# 		raise UserError('There is no data to generate')
	# 	country_ls = []
	# 	unnamed_summary_out_data = []
	# 	unnamed_summary_refund_data = []
	# 	for data in out_data_result:
	# 		country_ls.append(data['country'])
	# 	for data in refund_data_result:
	# 		country_ls.append(data['country'])
	# 	country_ls = list(set(country_ls))

	# 	for  country in country_ls:
	# 		t_credit_limit=t_c_value=t_inv_amt=0
	# 		for data in out_data_result:
	# 			partner_id = self.env['res.partner'].search([('id','=',data['res'])])
	# 			if partner_id.property_payment_term_id.id != 28:
	# 					if data['country'] == country:
	# 						t_credit_limit = t_credit_limit+data['credit_limit']
	# 						t_c_value = t_c_value+data['c_value']
	# 						t_inv_amt = t_inv_amt+data['amt']
	# 		vals ={'Country':country,
	# 			   'Credit Limit':t_credit_limit or 0,
	# 			   'Credit Insurance Coverage Type':'Unnamed Coverage',
	# 			   'Credit Insurance Coverage Value':t_c_value or 0,
	# 			   'Invoice Value  to be extracted':t_inv_amt,
	# 			   }
	# 		unnamed_summary_out_data.append(vals)

	# 	for  country in country_ls:
	# 		t_credit_limit=t_c_value=t_inv_amt=0
	# 		for data in refund_data_result:
	# 			partner_id = self.env['res.partner'].search([('id','=',data['res'])])
	# 			if partner_id.property_payment_term_id.id != 28:
	# 					if data['country'] == country:
	# 						t_credit_limit = t_credit_limit+data['credit_limit']
	# 						t_c_value = t_c_value+data['c_value']
	# 						t_inv_amt = t_inv_amt+data['amt']
	# 		vals ={'Country':country,
	# 			   'Credit Limit':t_credit_limit or 0,
	# 			   'Credit Insurance Coverage Type':'Unnamed Coverage',
	# 			   'Credit Insurance Coverage Value':t_c_value or 0,
	# 			   'Invoice Value  to be extracted':t_inv_amt,
	# 			   }
	# 		unnamed_summary_refund_data.append(vals)

	# 	for data in unnamed_summary_out_data:
	# 		data['Invoice Value  to be extracted'] = data['Invoice Value  to be extracted']
	# 		for d in unnamed_summary_refund_data:
	# 			if data['Country']==d['Country']:
	# 				inv_amt = data['Invoice Value  to be extracted']-d['Invoice Value  to be extracted']
	# 				data['Invoice Value  to be extracted'] = inv_amt
	# 				i = unnamed_summary_refund_data.index(d)
	# 				del unnamed_summary_refund_data[i]

	# 	for data in unnamed_summary_out_data:
	# 		unnamed_summary_data.append(data)
	# 	for data in unnamed_summary_refund_data:
	# 		data['Invoice Value  to be extracted']=data['Invoice Value  to be extracted']*(-1)
	# 		unnamed_summary_data.append(data)

	# 	return unnamed_summary_data

	def generate_excel(self):

		filename ='CreditInsuranceDeclarationReport.xlsx'
		from_date =datetime.strptime(self.from_date,'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(self.to_date,'%Y-%m-%d').strftime('%d-%m-%Y')
		title="Credit Insurance Declaration Report- "+ from_date + " "+"to " +to_date
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

		# if not self.summary:
		result = self.detail_coverage_data()
		header_rage ='A1:G1'
		date1 = str(self.from_date)  # input start date
		date2 = str(self.to_date)  # input end date
		month_list = [i.strftime("%b-%y") for i in pd.date_range(start=date1, end=date2, freq='MS')]
		header=["Customer","City","Country","Terms of Payment","Credit Insurance Company","Credit Limit"]
		num_header=["Credit Limit"]
		for m in month_list:
			header.append(m)
			num_header.append(m)
		total="Grand Total"
		header.append(total)
		num_header.append(total)
		dataframe= pd.DataFrame(result,columns=header)
		dataframe=dataframe.dropna(axis=1,how='all')
		dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
		worksheet = writer.sheets['Sheet1']
		worksheet.set_column('A:A',50)
		worksheet.set_column('B:B',30)
		worksheet.set_column('C:C',30)
		worksheet.set_column('D:D',50)
		worksheet.set_column('E:E',25)
		worksheet.set_column('F:F',30)
		worksheet.set_column('G:G',30,row_num_style)
		# worksheet.set_column('H:H',30,row_num_style)
		# worksheet.set_column('H:H',30,row_num_style)
		# if self.summary and self.coverage_type=='named':
		# 	result = self.named_coverage_data_summary()
		# 	header_rage ='A1:E1'
		# 	dataframe= pd.DataFrame(result,columns=["Customer","Credit Insurance Coverage Type","Credit Limit","Credit Insurance Coverage Value","Invoice Value  to be extracted"])
		# 	dataframe.style.set_properties(subset=["Credit Limit","Credit Insurance Coverage Value","Invoice Value  to be extracted"], **{'text-align': 'right'})
		# 	dataframe.sort_values(by='Customer')
		# 	dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
		# 	worksheet = writer.sheets['Sheet1']
		# 	worksheet.set_column('A:A',50)
		# 	worksheet.set_column('B:B',40)
		# 	worksheet.set_column('C:C',20,row_num_style)
		# 	worksheet.set_column('D:D',40,row_num_style)
		# 	worksheet.set_column('E:E',40,row_num_style)

		# if self.summary and self.coverage_type=='un_named':
		# 	result = self.unnamed_coverage_data_summary()
		# 	header_rage ='A1:E1'
		# 	dataframe= pd.DataFrame(result,columns=["Country","Credit Insurance Coverage Type","Credit Limit","Credit Insurance Coverage Value","Invoice Value  to be extracted"])
		# 	dataframe.style.set_properties(subset=["Credit Limit","Credit Insurance Coverage Value","Invoice Value  to be extracted"], **{'text-align': 'right'})
		# 	dataframe.sort_values(by='Country')
		# 	dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
		# 	worksheet = writer.sheets['Sheet1']
		# 	worksheet.set_column('A:A',50)
		# 	worksheet.set_column('B:B',40)
		# 	worksheet.set_column('C:C',20,row_num_style)
		# 	worksheet.set_column('D:D',40,row_num_style)
		# 	worksheet.set_column('E:E',40,row_num_style)
		
		worksheet.merge_range(header_rage,title, title_format)	
		for col_num, value in enumerate(dataframe.columns.values):
			worksheet.write(2, col_num, value, header_style)
		row=len(dataframe.index)+3
		col = 0
		worksheet.write(row,col,"Total",tot_format)
		# if not self.summary:
		col= col+5
		# if self.summary:
		# 	col= col+2
		# total_ls=['Credit Limit', 'Credit Insurance Coverage Value','Invoice Value  to be extracted']
		total_ls=num_header
		worksheet.merge_range(0,0,0,len(dataframe.columns)-1,title, title_format)
		for t_col in total_ls:
			for column in dataframe.columns:
				if t_col ==column:
					total=dataframe[column].sum()
					worksheet.set_column(col,col,30,row_num_style)
					worksheet.write(row,col,total,tot_format1)
					col = col + 1


		writer.save()
		excel_file = base64.encodestring(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'orchid.credit.insurance.report.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }

