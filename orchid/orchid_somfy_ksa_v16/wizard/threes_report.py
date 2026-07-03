from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd

class OrchidThreeSReport(models.TransientModel):
	
	_name = 'orchid.threes.report.wiz'
	_description = '3S Report'
	
	
	from_date = fields.Date(string="Start Date",required=True)	
	to_date = fields.Date(string="End Date",required=True)
	service_product = fields.Boolean(string="Service Products only",default=False)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	report_xl = fields.Selection([('product','Product Report'),('customer','Customer Report'),('invoice','Invoice Report')],string="Report",default='product')
	od_csv = fields.Boolean(string="CSV")
	factory_price = fields.Boolean(string="Factory Price")
	show_in_euro =  fields.Boolean(string="Show in Euro")
	# exchange_rate_id = fields.Many2one('orchid.budget.rate',string="Excange Rate", check_company=True)
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)

	
	# @api.model
	# def default_get(self, fields):
	# 	res = super(OrchidThreeSReport, self).default_get(fields)
	# 	exchange_rate_id = self.env['orchid.budget.rate'].search([('from_currency_id','=',154),('to_currency_id','=',1)], order="id asc", limit=1)
	# 	values = {
	# 		'exchange_rate_id':exchange_rate_id.id,
	# 	}
	# 	res.update(values)
	# 	return res
	
	@api.onchange('from_date')
	def last_day_of_month(self):
		if self.from_date:
			any_day=datetime.strptime(str(self.from_date),'%Y-%m-%d')
			next_month = any_day.replace(day=28) + timedelta(days=4)  # this will never fail
			to_date=next_month - timedelta(days=next_month.day)
			to_date=to_date.strftime('%Y-%m-%d')
			self.to_date=to_date
	
	
	def product_data(self,current_month):
		prd_data = []
		# qry = ('''SELECT tmpl.default_code,tmpl.description FROM account_move_line ail
		# 				LEFT JOIN product_product pp ON pp.id = ail.product_id
		# 				LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
		# 				LEFT JOIN account_move ai ON ai.id = ail.invoice_id
		# 			  WHERE ai.move_type='out_invoice' AND ai.state!='draft' AND date_part('month',ai.invoice_date) = %s AND
		# 			  pp.id NOT IN ( SELECT pp.id FROM account_move_line ail
		# 								LEFT JOIN product_product pp ON pp.id = ail.product_id
		# 								LEFT JOIN account_move ai ON ai.id = ail.invoice_id
		# 								WHERE ai.move_type='out_invoice' AND ai.state!='draft' AND date_part('month',ai.invoice_date) = %s ) 
		# 			  GROUP BY pp.id,tmpl.default_code,tmpl.description
		# 	''')%(current_month,prev_month)
		where_qry = " ai.move_type IN ('out_invoice','out_refund') AND  ai.state IN ('posted') "
		if not self.service_product:
			where_qry = where_qry + " AND tmpl.type <> 'service' "
		if self.service_product:
			where_qry = where_qry + " AND tmpl.type = 'service' "

		qry = ('''SELECT tmpl.default_code,tmpl.description 
				  FROM account_move_line ail
					LEFT JOIN product_product pp ON pp.id = ail.product_id
					LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
					LEFT JOIN account_move ai ON ai.id = ail.move_id
				  WHERE ai.company_id=%s AND ai.invoice_date BETWEEN '%s' AND '%s' 
				  AND pp.id NOT IN (SELECT pp.id FROM account_move_line ail
									LEFT JOIN product_product pp ON pp.id = ail.product_id
									LEFT JOIN account_move ai ON ai.id = ail.move_id
									WHERE ail.display_type='product' AND ai.company_id=%s AND date_part('month',ai.invoice_date) < %s AND ai.move_type IN ('out_invoice','out_refund') AND  ai.state IN ('posted') AND pp.id is NOT NULL)
				  AND ail.display_type='product' AND ''' + where_qry + '''
				  GROUP BY pp.id,tmpl.default_code,tmpl.description
			''')%(self.company_id.id, self.from_date,self.to_date,self.company_id.id,current_month)
		print(qry)
		self.env.cr.execute(qry)
		data_result = self.env.cr.fetchall()
		# print("ddddddddd",data_result)
		if not data_result:
			raise UserError('There is no data to generate')
		for data in data_result:
			vals ={'Product Code':data[0],
				   'Product Description':data[1],
				   }
			prd_data.append(vals)
		return prd_data

	def customer_data(self,current_month):
		cust_data = []

		# qry = ('''SELECT res.ref,res.od_ban_bp,res.name,lb.code,rc.code,dc.code FROM account_move ai
		# 				LEFT JOIN res_partner res  ON res.id = ai.partner_id
		# 				LEFT JOIN res_country rc ON rc.id = res.country_id
		# 				LEFT JOIN orchid_line_of_business lb ON lb.id = res.od_lne_buss_id
		# 				LEFT JOIN orchid_distribution_channel dc ON dc.id = res.od_distr_chanel_id
		# 			  WHERE ai.move_type='out_invoice' AND ai.state!='draft' AND date_part('month',ai.invoice_date) = %s AND
		# 			  res.id NOT IN ( SELECT res.id FROM account_move ai
		# 								LEFT JOIN res_partner res  ON res.id = ai.partner_id
		# 								WHERE ai.move_type='out_invoice' AND ai.state!='draft' AND date_part('month',ai.invoice_date) = %s )
		# 			  GROUP BY res.id,res.od_ban_bp,res.name,lb.code,rc.code,dc.code

		# 	''')%(current_month,prev_month)
		qry = ('''SELECT res.ref,res.od_ban_bp,res.name,lb.code,rc.code,dc.code FROM account_move ai
						LEFT JOIN res_partner res  ON res.id = ai.partner_id
						LEFT JOIN res_country rc ON rc.id = res.country_id
						LEFT JOIN orchid_line_of_business lb ON lb.id = res.od_lne_buss_id
						LEFT JOIN orchid_distribution_channel dc ON dc.id = res.od_distr_chanel_id
					  WHERE  ai.company_id=%s AND ai.move_type IN ('out_invoice','out_refund') AND ai.state IN ('posted') AND ai.invoice_date BETWEEN '%s' AND '%s' 
					  AND res.id NOT IN(SELECT res.id FROM account_move ai
										LEFT JOIN res_partner res  ON res.id = ai.partner_id
										WHERE ai.company_id=%s AND date_part('month',ai.invoice_date) < %s AND ai.move_type IN ('out_invoice','out_refund') AND ai.state IN ('posted'))
					  GROUP BY res.id,res.od_ban_bp,res.name,lb.code,rc.code,dc.code
			''')%(self.company_id.id, self.from_date,self.to_date,self.company_id.id,current_month)
		self.env.cr.execute(qry)
		data_result = self.env.cr.fetchall()
		if not data_result:
			raise UserError('There is no data to generate')
		for data in data_result:
			vals ={'Customer Reference':data[0],
				   'Customer Code':data[1],
				   'Customer Name':data[2],
				   'Line of Business':data[3],
				   'Country Code':data[4],
				   'Distribution Channel':data[5],
				   }
			cust_data.append(vals)
		return cust_data

	def invoice_data(self):
		inv_data = []
		where_qry = " ai.move_type IN ('out_invoice','out_refund') AND  ai.state IN ('posted') AND ai.od_expert_prgm_inv is not true "
		# if self.stock_product:
		# 	where_qry = where_qry + " AND tmpl.type <> 'service' "
		exempt_pdts_ls = [self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin').id,self.env.ref('orchid_somfy_ksa_v16.od_product_local_transportation').id,self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id]
		if not self.service_product:
			where_qry = where_qry + " AND ail.product_id NOT IN " + str(tuple(exempt_pdts_ls))
		if self.service_product:
			where_qry = where_qry + " AND tmpl.type = 'service' "

		select_str = '''SELECT res.ref as ref,
						 res.od_ban_bp as od_ban_bp,
						 tmpl.default_code as default_code,
						 ru.name as currency,
						 date_part('year',ai.invoice_date) as year,
						 date_part('month',ai.invoice_date) as month,

						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) * (-1)
						 ELSE (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END as quantity,
						 
						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.price_subtotal) * (-1)
						 ELSE (ail.price_subtotal) END as subtotal,
						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.debit) * (-1)
						 ELSE (ail.credit) END as sale_sar,

						 -- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (cst.cost * (ail.quantity + ail.od_free_qty)) * (-1)
						 -- ELSE (cst.cost * (ail.quantity + ail.od_free_qty)) END
						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (cst.amount_currency_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty)) * (-1)
						 ELSE (cst.amount_currency_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty)) END as cost,

						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (cst.cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty)) * (-1)
						 ELSE (cst.cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty)) END as cost_sar,

						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN tmpl.od_factory_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) * (-1)
						 ELSE tmpl.od_factory_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END as factory_cost,
						 ru.id as currency_id,
						 ai.od_exchange_rate as exch_rate,
						 ai.name as invoice,
						 ai.invoice_date as inv_date'''

		left_join_str = '''LEFT JOIN account_move_line ail ON ail.move_id = ai.id
						LEFT JOIN res_partner res  ON res.id = ai.partner_id
						LEFT JOIN product_product pp ON pp.id = ail.product_id
						LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
						LEFT JOIN res_currency ru ON ru.id = ai.currency_id
						'''

		dropshipping_left_join = left_join_str + "\n LEFT JOIN orchid_account_invoice_dropshipping_cost cst ON ail.move_id = cst.inv_id and ail.product_id = cst.product_id "
		normalshipping_left_join = left_join_str + "\n LEFT JOIN orchid_account_invoice_cost cst ON ail.move_id = cst.inv_id and ail.product_id = cst.product_id "
		
		group_by_str = '''
						res.ref,
						res.od_ban_bp,
						tmpl.default_code,
						ru.name,
						ai.invoice_date,
						ai.move_type,
						ail.id,
						ail.quantity,
						ail.od_free_qty,
						ail.od_adjustment_qty,
						cst.amount_currency_cost,
						ail.id,
						tmpl.od_factory_cost,
						ru.id,
						ai.od_exchange_rate,
						ail.debit,
						ail.credit,
						cst.cost,
						ai.name '''

		qry1 = ("""%s FROM account_move ai
					%s
				  WHERE (ail.display_type='product') AND ai.company_id=%s AND ai.invoice_date BETWEEN '%s' AND '%s' AND (ai.od_cos_entry_id is null) AND """ + where_qry +"""
				  GROUP BY %s """)%(select_str,normalshipping_left_join,self.company_id.id,self.from_date,self.to_date,group_by_str)

		print("qryyy111",qry1)
		print("-----------------------------------------------------------------------------------------------------")

		qry2 = ("""%s FROM account_move ai
					%s
				  WHERE (ail.display_type='product') AND ai.company_id=%s AND ai.invoice_date BETWEEN '%s' AND '%s' AND (ai.od_cos_entry_id is not null) AND """ + where_qry +"""
				  GROUP BY %s """)%(select_str,dropshipping_left_join,self.company_id.id,self.from_date,self.to_date,group_by_str)
		foo_str = '''SELECT foo.ref as ref,
						 foo.od_ban_bp as od_ban_bp,
						 foo.default_code as default_code,
						 foo.currency as currency,
						 foo.year as year,
						 foo.month as month,
						 foo.quantity as quantity,
						 SUM(foo.subtotal) as subtotal,
						 SUM(foo.sale_sar) as sale_sar,
						 foo.cost as cost,
						 SUM(foo.cost_sar) as cost_sar,
						 foo.factory_cost as factory_cost,
						 foo.currency_id as currency_id,
						 foo.exch_rate as exch_rate,
						 foo.invoice,
						 foo.inv_date'''

		foo_group_by = '''
						foo.ref,
						foo.od_ban_bp,
						foo.default_code,
						foo.currency,
						foo.month,
						foo.year,
						foo.quantity,
						foo.cost,
						foo.factory_cost,
						foo.currency_id,
						foo.exch_rate,
						foo.invoice,
						foo.inv_date'''

		qry = ('''%s FROM(%s
			  UNION
			  %s
			  ) as foo
			  GROUP BY %s''')%(foo_str,qry1,qry2,foo_group_by)


		print(qry)
		print("-----------------------------------------------------------------------------------------------------")


		# qry = ('''SELECT res.ref,
		# 				 res.od_ban_bp,
		# 				 tmpl.default_code,
		# 				 ru.name,
		# 				 date_part('year',ai.invoice_date),
		# 				 date_part('month',ai.invoice_date),

		# 				 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) * (-1)
		# 				 ELSE (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END,
						 
		# 				 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.price_subtotal) * (-1)
		# 				 ELSE (ail.price_subtotal) END,

		# 				 -- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (cst.cost * (ail.quantity + ail.od_free_qty)) * (-1)
		# 				 -- ELSE (cst.cost * (ail.quantity + ail.od_free_qty)) END
		# 				 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (cst.amount_currency_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty)) * (-1)
		# 				 ELSE (cst.amount_currency_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty)) END,

		# 				 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN tmpl.od_factory_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) * (-1)
		# 				 ELSE tmpl.od_factory_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END,
		# 				 ru.id

		# 				FROM account_move ai
		# 				LEFT JOIN account_move_line ail ON ail.move_id = ai.id
		# 				LEFT JOIN res_partner res  ON res.id = ai.partner_id
		# 				LEFT JOIN product_product pp ON pp.id = ail.product_id
		# 				LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
		# 				LEFT JOIN res_currency ru ON ru.id = ai.currency_id
		# 				LEFT JOIN orchid_account_move_cost cst ON ail.move_id = cst.inv_id 
		# 					and ail.product_id = cst.product_id 
		# 			  WHERE ail.display_type='product' AND ai.company_id=%s AND ai.invoice_date BETWEEN '%s' AND '%s' AND ''' +where_qry+'''
		# 			  GROUP BY
		# 				res.ref,
		# 				res.od_ban_bp,
		# 				tmpl.default_code,
		# 				ru.name,
		# 				ai.invoicqry2e_date,
		# 				ai.move_type,
		# 				ail.id,
		# 				ail.quantity,
		# 				ail.od_free_qty,
		# 				ail.od_adjustment_qty,
		# 				cst.amount_currency_cost,
		# 				ail.id,
		# 				tmpl.od_factory_cost,
		# 				ru.id
		# 			  ORDER BY ai.invoice_date, ail.id
		# 	''')%(self.company_id.id, self.from_date,self.to_date)
		self.env.cr.execute(qry)
		data_result = self.env.cr.dictfetchall()
		print("jjjj",data_result)
		if not data_result:
			raise UserError('There is no data to generate')
		for data in data_result:
			print("dataaaaa",data)
			sales=data['subtotal'] or 0
			cos=data['cost'] or 0
			factory_price=data['factory_cost'] or 0
			# find the euro to sar rate to calculate the factory cost in sar
			rate_id = self.env['res.currency.rate'].search([
				('company_id', '=', self.company_id.id),
				('currency_id', '=', 1),
				('name', '=', data.get('inv_date')),
			], limit=1)
			if rate_id:
				factory_price = factory_price*rate_id.inverse_company_rate
			sales_company = data['sale_sar']
			cos_company = data['cost_sar']
			if data['currency_id']!=1:
				sales=0
				cos=0
			# if data[10]!=1 and self.show_in_euro:
			# 	sales=sales*self.exchange_rate_id.rate
			# 	cos=cos*self.exchange_rate_id.rate
			# 	factory_price=factory_price*self.exchange_rate_id.rate

			vals ={
				   'Customer Reference':data['ref'],
				   'Customer Code':data['od_ban_bp'],
				   'Product Code':data['default_code'],
				   'Local Currency' : data['currency'],
				   'Year':data['year'],
				   'Month':data['month'],
				   'Quantity':data['quantity'] or 0,
				   'Sales':sales,
				   'COS':cos,
				   'Exchange Rate':data['exch_rate'],
				   'Sales SAR':sales_company or 0,
				   'COS SAR':cos_company or 0,
				   'Factory Price':factory_price,
				   }
			inv_data.append(vals)
		return inv_data


	def generate_excel(self):

		current_month = datetime.strptime(str(self.from_date),'%Y-%m-%d').strftime('%m')
		# prev_month = int(current_month) - 1
		from_date =datetime.strptime(str(self.from_date),'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(str(self.to_date),'%Y-%m-%d').strftime('%d-%m-%Y')

		if self.report_xl == 'product':
			result = self.product_data(current_month)
			dataframe= pd.DataFrame(result,columns=["Product Code","Product Description"])
			# pd.options.display.float_format = '{:,.2f}'.format
			dataframe.sort_values(by='Product Code')
			filename ='3S Products.xlsx'
			csv_filename ='3S_Products.csv'
			title="3S Products - "+ from_date + " "+"to " +to_date
			header_rage ='A1:B1'
		if self.report_xl == 'customer':
			result = self.customer_data(current_month)
			dataframe= pd.DataFrame(result,columns=["Customer Reference","Customer Code","Customer Name","Line of Business","Distribution Channel","Country Code"])
			# pd.options.display.float_format = '{:,.2f}'.format
			dataframe.sort_values(by='Customer Code')
			filename ='3S Customers.xlsx'
			csv_filename ='3S_Customers.csv'
			title="3S Customers - "+ from_date + " "+"to " +to_date
			header_rage ='A1:F1'

		if self.report_xl == 'invoice':
			# if not self.exchange_rate_id and self.show_in_euro:
			# 	raise UserError('Please define a Budget rate for SAR to EURO in the Budget master')
			result = self.invoice_data()
			if self.factory_price:
				header_rage ='A1:L1'
				# dataframe= pd.DataFrame(result,columns=["Customer Reference","Customer Code","Product Code","Local Currency","Year","Month","Quantity","Sales","COS","Exchange Rate","Sales SAR","COS SAR","Factory Price"])
				dataframe= pd.DataFrame(result,columns=["Customer Code","Product Code","Local Currency","Year","Month","Quantity","Sales","COS","Exchange Rate","Sales SAR","COS SAR","Factory Price"])
				dataframe.style.set_properties(subset=["Sales", "COS", "Factory Price"], **{'text-align': 'right'})
			else:
				header_rage ='A1:K1'
				# dataframe= pd.DataFrame(result,columns=["Customer Reference","Customer Code","Product Code","Local Currency","Year","Month","Quantity","Sales","COS","Exchange Rate","Sales SAR","COS SAR"])
				dataframe= pd.DataFrame(result,columns=["Customer Code","Product Code","Local Currency","Year","Month","Quantity","Sales","COS","Exchange Rate","Sales SAR","COS SAR"])
				dataframe.style.set_properties(subset=["Sales", "COS","Exchange Rate","Sales SAR","COS SAR"], **{'text-align': 'right'})
			dataframe.sort_values(by='Customer Code')
			filename ='3S Sales.xlsx'
			csv_filename ='3S_Sales.csv'
			title="3S Sales - "+ from_date + " "+"to " +to_date
			

		writer = pd.ExcelWriter(filename, engine='xlsxwriter')
		fp = BytesIO()
		writer.book.filename = fp
		if self.od_csv:
			dataframe.to_csv(csv_filename, index = False, header=True)
			csv_data=dataframe.to_csv(csv_filename, encoding='utf-8')
		else:
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
			worksheet.set_column('A:A',30)
			worksheet.set_column('B:B',30)
			worksheet.set_column('C:C',30)
			worksheet.set_column('H:H',30,row_num_style)
			worksheet.set_column('I:I',30,row_num_style)
			worksheet.set_column('J:J',30,row_num_style)
			worksheet.set_column('K:K',30,row_num_style)
			worksheet.set_column('L:L',30,row_num_style)
			worksheet.set_column('M:M',30,row_num_style)
			
			if self. report_xl == 'invoice':
				row=len(dataframe.index)+3
				col = 0
				worksheet.write(row,col,"Total",tot_format)
				col= col+5
				df_total = dataframe[['Quantity','Sales','COS','Exchange Rate','Sales SAR','COS SAR']]
				if self.factory_price:
					df_total=dataframe[['Quantity','Sales','COS','Exchange Rate','Sales SAR','COS SAR','Factory Price']]
				# for column in dataframe[['Quantity','Sales','COS']]:
				for column in df_total:
					total=dataframe[column].sum()
					worksheet.write(row,col,total,tot_format1)
					if column =='Exchange Rate':
						exch_tot = ""
						worksheet.write(row,col,exch_tot,tot_format1)
					col = col + 1

			writer.close()
			excel_file = base64.encodebytes(fp.getvalue())
			self.write({'excel_file':excel_file,'file_name':filename})
			fp.close()
			return {
				  'view_type': 'form',
				  "view_mode": 'form',
				  'res_model': 'orchid.threes.report.wiz',
				  'res_id': self.id,
				  'type': 'ir.actions.act_window',
				  'target': 'new'
				  }
	
	def generate_view(self):

		date_from = self.from_date
		date_to = self.to_date
		domain=[('company_id','=',self.company_id.id),('date_invoice','>=',date_from),('date_invoice','<=',date_to),('invoice_type','in',('out_refund','out_invoice')),('state','in', ('open','paid'))]
		current_month = datetime.strptime(str(self.from_date),'%Y-%m-%d').strftime('%m')
		
		if self.stock_product and self.report_xl != 'customer':
			prd_domain = ('product_type','!=','service')
			domain.append(prd_domain)
		if self.report_xl == 'product':
			previous_product =('''SELECT pp.id FROM account_move_line ail
								  LEFT JOIN product_product pp ON pp.id = ail.product_id
								  LEFT JOIN account_move ai ON ai.id = ail.move_id
								  WHERE ail.display_type='product' AND ai.company_id=%s AND date_part('month',ai.invoice_date) < %s AND ai.move_type IN ('out_invoice','out_refund') AND  ai.state IN ('posted') AND pp.id IS NOT NULL''')%(self.company_id.id, current_month)
			self._cr.execute(previous_product)
			result_prd=self._cr.fetchall()
			if result_prd:
				result_prd = [z[0] for z in result_prd]
				pid_domain = ('id','not in',tuple(result_prd))
				domain.append(pid_domain)
			action = self.env.ref('orchid_somfy_ksa_v16.action_orchid_3s_products_tree_view')
			result = action.read()[0]
			result['domain'] = domain
			# print("dommmmmmmm",domain)
			# print("dommmmmmmm",result)
			return result
		if self.report_xl == 'customer':
			previous_cust =('''SELECT res.id FROM account_move ai
							   LEFT JOIN res_partner res  ON res.id = ai.partner_id
							   WHERE ai.company_id=%s AND date_part('month',ai.invoice_date) < %s AND ai.move_type IN ('out_invoice','out_refund') AND ai.state IN ('posted')''')%(self.company_id.id, current_month)
			self._cr.execute(previous_cust)
			result_cust=self._cr.fetchall()
			if result_cust:
				result_cust = [z[0] for z in result_cust]
				cid_domain = ('id','not in',tuple(result_cust))
				domain.append(cid_domain)
			action = self.env.ref('orchid_somfy_ksa_v16.action_orchid_3s_customers_tree_view')
			result = action.read()[0]
			result['domain'] = domain
			return result
		if self.report_xl == 'invoice':
			if self.show_in_euro:
				action = self.env.ref('orchid_somfy_ksa_v16.action_orchid_3s_sales_euro_tree_view')
			else:
				action = self.env.ref('orchid_somfy_ksa_v16.action_orchid_3s_sales_tree_view')
			result = action.read()[0]
			result['domain'] = domain
			return result