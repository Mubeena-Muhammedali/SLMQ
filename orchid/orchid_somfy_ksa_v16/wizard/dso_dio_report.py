from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd
import calendar
from dateutil.relativedelta import relativedelta
import xlsxwriter

class OrchidDsoWiz(models.TransientModel):
	_name = 'od.dso.wiz'
	_description = 'DSO/DIO Report'

	month = fields.Selection([('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
                          ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'), 
                          ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'), ], 
                          string='Month')
	year = fields.Selection([(str(num),num) for num in range(2000,(datetime.now().year)+50)])

	user_id = fields.Many2one('res.users', string="Salesman", check_company=True)
	report_type = fields.Selection([('DSO','DSO'),('DIO','DIO')], string="Report")
	excel_file = fields.Binary(string='Excel Report',readonly=True)
	file_name = fields.Char(string='Excel File',readonly=True)
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)

	date_from = fields.Date(string="Date From")
	date_to = fields.Date(string="Date To")

	@api.onchange('month','year')
	def get_dates(self):
		for wiz in self:
			if wiz.month and wiz.year:
				string_date_to = str(wiz.year)+'-'+str(wiz.month)
				date_to =  datetime.strptime(string_date_to+"-01", "%Y-%m-%d")
				date_to = date_to.date()
				last_day = calendar.monthrange(date_to.year, date_to.month)[1]
				date_to = date_to.replace(day=last_day)
				date_from = date_to - relativedelta(months=11)
				date_from = date_from.replace(day=1)
				# if self.report_type=='DSO':
				# 	date_from = date_to.replace(day=1,month=1)
				wiz.date_from = date_from
				wiz.date_to = date_to
			else:
				wiz.date_from = False
				wiz.date_to = False
			# print("wwwww",wiz.date_to,wiz.date_from)

	def generate_excel_dso(self):
		date_from =datetime.strptime(str(self.date_from),'%Y-%m-%d').strftime('%d-%m-%Y')
		date_to =datetime.strptime(str(self.date_to),'%Y-%m-%d').strftime('%d-%m-%Y')
		report_name = str(self.report_type)+"Report"
		title=report_name+" - "+ date_from + " "+"to " +date_to
		filename =str(report_name)+'.xlsx'
		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		sheet= workbook.add_worksheet(str(report_name))
		style_main_header=workbook.add_format({'bold':True,'font_size':15,'align':'center','valign':'vcenter','bg_color':'#D7E4BC','border':0})
		style_sub_header=workbook.add_format({'bold':True,'bg_color':'#cccccc','border':0})
		style_balance=workbook.add_format({'bold':False,'num_format':'#,##0.00'})
		style_balance1=workbook.add_format({'bold':False,'align':'right'})
		style_total=workbook.add_format({'bold':True,'num_format':'#,##0.00','bg_color':'#cccccc'})
		style_total_text=workbook.add_format({'bold':True})
		style_total_text1=workbook.add_format({'bold':True,'bg_color':'#b7b3ca'})
		style_total1=workbook.add_format({'bold':True,'num_format':'#,##0.00'})
		style_total2=workbook.add_format({'bold':False,'align':'right','bg_color':'#cccccc'})
		style_total3=workbook.add_format({'bold':False,'align':'right','bg_color':'#cccccc'})
		sheet.set_column('A:A',30)
		row = 0
		col =0
		if self.report_type=='DSO':
			print("DSO********************************************8")
			users_dict = {}
			ls_index = 0
			user_domain=[]
			user_ids=False
			if self.user_id:
				sale_domain = ('id','=',self.user_id.id)
				# user_domain.append(sale_domain)
				user_ids = self.env['res.users'].browse(self.user_id.id)
			else:
				# salesman_domain = ['|',('active','=',False),('active','=',True)]
				# user_domain.append(salesman_domain)
				# user_ids = self.env['res.users'].search(['|',('active','=',False),('active','=',True)])
				user_ids = self.env['res.users'].search([])

			# user_ids = self.env['res.users'].search(user_domain)
			# user_ids = self.env['res.users'].browse(89)
			# print("userrrr",user_ids)
			if user_ids:
				for user_id in user_ids.sorted('id'):
					ls_index+=1
					users_dict[user_id.id]=ls_index
			col_merge=13
			row_merge=row
			sheet.merge_range(row,col,row,col_merge,title,style_main_header)
			row=row+2
			
			# month_ls =['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
			month_ls=[]
			month_date = self.date_from
			# print("month_datemonth_date",month_date)
			while (month_date<=self.date_to):
				month=""
				month=month_date.strftime("%B")+" "+str(month_date.year)
				month_ls.append(month)
				# print("kkkkkk",month,month_date,month_ls)
				month_date=month_date+relativedelta(months=1)
				# print("oppiiiii",month_date)
			col=1
			for month in month_ls:
				sheet.set_column(row,col,15)
				sheet.write(row,col,month,style_sub_header)
				col = col+1
			sheet.write(row,col,"Total",style_sub_header)
			sheet.set_column(row,col,15)
			row = row+1
			for user_id in user_ids:
				row_total = 0
				col=0
				sale_row=0
				collection_row=0
				receivables_row=0
				aging_row=0
				sale_sum=0
				collection_sum=0
				receivables_sum=0
				aging_sum=0
				col_merge = col+13
				sheet.merge_range(row,col,row,col_merge,user_id.name,style_total_text1)
				row=row+1
				sale_row = row
				sheet.write(row,col,"Sales")
				row=row+1
				collection_row = row
				sheet.write(row,col,"OPRC")
				row=row+1
				receivables_row = row
				sheet.write(row,col,"Receivables")
				row=row+1
				aging_row = row
				sheet.write(row,col,"Aging Days")
				row=row+1

				# i=int(self.month)
				# print("iiiiii",i)
				i=12
				collection = 0
				receivables = 0
				month_date = self.date_to.replace(day=1)
				while(i>=1):
					collection = 0
					end_col=i 
					sale_date_from = month_date
					last_day = calendar.monthrange(sale_date_from.year, sale_date_from.month)[1]
					sale_date_to = sale_date_from.replace(day=last_day)
					# print("sssssss",sale_date_from,sale_date_to)
					# print("reeeeeee",collection,receivables)

					sales_qry = """SELECT COALESCE(sum(mv.amount_total_in_currency_signed),0)
									FROM account_move mv
									WHERE mv.invoice_user_id=%s AND mv.company_id=%s 
									AND mv.invoice_date>='%s' AND mv.invoice_date<='%s' AND mv.state='posted' AND mv.move_type in ('out_invoice','out_refund') """%(user_id.id, self.company_id.id,sale_date_from,sale_date_to)
					# print("salessss",sales_qry)
					self._cr.execute(sales_qry)
					sales_result = self._cr.fetchall()
					sales_result = [sale[0] for sale in sales_result]
					sales = 0
					if sales_result:
						sales =sales_result[0]
					# print("hhhhh",sales_qry)

					if i==12:
						# print("iiiiionccc",i)
						receivables_qry = """SELECT COALESCE(sum(aml.amount_currency),0)
										FROM account_move_line aml
										LEFT JOIN account_move mv ON mv.id=aml.move_id
										LEFT JOIN account_account aa ON aa.id = aml.account_id
										LEFT JOIN res_partner res ON res.id=aml.partner_id
										WHERE aa.account_type='asset_receivable' AND mv.invoice_user_id=%s AND mv.company_id=%s 
										AND aml.date<='%s' AND mv.state='posted'"""%(user_id.id, self.company_id.id,sale_date_to)
						self._cr.execute(receivables_qry)
						receivables_result = self._cr.fetchall()
						receivables_result = [r[0] for r in receivables_result]
						# receivables = 0
						if receivables_result:
							receivables =receivables_result[0]

					# collection = 0
					collection = receivables - sales

					aging = 0
					amount = (receivables/(sales if sales else 1))*30
					if collection>0:
						aging=30
					elif amount < 0:
						aging=0
					else:
						aging = amount

					sale_sum += sales
					collection_sum += collection
					receivables_sum += receivables
					aging_sum += aging

					sheet.write(sale_row,end_col,sales, style_balance)
					sheet.write(collection_row,end_col,collection, style_balance)
					sheet.write(receivables_row,end_col,receivables, style_balance)
					sheet.write(aging_row,end_col,aging, style_balance)
					receivables=collection
					i=i-1
					month_date=month_date+relativedelta(months=-1)
				tot_col = end_col+12
				sheet.write(sale_row,tot_col,sale_sum,style_total1)
				sheet.write(collection_row,tot_col,collection_sum,style_total1)
				sheet.write(receivables_row,tot_col,receivables_sum,style_total1)
				sheet.write(aging_row,tot_col,aging_sum,style_total1)

				previous_receivables = 0
				previous_to_date = self.date_from - relativedelta(days=1)
				# print("pppp",previous_to_date)
				previous_receivables_qry = """SELECT COALESCE(sum(aml.amount_currency),0)
										FROM account_move_line aml
										LEFT JOIN account_move mv ON mv.id=aml.move_id
										LEFT JOIN account_account aa ON aa.id = aml.account_id
										LEFT JOIN res_partner res ON res.id=aml.partner_id
										WHERE aa.account_type='asset_receivable' AND mv.invoice_user_id=%s AND mv.company_id=%s 
										AND aml.date<='%s' AND mv.state='posted' """%(user_id.id, self.company_id.id,previous_to_date)
				self._cr.execute(previous_receivables_qry)
				previous_receivables_result = self._cr.fetchall()
				previous_receivables_result = [r[0] for r in previous_receivables_result]
				previous_receivables = 0
				if previous_receivables_result:
					previous_receivables =previous_receivables_result[0]
				# print("kooo",previous_receivables_qry)
				col = 0
				col_merge = end_col
				row = aging_row+1
				sheet.merge_range(row,col,row,col_merge,"Debtors Turn Over Ratio",style_total_text)
				col=tot_col
				current_receivables = receivables #receivables of december
				current_sales = sale_sum or 1 #total sales of the year
				ratio = ((previous_receivables+current_receivables)/2)/current_sales*365
				sheet.write(row,col,ratio,style_total1)
				col = 0
				row=row+1
				sheet.merge_range(row,col,row,col_merge,"Days of Sales Outstanding",style_total_text)
				col=tot_col
				sheet.write(row,col,aging_sum,style_total1)
				row=row+1

		if self.report_type=='DIO':
			print("DIO********************************************8")
			account_dict = {}
			ls_index = 0
			col_merge=12
			row_merge=row
			sheet.merge_range(row,col,row,col_merge,title,style_main_header)
			row=row+2
			sheet.set_column(row,col,50)
			sheet.write(row,col,"Particulars",style_sub_header)
			# month_ls =['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
			month_ls=[]
			month_date = self.date_from
			# print("month_datemonth_date",month_date)
			while (month_date<=self.date_to):
				month=""
				month=month_date.strftime("%B")+" "+str(month_date.year)
				month_ls.append(month)
				# print("kkkkkk",month,month_date,month_ls)
				month_date=month_date+relativedelta(months=1)
				# print("oppiiiii",month_date)
			col=1
			for month in month_ls:
				sheet.set_column(row,col,15)
				sheet.write(row,col,month,style_sub_header)
				col = col+1
			row = row+1
			cogs_account_ids = []
			stock_in_account_ids = []
			cogs_account_id_param = self.sudo().env.ref('orchid_somfy_ksa_v16.od_dio_report_cogs')
			cogs_account_ids_str = cogs_account_id_param.value
			stock_in_account_id_param = self.sudo().env.ref('orchid_somfy_ksa_v16.od_dio_report_stock')
			stock_in_account_ids_str = stock_in_account_id_param.value
			# print("cogs_account_ids",cogs_account_ids_str,stock_in_account_ids_str)
			if (not cogs_account_ids_str) or (cogs_account_ids_str=='[]'):
				raise UserError(_("No value set for the param 'COGS Account ids list' !!"))
			if (not stock_in_account_ids_str) or (stock_in_account_ids_str=='[]'):
				raise UserError(_("No value set for the param 'Stock Account ids list' !!"))
			cogs_account_ids_str = cogs_account_ids_str[1:-1]
			stock_in_account_ids_str = stock_in_account_ids_str[1:-1]
			# print("strrrrrrsss",cogs_account_ids_str,stock_in_account_ids_str)
			cogs_account_ids_ls =  cogs_account_ids_str.split(", ")
			stock_in_account_ids_ls =  stock_in_account_ids_str.split(", ")
			# print("tttt",cogs_account_ids_ls, type(cogs_account_ids_ls))
			strc_num=''
			length_cogs = len(cogs_account_ids_ls[0])
			for c in cogs_account_ids_ls[0]:
				length_cogs-=1
				if c==',':
					cogs_account_ids.append(int(strc_num))
					strc_num = ''
				elif (length_cogs==0):
					strc_num+=c
					cogs_account_ids.append(int(strc_num))
					strc_num = ''
				else:
					strc_num+=c

			str_num=''
			length = len(stock_in_account_ids_ls[0])
			for s in stock_in_account_ids_ls[0]:
				# print("ssssss",s,type(s))
				length-=1
				# print("length",length)
				if (s==','):
					stock_in_account_ids.append(int(str_num))
					str_num = ''
				elif (length==0):
					str_num+=s
					stock_in_account_ids.append(int(str_num))
					str_num = ''
				else:
					str_num+=s

			# print("accountsss",cogs_account_ids,stock_in_account_ids)

			row_total = 0
			col=0
			stock_row=0
			cogs_row=0
			cogs_rollback_row=0
			dio_row=0
			stock_row = row
			sheet.write(row,col,"Stock Value at month end(include transit) as per HFM")
			row=row+1
			cogs_row = row
			sheet.write(row,col,"Total COGS as per HFM (KSA) each month")
			row=row+1
			cogs_rollback_row = row
			sheet.write(row,col,"Roll Back 12 Months COGS")
			row=row+1
			dio_row = row
			sheet.write(row,col,"DIO", style_total_text)
			row=row+1
			# range_limit = int(self.month)+1
			range_limit = 13
			# for i in range (1,13):
			from_date = self.date_from
			for i in range (1,range_limit):
				end_col=i 
				# stock_date_from = self.date_from.replace(month=i)
				stock_date_from = from_date
				last_day = calendar.monthrange(stock_date_from.year, stock_date_from.month)[1]
				stock_date_to = stock_date_from.replace(day=last_day)
				# print("sssssss",stock_date_from,stock_date_to)

				stock_qry = """SELECT COALESCE(sum(mvl.balance),0)
								FROM account_move_line mvl
								LEFT JOIN account_move am ON am.id=mvl.move_id
								WHERE mvl.company_id=%s 
								AND mvl.date<='%s' AND am.state='posted' AND mvl.account_id in %s """%(self.company_id.id,stock_date_to, tuple(stock_in_account_ids))
				self._cr.execute(stock_qry)
				stock_result = self._cr.fetchall()
				stock_result = [s[0] for s in stock_result]
				stock = 0
				if stock_result:
					stock =stock_result[0]
				# print("stttt",stock_qry)

				cogs_qry = """SELECT COALESCE(sum(mvl.balance),0)
								FROM account_move_line mvl
								LEFT JOIN account_move am ON am.id=mvl.move_id
								WHERE mvl.company_id=%s 
								AND mvl.date>='%s' AND mvl.date<='%s' AND am.state='posted' AND mvl.account_id in %s  """%(self.company_id.id,stock_date_from,stock_date_to, tuple(cogs_account_ids))
				# print("jjjjjjjjjjjj",cogs_qry)
				self._cr.execute(cogs_qry)
				cogs_result = self._cr.fetchall()
				cogs_result = [r[0] for r in cogs_result]
				cogs = 0
				if cogs_result:
					cogs =cogs_result[0]

				date_from_rollback = stock_date_from - relativedelta(months=11)
				# print("date_from_rollback",date_from_rollback,stock_date_from,stock_date_to)

				cogs_rollback_qry = """SELECT COALESCE(sum(mvl.balance),0)
								FROM account_move_line mvl
								LEFT JOIN account_move am ON am.id=mvl.move_id
								WHERE mvl.company_id=%s 
								AND mvl.date>='%s' AND mvl.date<='%s' AND am.state='posted' AND mvl.account_id in %s  """%(self.company_id.id,date_from_rollback,stock_date_to, tuple(cogs_account_ids))
				self._cr.execute(cogs_rollback_qry)
				cogs_rollback_result = self._cr.fetchall()
				cogs_rollback_result = [c[0] for c in cogs_rollback_result]
				cogs_rollback = 0
				if cogs_rollback_result:
					cogs_rollback =cogs_rollback_result[0]
				# print("rolll",cogs_rollback_qry)

				
				dio = 0
				# print("possss",stock,cogs_rollback,cogs)
				dio = (stock/(cogs_rollback if cogs_rollback else 1))*360
				

				sheet.write(stock_row,end_col,stock, style_balance)
				sheet.write(cogs_row,end_col,cogs, style_balance)
				sheet.write(cogs_rollback_row,end_col,cogs_rollback, style_balance)
				sheet.write(dio_row,end_col,dio, style_balance)
				# print("sttttt",stock_date_from,stock_date_to,date_from_rollback,i)
				from_date = from_date+relativedelta(months=1)




		workbook.close()
		output.seek(0)
		# excel_file = base64.encodestring(output.read())
		excel_file = base64.encodebytes(output.read())
		self.write({'excel_file':excel_file,'file_name':filename})
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.dso.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }

