# -*- coding: utf-8 -*-
from odoo import fields, models,api,_
from odoo.exceptions import UserError
# import xlwt
import xlsxwriter
from io import BytesIO
import base64
from collections import defaultdict
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import time
from itertools import groupby

class OrchidAccountPLReport(models.TransientModel):

	_name = 'od.account.pl.report.wiz'
	description = 'P&L Report'

	from_date = fields.Date(string="Start Date",required=True)	
	to_date = fields.Date(string="End Date",required=True)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)
	report_options = fields.Selection([('pl','P&L Report'),('marketing','Marketing Report')], string="Report", default='pl')
	cost_center_ids = fields.Many2many('orchid.account.cost.center', string="Cost Center")
	cost_center = fields.Boolean(string="Cost Center Wise", default=False)
	analysis = fields.Boolean(string="P&L Analysis", default=False)

	@api.onchange('report_options', 'cost_center')
	def onchange_analysis(self):
		for wiz in self:
			if wiz.report_options!='pl':
				wiz.analysis=False
			if wiz.cost_center:
				wiz.analysis=False
	@api.model
	def default_get(self, fields):
		res = super(OrchidAccountPLReport, self).default_get(fields)
		cost_center_ids = self.env['orchid.account.cost.center'].search([('include_pl','=',True)]).sorted('id')
		values = {
			'cost_center_ids':[(6,0,cost_center_ids.ids)],
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
			self.year_validation()
	
	@api.onchange('to_date')
	def year_validation(self):
		if self.from_date and self.to_date:
			date_to = datetime.strptime(str(self.to_date),'%Y-%m-%d')
			date_from = datetime.strptime(str(self.from_date),'%Y-%m-%d')
			if date_from and date_to:
				if date_from.year!=date_to.year:
					raise UserError(_("Please select dates of same year !!!"))

	def generate_excel(self):

		lock_date = self.company_id.period_lock_date
		if not lock_date:
			raise UserError(_("Update All Lock Date"))
		if lock_date<self.from_date or lock_date<self.to_date:
			raise UserError(_(f"Current lock date is {lock_date}"))

		from_date =datetime.strptime(str(self.from_date),'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(str(self.to_date),'%Y-%m-%d').strftime('%d-%m-%Y')
		title="Statement for Profit & Loss Report for the period- "+ from_date + " "+"to " +to_date
		report_options = self.report_options
		report_name = _(dict(self.env['od.account.pl.report.wiz'].fields_get(allfields=['report_options'])['report_options']['selection'])[self.report_options])
		if self.analysis:
			title="Profit & Loss Analysis for the period- "+ from_date + " "+"to " +to_date
		if report_options == 'marketing':
			title="Marketing Report for the period- "+ from_date + " "+"to " +to_date
		filename =str(report_name)+'.xlsx'
		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		# sheet= workbook.add_worksheet('P&L Report')
		sheet= workbook.add_worksheet(str(report_name))
		style_main_header=workbook.add_format({'bold':True,'font_size':15,'align':'center','valign':'vcenter','bg_color':'#D7E4BC','border':0})
		style_sub_header=workbook.add_format({'bold':True,'bg_color':'#cccccc','border':0})
		style_sub_header_center=workbook.add_format({'bold':True,'bg_color':'#cccccc','border':0,'align':'center','valign':'vcenter'})
		style_balance=workbook.add_format({'bold':False,'num_format':'#,##0.00'})
		style_balance1=workbook.add_format({'bold':False,'align':'right'})
		style_balance_bold=workbook.add_format({'bold':True,'align':'right'})
		style_total=workbook.add_format({'bold':True,'num_format':'#,##0.00','bg_color':'#cccccc'})
		style_total_text=workbook.add_format({'bold':True,'bg_color':'#cccccc'})
		style_total_text1=workbook.add_format({'bold':True,'bg_color':'#cccccc'})
		style_total1=workbook.add_format({'bold':True,'num_format':'#,##0.00','bg_color':'#cccccc'})
		style_total2=workbook.add_format({'bold':False,'align':'right','bg_color':'#cccccc'})
		style_total3=workbook.add_format({'bold':False,'align':'right','bg_color':'#cccccc'})
		sheet.set_column('A:A',12)
		sheet.set_column('B:B',12)
		sheet.set_column('C:C',50)
		sheet.set_column('D:D',15)
		row = 0
		col =0
		if (not self.cost_center) and (not self.analysis):
			col_merge=15
			row_merge=row
			sheet.merge_range(row,col,row,col_merge,title,style_main_header)
			row=row+2
			
			month_ls =['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
			col=3
			for month in month_ls:
				sheet.write(row,col,month,style_sub_header)
				col = col+1
			sheet.write(row,col,"Total",style_sub_header)
			for group in self.env['od.report.template'].search([('report_value','=',report_options)], order='sequence asc'):
				row = row+1
				group_sum = {}
				if group.display_details == 'accounts':
					for account in group.account_account_ids:
						account_row_total = 0
						col=0
						sheet.write(row,col,account.name.group_id.code_prefix_start)
						col=col+1
						sheet.write(row,col,account.name.code)
						col=col+1
						sheet.write(row,col,account.name.name)
						col=col+1
						for i in range(1,14):
							mnt_value=" "
							sheet.write(row,col,mnt_value,style_balance1)
							sheet.set_column(row,col,15)
							col = col+1
						account_balance_qry = ''' SELECT 
													CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
													THEN sum(COALESCE((aml.balance*-1),0)) 
													ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance,
						 							date_part('month',aml.date) AS month 
						 							FROM account_move_line aml
						 							LEFT JOIN account_move am ON (aml.move_id=am.id)
						 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 							WHERE am.company_id=%s AND am.state='posted' 
						 							AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 							GROUP BY date_part('month',aml.date), aa.account_type '''%(self.company_id.id, account.name.id,account.name.account_type,self.from_date,self.to_date)
						self._cr.execute(account_balance_qry)
						acct_data = self._cr.dictfetchall()
						account_data = []
						if acct_data:
							if account.id ==4437:
								print("asssssss",acct_data)
							for i in range(1,13):
								data_dict = {}
								month_sum = 0
								for d in acct_data:
									if int(d['month'])==i:
										month_sum = month_sum+d['balance']
								if month_sum !=0:
									data_dict['month'] = i
									data_dict['balance'] = month_sum
									# data_dict['user_type_id'] = account.name.user_type_id.id
									account_data.append(data_dict)
						for data in account_data:
							month = int(data['month'])
							balance = data['balance'] if data['balance']!=None else 0
							bal_col = month+2
							account_row_total = account_row_total+balance
							if data['month'] in group_sum:
								group_sum[month] = group_sum[month]+balance
							else:
								group_sum[month] = balance
							# excel_balance = balance
							# if excel_balance<0:
								# excel_balance = excel_balance*-1
							# sheet.write(row,bal_col,abs(balance),style_balance)
							if report_options == 'marketing':
								sheet.write(row,bal_col,balance*-1,style_balance)
							elif report_options == 'pl':
								# sheet.write(row,bal_col,abs(balance),style_balance)
								sheet.write(row,bal_col,balance*-1,style_balance)
							# sheet.write(row,bal_col,excel_balance,style_balance)
						if account_row_total!=0:
							# sheet.write(row,15,abs(account_row_total),style_balance)
							if report_options == 'marketing':
								sheet.write(row,15,account_row_total*-1,style_balance)
							elif report_options == 'pl':
								# sheet.write(row,15,abs(account_row_total),style_balance)
								sheet.write(row,15,account_row_total*-1,style_balance)
						row=row+1
						col=0
					sheet.write(row,col," ",style_total_text)
					col=col+1
					sheet.write(row,col,group.account_grp_id.code_prefix_start,style_total_text)
					col=col+1
					sheet.write(row,col,group.name,style_total_text)
					col=col+1
					group_row_total = 0
					for i in range (1,13):
						end_col=i+2
						if i in group_sum:
							end_sum=group_sum[i]
							# sheet.write(row,end_col,abs(end_sum),style_total)
							if report_options == 'marketing':
								sheet.write(row,end_col,end_sum*-1,style_total)
							elif report_options == 'pl':
								# sheet.write(row,end_col,abs(end_sum),style_total)
								sheet.write(row,end_col,end_sum*-1,style_total)
							group_row_total = group_row_total + end_sum
						else:
							mnt_value=" "
							sheet.write(row,end_col,mnt_value,style_total2)
					if group_row_total!=0:
						# sheet.write(row,15,abs(group_row_total),style_total)
						if report_options == 'marketing':
							sheet.write(row,15,group_row_total*-1,style_total)
						elif report_options == 'pl':
							# sheet.write(row,15,abs(group_row_total),style_total)
							sheet.write(row,15,group_row_total*-1,style_total)
					else:
						sheet.write(row,15," ",style_total2)
					col=0

				if group.display_details == 'compute':
					group_accounts = []
					for subgroup in group.account_group_ids:
						for acc in subgroup.name.account_account_ids:
							group_accounts.append(acc.name)
					account_data = []
					for account in group_accounts:
						account_balance_qry = ''' SELECT 
												CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
												THEN sum(COALESCE((aml.balance*-1),0)) 
												ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance, 
												date_part('month',aml.date) AS month 
												FROM account_move_line aml
												LEFT JOIN account_move am ON (aml.move_id=am.id)
						 						LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 						WHERE am.company_id=%s AND am.state='posted' AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 						GROUP BY date_part('month',aml.date), aa.account_type '''%(self.company_id.id, account.id,account.account_type,self.from_date,self.to_date)
						
						# print("accccccccc",account_balance_qry)
						self._cr.execute(account_balance_qry)
						acct_data = self._cr.dictfetchall()
						if acct_data:
							if account.id==4437:
								print("ooopppppp",acct_data)
							for i in range(1,13):
								data_dict = {}
								month_sum = 0
								for d in acct_data:
									if int(d['month'])==i:
										month_sum = month_sum+d['balance']
								if month_sum !=0:
									data_dict['month'] = i
									data_dict['balance'] = month_sum
									account_data.append(data_dict)
					for data in account_data:
						month = int(data['month'])
						balance = data['balance'] if data['balance']!=None else 0
						bal_col = month+2
						if group.id==22:
							print("opouuuuuuuuuuuu",group_sum)
						if data['month'] in group_sum:
							group_sum[month] = group_sum[month]+balance
						else:
							group_sum[month] = balance
						if group.id==22:
							print("loppoooooo",group_sum,group.name)
					sheet.write(row,col," ",style_total_text1)
					col=col+1
					sheet.write(row,col,group.account_grp_id.code_prefix_start,style_total_text1)
					col=col+1
					sheet.write(row,col,group.name,style_total_text1)
					col=col+1
					group_row_total = 0
					for i in range (1,13):
						end_col=i+2
						if i in group_sum:
							end_sum=group_sum[i]
							# sheet.write(row,end_col,abs(end_sum),style_total1)
							if report_options == 'marketing':
								sheet.write(row,end_col,end_sum*-1,style_total1)
							elif report_options == 'pl':
								# sheet.write(row,end_col,abs(end_sum),style_total1)
								sheet.write(row,end_col,end_sum*-1,style_total1)
							group_row_total = group_row_total + end_sum
						else:
							mnt_value=" "
							sheet.write(row,end_col,mnt_value,style_total3)
					if group_row_total!=0:
						sheet.write(row,15,abs(group_row_total),style_total1)
						if report_options == 'marketing':
							sheet.write(row,15,group_row_total*-1,style_total1)
						elif report_options == 'pl':
							# sheet.write(row,15,abs(group_row_total),style_total1)
							sheet.write(row,15,group_row_total*-1,style_total1)
					else:
						sheet.write(row,15," ",style_total3)
					col=0
				row = row+1


		if self.cost_center and self.cost_center_ids:
			cost_center_dict = {}
			ls_index = 0

			for cost_center_id in self.cost_center_ids.sorted('id'):
				ls_index+=1
				cost_center_dict[cost_center_id.id]=ls_index

			cost_center_len=len(self.cost_center_ids.ids)+3
			col_merge = cost_center_len
			row_merge=row
			sheet.merge_range(row,col,row,col_merge,title,style_main_header)
			row=row+2
			
			print("cost_center_dict",cost_center_dict,cost_center_len)
			col=3
			for cost_center_id in self.cost_center_ids.sorted('id'):
				sheet.write(row,col,cost_center_id.name,style_sub_header)
				col = col+1
			sheet.write(row,col,"Total",style_sub_header)
			for group in self.env['od.report.template'].search([('report_value','=',report_options)], order='sequence asc'):
				row = row+1
				group_sum = {}
				if group.display_details == 'accounts':
					for account in group.account_account_ids:
						account_row_total = 0
						col=0
						sheet.write(row,col,account.name.group_id.code_prefix_start)
						col=col+1
						sheet.write(row,col,account.name.code)
						col=col+1
						sheet.write(row,col,account.name.name)
						col=col+1
						for i in range(1,(cost_center_len+2)):
							cost_center_value=" "
							sheet.write(row,col,cost_center_value,style_balance1)
							sheet.set_column(row,col,cost_center_len)
							col = col+1
						account_balance_qry = ''' SELECT 
													CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
													THEN sum(COALESCE((aml.balance*-1),0)) 
													ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance,
						 							CASE WHEN aml.orchid_cc_id is not null
						 							THEN aml.orchid_cc_id 
						 							ELSE 0 END AS cost_center_id 
						 							FROM account_move_line aml
						 							LEFT JOIN account_move am ON (aml.move_id=am.id)
						 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 							WHERE am.company_id=%s AND am.state='posted' 
						 							AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 							GROUP BY aml.orchid_cc_id, aa.account_type '''%(self.company_id.id, account.name.id,account.name.account_type,self.from_date,self.to_date)
						self._cr.execute(account_balance_qry)
						acct_data = self._cr.dictfetchall()
						account_data = []
						if acct_data:
							for i in self.cost_center_ids.sorted('id').ids:
								data_dict = {}
								cost_center_sum = 0
								for d in acct_data:
									if int(d['cost_center_id'])==i:
										cost_center_sum = cost_center_sum+d['balance']
								if cost_center_sum !=0:
									data_dict['cost_center_id'] = i
									data_dict['balance'] = cost_center_sum
									# data_dict['user_type_id'] = account.name.user_type_id.id
									account_data.append(data_dict)
						for data in account_data:
							cost_center_id = int(data['cost_center_id'])
							balance = data['balance'] if data['balance']!=None else 0
							bal_col = cost_center_dict[cost_center_id]+2
							account_row_total = account_row_total+balance
							if data['cost_center_id'] in group_sum:
								group_sum[cost_center_id] = group_sum[cost_center_id]+balance
							else:
								group_sum[cost_center_id] = balance
							# excel_balance = balance
							# if excel_balance<0:
								# excel_balance = excel_balance*-1
							# sheet.write(row,bal_col,abs(balance),style_balance)
							if report_options == 'marketing':
								sheet.write(row,bal_col,balance*-1,style_balance)
							elif report_options == 'pl':
								# sheet.write(row,bal_col,abs(balance),style_balance)
								sheet.write(row,bal_col,balance*-1,style_balance)
							# sheet.write(row,bal_col,excel_balance,style_balance)
						if account_row_total!=0:
							# sheet.write(row,cost_center_len,abs(account_row_total),style_balance)
							if report_options == 'marketing':
								sheet.write(row,cost_center_len,account_row_total*-1,style_balance)
							elif report_options == 'pl':
								# sheet.write(row,cost_center_len,abs(account_row_total),style_balance)
								sheet.write(row,cost_center_len,account_row_total*-1,style_balance)
						row=row+1
						col=0
					sheet.write(row,col," ",style_total_text)
					col=col+1
					sheet.write(row,col,group.account_grp_id.code_prefix_start,style_total_text)
					col=col+1
					sheet.write(row,col,group.name,style_total_text)
					col=col+1
					group_row_total = 0
					for i in self.cost_center_ids.sorted('id').ids:
						end_col=cost_center_dict[i]+2
						if i in group_sum:
							end_sum=group_sum[i]
							# sheet.write(row,end_col,abs(end_sum),style_total)
							if report_options == 'marketing':
								sheet.write(row,end_col,end_sum*-1,style_total)
							elif report_options == 'pl':
								# sheet.write(row,end_col,abs(end_sum),style_total)
								sheet.write(row,end_col,end_sum*-1,style_total)
							group_row_total = group_row_total + end_sum
						else:
							cost_center_value=" "
							sheet.write(row,end_col,cost_center_value,style_total2)
					if group_row_total!=0:
						# sheet.write(row,15,abs(group_row_total),style_total)
						if report_options == 'marketing':
							sheet.write(row,cost_center_len,group_row_total*-1,style_total)
						elif report_options == 'pl':
							# sheet.write(row,cost_center_len,abs(group_row_total),style_total)
							sheet.write(row,cost_center_len,group_row_total*-1,style_total)
					else:
						sheet.write(row,cost_center_len," ",style_total2)
					col=0

				if group.display_details == 'compute':
					group_accounts = []
					for subgroup in group.account_group_ids:
						for acc in subgroup.name.account_account_ids:
							group_accounts.append(acc.name)
					account_data = []
					for account in group_accounts:
						account_balance_qry = ''' SELECT 
												CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
												THEN sum(COALESCE((aml.balance*-1),0)) 
												ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance, 
												CASE WHEN aml.orchid_cc_id is not null
					 							THEN aml.orchid_cc_id 
					 							ELSE 0 END AS cost_center_id
												FROM account_move_line aml
												LEFT JOIN account_move am ON (aml.move_id=am.id)
						 						LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 						WHERE am.company_id=%s AND am.state='posted' AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 						GROUP BY aml.orchid_cc_id, aa.account_type '''%(self.company_id.id, account.id,account.account_type,self.from_date,self.to_date)
						print("accccccccc",account_balance_qry)
						self._cr.execute(account_balance_qry)
						acct_data = self._cr.dictfetchall()
						if acct_data:
							for i in self.cost_center_ids.sorted('id').ids:
								data_dict = {}
								cost_center_sum = 0
								for d in acct_data:
									if int(d['cost_center_id'])==i:
										cost_center_sum = cost_center_sum+d['balance']
								if cost_center_sum !=0:
									data_dict['cost_center_id'] = i
									data_dict['balance'] = cost_center_sum
									account_data.append(data_dict)
					for data in account_data:
						cost_center_id = int(data['cost_center_id'])
						balance = data['balance'] if data['balance']!=None else 0
						bal_col = cost_center_dict[cost_center_id]+2
						if data['cost_center_id'] in group_sum:
							group_sum[cost_center_id] = group_sum[cost_center_id]+balance
						else:
							group_sum[cost_center_id] = balance
					sheet.write(row,col," ",style_total_text1)
					col=col+1
					sheet.write(row,col,group.account_grp_id.code_prefix_start,style_total_text1)
					col=col+1
					sheet.write(row,col,group.name,style_total_text1)
					col=col+1
					group_row_total = 0
					for i in self.cost_center_ids.sorted('id').ids:
						end_col=cost_center_dict[i]+2
						if i in group_sum:
							end_sum=group_sum[i]
							# sheet.write(row,end_col,abs(end_sum),style_total1)
							if report_options == 'marketing':
								sheet.write(row,end_col,end_sum*-1,style_total1)
							elif report_options == 'pl':
								# sheet.write(row,end_col,abs(end_sum),style_total1)
								sheet.write(row,end_col,end_sum*-1,style_total1)
							group_row_total = group_row_total + end_sum
						else:
							cost_center_value=" "
							sheet.write(row,end_col,cost_center_value,style_total3)
					if group_row_total!=0:
						sheet.write(row,cost_center_len,abs(group_row_total),style_total1)
						if report_options == 'marketing':
							sheet.write(row,cost_center_len,group_row_total*-1,style_total1)
						elif report_options == 'pl':
							# sheet.write(row,cost_center_len,abs(group_row_total),style_total1)
							sheet.write(row,cost_center_len,group_row_total*-1,style_total1)
					else:
						sheet.write(row,cost_center_len," ",style_total3)
					col=0
				row = row+1

		if self.analysis:
			col_merge=16
			row_merge=row
			sheet.merge_range(row,col,row,col_merge,title,style_main_header)
			row=row+2
			
			headers =['Current Month','Year to Date','Year to Date PY','Budget YTD CY','Budget CY','Variance YTD Vs  YTD PY','Variance YTD Vs Budget YTD']
			col=0
			col=col+3
			for header in headers:
				col_merge=col+1
				sheet.merge_range(row,col,row,col_merge,header,style_sub_header_center)
				row=row+1
				sheet.write(row,col,"Amount",style_balance_bold)
				sheet.set_column(row,col,30)
				col=col+1
				sheet.write(row,col,"%",style_balance_bold)
				sheet.set_column(row,col,20)
				row=row-1
				col = col+1
			for group in self.env['od.report.template'].search([('report_value','=',report_options)], order='sequence asc'):
				row = row+2
				group_sum = {
				'current':{'balance':0},
				'ytd':{'balance':0},
				'ytd_py':{'balance':0},
				'budget_ytd':{'balance':0},
				'budget_current':{'balance':0},
				'variance':{'balance':0},
				'variance_budget':{'balance':0},
				}
				if group.display_details == 'accounts':
					for account in group.account_account_ids:
						account_row_total = 0
						col=0
						# sheet.write(row,col,account.name.group_id.code_prefix_start)
						if not group.show_group_budget:
							sheet.write(row,col,account.name.code[:4])
						col=col+1
						if not group.show_group_budget:
							sheet.write(row,col,account.name.code)
						col=col+1
						if not group.show_group_budget:
							sheet.write(row,col,account.name.name)
						col=col+1
						# for i in range(1,14):
						# 	mnt_value=" "
						# 	sheet.write(row,col,mnt_value,style_balance1)
						# 	sheet.set_column(row,col,15)
						# 	col = col+1
						current_month_qry = ''' SELECT 
													CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
													THEN sum(COALESCE((aml.balance*-1),0)) 
													ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance
						 							FROM account_move_line aml
						 							LEFT JOIN account_move am ON (aml.move_id=am.id)
						 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 							WHERE am.company_id=%s AND am.state='posted' 
						 							AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 							GROUP BY aa.account_type '''%(self.company_id.id, account.name.id,account.name.account_type,self.from_date,self.to_date)
						self._cr.execute(current_month_qry)
						current_data = self._cr.fetchall()
						current_month_data = [c[0] for c in current_data if c[0]!=None]
						current_month = 0
						current_month_col = col
						if current_month_data:
							current_month = current_month_data[0]
						group_sum['current']['balance'] = group_sum['current']['balance']+current_month
						group_sum['current']['col'] = current_month_col
						group_sum['current']['col_per'] = current_month_col+1
						if not group.show_group_budget:
							sheet.write(row,current_month_col,abs(current_month),style_balance)
							sheet.write(row,current_month_col+1,0,style_balance)
						col=col+2

						current_year_start = self.to_date.replace(day=1, month=1)
						ytd_qry = ''' SELECT 
													CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
													THEN sum(COALESCE((aml.balance*-1),0)) 
													ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance
						 							FROM account_move_line aml
						 							LEFT JOIN account_move am ON (aml.move_id=am.id)
						 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 							WHERE am.company_id=%s AND am.state='posted' 
						 							AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 							GROUP BY aa.account_type '''%(self.company_id.id, account.name.id,account.name.account_type,current_year_start,self.to_date)
						self._cr.execute(ytd_qry)
						ytd_data = self._cr.fetchall()
						ytd_full_data = [c[0] for c in ytd_data if c[0]!=None]
						ytd = 0
						ytd_col = col
						if ytd_full_data:
							ytd = ytd_full_data[0]
						group_sum['ytd']['balance'] = group_sum['ytd']['balance']+ytd
						group_sum['ytd']['col'] = ytd_col
						group_sum['ytd']['col_per'] = ytd_col+1

						if not group.show_group_budget:
							sheet.write(row,ytd_col,abs(ytd),style_balance)
							sheet.write(row,ytd_col+1,0,style_balance)
						col=col+2

						start_py_year = self.from_date.year - 1
						end_py_year = self.to_date.year - 1
						py_year_start = self.from_date.replace(year=start_py_year)
						py_year_end = self.to_date.replace(year=end_py_year)
						ytd_py_qry = ''' SELECT 
													CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
													THEN sum(COALESCE((aml.balance*-1),0)) 
													ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance
						 							FROM account_move_line aml
						 							LEFT JOIN account_move am ON (aml.move_id=am.id)
						 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 							WHERE am.company_id=%s AND am.state='posted' 
						 							AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 							GROUP BY aa.account_type '''%(self.company_id.id, account.name.id,account.name.account_type,py_year_start,py_year_end)
						self._cr.execute(ytd_py_qry)
						ytd_py_data = self._cr.fetchall()
						ytd_py_full_data = [c[0] for c in ytd_py_data if c[0]!=None]
						ytd_py = 0
						ytd_py_col = col
						if ytd_py_full_data:
							ytd_py = ytd_py_full_data[0]
						group_sum['ytd_py']['balance'] = group_sum['ytd_py']['balance']+ytd_py
						group_sum['ytd_py']['col'] = ytd_py_col
						group_sum['ytd_py']['col_per'] = ytd_py_col+1

						if not group.show_group_budget:
							sheet.write(row,ytd_py_col,abs(ytd_py),style_balance)
							sheet.write(row,ytd_py_col+1,0,style_balance)
						col=col+2

						if not group.show_group_budget:
							budget_ytd_qry = ''' SELECT 
														CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
														THEN sum(COALESCE((aml.planned_amount*-1),0)) 
														ELSE (sum(COALESCE(aml.planned_amount*-1,0))) end as balance
							 							FROM orchid_budget_analysis_line aml
							 							LEFT JOIN orchid_budget_analysis am ON (aml.od_budget_id=am.id)
							 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
							 							WHERE am.company_id=%s AND am.od_state='approved' 
							 							AND aml.account_id=%s AND aa.account_type='%s' AND am.od_date_start >='%s' AND am.od_date_end<='%s' 
							 							GROUP BY aa.account_type '''%(self.company_id.id, account.name.id,account.name.account_type,self.from_date,self.to_date)
							self._cr.execute(budget_ytd_qry)
							budget_ytd_data = self._cr.fetchall()
							budget_ytd_full_data = [c[0] for c in budget_ytd_data if c[0]!=None]
							budget_ytd = 0
							budget_ytd_col = col
							if budget_ytd_full_data:
								budget_ytd = budget_ytd_full_data[0]
							group_sum['budget_ytd']['balance'] = group_sum['budget_ytd']['balance']+budget_ytd
							group_sum['budget_ytd']['col'] = budget_ytd_col
							group_sum['budget_ytd']['col_per'] = budget_ytd_col+1

							sheet.write(row,budget_ytd_col,abs(budget_ytd),style_balance)
							sheet.write(row,budget_ytd_col+1,0,style_balance)
							col=col+2

							budget_current_qry = ''' SELECT 
														CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
														THEN sum(COALESCE((aml.budget_amount*-1),0)) 
														ELSE (sum(COALESCE(aml.budget_amount*-1,0))) end as balance
							 							FROM orchid_budget_analysis_line aml
							 							LEFT JOIN orchid_budget_analysis am ON (aml.od_budget_id=am.id)
							 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
							 							WHERE am.company_id=%s AND am.od_state='approved' 
							 							AND aml.account_id=%s AND aa.account_type='%s' AND am.od_date_start >='%s' AND am.od_date_end<='%s' 
							 							GROUP BY aa.account_type '''%(self.company_id.id, account.name.id,account.name.account_type,self.from_date,self.to_date)
							self._cr.execute(budget_current_qry)
							budget_current_data = self._cr.fetchall()
							budget_current_full_data = [c[0] for c in budget_current_data if c[0]!=None]
							budget_current= 0
							budget_current_col = col
							if budget_current_full_data:
								budget_current = budget_current_full_data[0]
							group_sum['budget_current']['balance'] = group_sum['budget_current']['balance']+budget_current
							group_sum['budget_current']['col'] = budget_current_col
							group_sum['budget_current']['col_per'] = budget_current_col+1

							sheet.write(row,budget_current_col,abs(budget_current),style_balance)
							sheet.write(row,budget_current_col+1,0,style_balance)

						# new
						if group.show_group_budget:
							budget_ytd_qry = ''' SELECT 
													-- CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
													-- THEN sum(COALESCE((aml.planned_amount*-1),0)) 
													-- ELSE (sum(COALESCE(aml.planned_amount*-1,0))) end as balance
													sum(COALESCE((aml.planned_amount*-1),0)) as balance
						 							FROM orchid_budget_analysis_line aml
						 							LEFT JOIN orchid_budget_analysis am ON (aml.od_budget_id=am.id)
						 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 							WHERE am.company_id=%s AND am.od_state='approved' 
						 							AND aml.report_template_id =%s 
						 							 AND am.od_date_start >='%s' AND am.od_date_end<='%s' 
						 							GROUP BY aml.report_template_id '''%(self.company_id.id, group.id,self.from_date,self.to_date)
							self._cr.execute(budget_ytd_qry)
							budget_ytd_data = self._cr.fetchall()
							budget_ytd_full_data = [c[0] for c in budget_ytd_data if c[0]!=None]
							budget_ytd = 0
							budget_ytd_col = col
							if budget_ytd_full_data:
								budget_ytd = budget_ytd_full_data[0]
							group_sum['budget_ytd']['balance'] = budget_ytd
							group_sum['budget_ytd']['col'] = budget_ytd_col
							group_sum['budget_ytd']['col_per'] = budget_ytd_col+1
							col=col+2

							budget_current_qry = ''' SELECT 
														-- CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
														-- THEN sum(COALESCE((aml.budget_amount*-1),0)) 
														-- ELSE (sum(COALESCE(aml.budget_amount*-1,0))) end as balance
														sum(COALESCE((aml.budget_amount*-1),0)) as balance
							 							FROM orchid_budget_analysis_line aml
							 							LEFT JOIN orchid_budget_analysis am ON (aml.od_budget_id=am.id)
							 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
							 							WHERE am.company_id=%s AND am.od_state='approved' 
							 							AND aml.report_template_id=%s AND am.od_date_start >='%s' AND am.od_date_end<='%s' 
							 							GROUP BY aml.report_template_id '''%(self.company_id.id, group.id,self.from_date,self.to_date)
							self._cr.execute(budget_current_qry)
							budget_current_data = self._cr.fetchall()
							budget_current_full_data = [c[0] for c in budget_current_data if c[0]!=None]
							budget_current= 0
							budget_current_col = col
							if budget_current_full_data:
								budget_current = budget_current_full_data[0]
							group_sum['budget_current']['balance'] = budget_current
							group_sum['budget_current']['col'] = budget_current_col
							group_sum['budget_current']['col_per'] = budget_current_col+1

						col=col+2
						
						variance = 0
						variance = ytd - ytd_py
						variance_col=col
						group_sum['variance']['balance'] = group_sum['variance']['balance']+variance
						group_sum['variance']['col'] = variance_col
						group_sum['variance']['col_per'] = variance_col+1

						if not group.show_group_budget:
							sheet.write(row,variance_col,abs(variance),style_balance)
							sheet.write(row,variance_col+1,0,style_balance)
						col=col+2

						variance_budget = 0
						variance_budget = variance - budget_ytd
						variance_budget_col=col
						group_sum['variance_budget']['balance'] = group_sum['variance_budget']['balance']+variance_budget
						group_sum['variance_budget']['col'] = variance_budget_col
						group_sum['variance_budget']['col_per'] = variance_budget_col+1

						if not group.show_group_budget:
							sheet.write(row,variance_budget_col,abs(variance_budget),style_balance)
							sheet.write(row,variance_budget_col+1,0,style_balance)
						col=col+2
						if not group.show_group_budget:
							row=row+1
						col=0
					sheet.write(row,col," ",style_total_text)
					col=col+1
					sheet.write(row,col,group.account_grp_id.code_prefix_start,style_total_text)
					col=col+1
					sheet.write(row,col,group.name,style_total_text)
					
					sheet.write(row,group_sum['current']['col'],abs(group_sum['current']['balance']),style_total)
					sheet.write(row,group_sum['current']['col_per'],0,style_total)
					sheet.write(row,group_sum['ytd']['col'],abs(group_sum['ytd']['balance']),style_total)
					sheet.write(row,group_sum['ytd']['col_per'],0,style_total)
					sheet.write(row,group_sum['ytd_py']['col'],abs(group_sum['ytd_py']['balance']),style_total)
					sheet.write(row,group_sum['ytd_py']['col_per'],0,style_total)
					sheet.write(row,group_sum['budget_current']['col'],abs(group_sum['budget_current']['balance']),style_total)
					sheet.write(row,group_sum['budget_current']['col_per'],0,style_total)
					sheet.write(row,group_sum['budget_ytd']['col'],abs(group_sum['budget_ytd']['balance']),style_total)
					sheet.write(row,group_sum['budget_ytd']['col_per'],0,style_total)
					sheet.write(row,group_sum['variance']['col'],abs(group_sum['variance']['balance']),style_total)
					sheet.write(row,group_sum['variance']['col_per'],0,style_total)
					sheet.write(row,group_sum['variance_budget']['col'],abs(group_sum['variance_budget']['balance']),style_total)
					sheet.write(row,group_sum['variance_budget']['col_per'],0,style_total)
					col=0

				if group.display_details == 'compute':
					group_accounts = []
					for subgroup in group.account_group_ids:
						for acc in subgroup.name.account_account_ids:
							group_accounts.append(acc.name)
					account_data = []
					# print("group_accounts",group_accounts)
					account_template_id = False
					for account in group_accounts:
						for subgroup in group.account_group_ids:
							for acc in subgroup.name.account_account_ids:
								if acc.name.id==account.id:
									account_template_id = subgroup.name
									break;


						# print("account_template_idaccount_template_id",account_template_id,account_template_id.name)
						col=0
						col+=3
						current_month_qry = ''' SELECT 
													CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
													THEN sum(COALESCE((aml.balance*-1),0)) 
													ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance
						 							FROM account_move_line aml
						 							LEFT JOIN account_move am ON (aml.move_id=am.id)
						 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 							WHERE am.company_id=%s AND am.state='posted' 
						 							AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 							GROUP BY aa.account_type '''%(self.company_id.id, account.id,account.account_type,self.from_date,self.to_date)
						self._cr.execute(current_month_qry)
						current_data = self._cr.fetchall()
						current_month_data = [c[0] for c in current_data if c[0]!=None]
						current_month = 0
						current_month_col = col
						if current_month_data:
							current_month = current_month_data[0]
						
						# print("vvv",current_month,group_sum['current']['balance'])
						group_sum['current']['balance'] = group_sum['current']['balance']+current_month
						group_sum['current']['col'] = current_month_col
						group_sum['current']['col_per'] = current_month_col+1
						col=col+2
						# print("vvv",current_month,group_sum['current']['balance'])

						current_year_start = self.to_date.replace(day=1, month=1)
						ytd_qry = ''' SELECT 
													CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
													THEN sum(COALESCE((aml.balance*-1),0)) 
													ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance
						 							FROM account_move_line aml
						 							LEFT JOIN account_move am ON (aml.move_id=am.id)
						 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 							WHERE am.company_id=%s AND am.state='posted' 
						 							AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 							GROUP BY aa.account_type '''%(self.company_id.id, account.id,account.account_type,current_year_start,self.to_date)
						self._cr.execute(ytd_qry)
						ytd_data = self._cr.fetchall()
						ytd_full_data = [c[0] for c in ytd_data if c[0]!=None]
						ytd = 0
						ytd_col = col
						if ytd_full_data:
							ytd = ytd_full_data[0]
						group_sum['ytd']['balance'] = group_sum['ytd']['balance']+ytd
						group_sum['ytd']['col'] = ytd_col
						group_sum['ytd']['col_per'] = ytd_col
						col=col+2

						start_py_year = self.from_date.year - 1
						end_py_year = self.to_date.year - 1
						py_year_start = self.from_date.replace(year=start_py_year)
						py_year_end = self.to_date.replace(year=end_py_year)
						ytd_py_qry = ''' SELECT 
													CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
													THEN sum(COALESCE((aml.balance*-1),0)) 
													ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance
						 							FROM account_move_line aml
						 							LEFT JOIN account_move am ON (aml.move_id=am.id)
						 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
						 							WHERE am.company_id=%s AND am.state='posted' 
						 							AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
						 							GROUP BY aa.account_type '''%(self.company_id.id, account.id,account.account_type,py_year_start,py_year_end)
						self._cr.execute(ytd_py_qry)
						ytd_py_data = self._cr.fetchall()
						ytd_py_full_data = [c[0] for c in ytd_py_data if c[0]!=None]
						ytd_py = 0
						ytd_py_col = col
						if ytd_py_full_data:
							ytd_py = ytd_py_full_data[0]
						group_sum['ytd_py']['balance'] = group_sum['ytd_py']['balance']+ytd_py
						group_sum['ytd_py']['col'] = ytd_py_col
						group_sum['ytd_py']['col_per'] = ytd_py_col+1
						col=col+2


						if account_template_id.show_group_budget:

							budget_ytd_qry = ''' SELECT 
														-- CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
														-- THEN sum(COALESCE((aml.planned_amount*-1),0)) 
														-- ELSE (sum(COALESCE(aml.planned_amount*-1,0))) end as balance
														sum(COALESCE((aml.planned_amount*-1),0)) as balance
							 							FROM orchid_budget_analysis_line aml
							 							LEFT JOIN orchid_budget_analysis am ON (aml.od_budget_id=am.id)
							 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
							 							WHERE am.company_id=%s AND am.od_state='approved' 
							 							AND aml.report_template_id=%s AND am.od_date_start >='%s' AND am.od_date_end<='%s' 
							 							GROUP BY aml.report_template_id '''%(self.company_id.id, account_template_id.id,self.from_date,self.to_date)
							self._cr.execute(budget_ytd_qry)
							budget_ytd_data = self._cr.fetchall()
							budget_ytd_full_data = [c[0] for c in budget_ytd_data if c[0]!=None]
							budget_ytd = 0
							budget_ytd_col = col
							if budget_ytd_full_data:
								budget_ytd = budget_ytd_full_data[0]
							group_sum['budget_ytd']['balance'] = budget_ytd
							group_sum['budget_ytd']['col'] = budget_ytd_col
							group_sum['budget_ytd']['col_per'] = budget_ytd_col+1

							col=col+2

							budget_current_qry = ''' SELECT 
														-- CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
														-- THEN sum(COALESCE((aml.budget_amount*-1),0)) 
														-- ELSE (sum(COALESCE(aml.budget_amount*-1,0))) end as balance
														sum(COALESCE((aml.budget_amount*-1),0)) as balance
							 							FROM orchid_budget_analysis_line aml
							 							LEFT JOIN orchid_budget_analysis am ON (aml.od_budget_id=am.id)
							 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
							 							WHERE am.company_id=%s AND am.od_state='approved' 
							 							AND aml.report_template_id=%s AND am.od_date_start >='%s' AND am.od_date_end<='%s' 
							 							GROUP BY aml.report_template_id '''%(self.company_id.id, account_template_id.id,self.from_date,self.to_date)
							self._cr.execute(budget_current_qry)
							budget_current_data = self._cr.fetchall()
							budget_current_full_data = [c[0] for c in budget_current_data if c[0]!=None]
							budget_current= 0
							budget_current_col = col
							if budget_current_full_data:
								budget_current = budget_current_full_data[0]
							group_sum['budget_current']['balance'] = budget_current
							group_sum['budget_current']['col'] = budget_current_col
							group_sum['budget_current']['col_per'] = budget_current_col+1


						if not account_template_id.show_group_budget:
							budget_ytd_qry = ''' SELECT 
														CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
														THEN sum(COALESCE((aml.planned_amount*-1),0)) 
														ELSE (sum(COALESCE(aml.planned_amount*-1,0))) end as balance
							 							FROM orchid_budget_analysis_line aml
							 							LEFT JOIN orchid_budget_analysis am ON (aml.od_budget_id=am.id)
							 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
							 							WHERE am.company_id=%s AND am.od_state='approved' 
							 							AND aml.account_id=%s AND aa.account_type='%s' AND am.od_date_start >='%s' AND am.od_date_end<='%s' 
							 							GROUP BY aa.account_type '''%(self.company_id.id, account.id,account.account_type,self.from_date,self.to_date)
							self._cr.execute(budget_ytd_qry)
							budget_ytd_data = self._cr.fetchall()
							budget_ytd_full_data = [c[0] for c in budget_ytd_data if c[0]!=None]
							budget_ytd = 0
							budget_ytd_col = col
							if budget_ytd_full_data:
								budget_ytd = budget_ytd_full_data[0]
							group_sum['budget_ytd']['balance'] = group_sum['budget_ytd']['balance']+budget_ytd
							group_sum['budget_ytd']['col'] = budget_ytd_col
							group_sum['budget_ytd']['col_per'] = budget_ytd_col+1

							col=col+2

							budget_current_qry = ''' SELECT 
														CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
														THEN sum(COALESCE((aml.budget_amount*-1),0)) 
														ELSE (sum(COALESCE(aml.budget_amount*-1,0))) end as balance
							 							FROM orchid_budget_analysis_line aml
							 							LEFT JOIN orchid_budget_analysis am ON (aml.od_budget_id=am.id)
							 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
							 							WHERE am.company_id=%s AND am.od_state='approved' 
							 							AND aml.account_id=%s AND aa.account_type='%s' AND am.od_date_start >='%s' AND am.od_date_end<='%s' 
							 							GROUP BY aa.account_type '''%(self.company_id.id, account.id,account.account_type,self.from_date,self.to_date)
							self._cr.execute(budget_current_qry)
							budget_current_data = self._cr.fetchall()
							budget_current_full_data = [c[0] for c in budget_current_data if c[0]!=None]
							budget_current= 0
							budget_current_col = col
							if budget_current_full_data:
								budget_current = budget_current_full_data[0]
							group_sum['budget_current']['balance'] = group_sum['budget_current']['balance']+budget_current
							group_sum['budget_current']['col'] = budget_current_col
							group_sum['budget_current']['col_per'] = budget_current_col+1

						col=col+2
						
						variance = 0
						variance = ytd - ytd_py
						variance_col=col
						group_sum['variance']['balance'] = group_sum['variance']['balance']+variance
						group_sum['variance']['col'] = variance_col
						group_sum['variance']['col_per'] = variance_col+1
						col=col+2

						variance_budget = 0
						variance_budget = variance - budget_ytd
						variance_budget_col=col
						group_sum['variance_budget']['balance'] = group_sum['variance_budget']['balance']+variance_budget
						group_sum['variance_budget']['col'] = variance_budget_col
						group_sum['variance_budget']['col_per'] = variance_budget_col+1

					
					col=0
					sheet.write(row,col," ",style_total_text)
					col=col+1
					sheet.write(row,col,group.account_grp_id.code_prefix_start,style_total_text)
					col=col+1
					sheet.write(row,col,group.name,style_total_text)
					# print("group_sum['current']['col']group_sum['current']['col']",group_sum['current']['col'])
					sheet.write(row,group_sum['current']['col'],abs(group_sum['current']['balance']),style_total)
					sheet.write(row,group_sum['current']['col_per'],0,style_total)
					sheet.write(row,group_sum['ytd']['col'],abs(group_sum['ytd']['balance']),style_total)
					sheet.write(row,group_sum['ytd']['col_per'],0,style_total)
					sheet.write(row,group_sum['ytd_py']['col'],abs(group_sum['ytd_py']['balance']),style_total)
					sheet.write(row,group_sum['ytd_py']['col_per'],0,style_total)
					sheet.write(row,group_sum['budget_current']['col'],abs(group_sum['budget_current']['balance']),style_total)
					sheet.write(row,group_sum['budget_current']['col_per'],0,style_total)
					sheet.write(row,group_sum['budget_ytd']['col'],abs(group_sum['budget_ytd']['balance']),style_total)
					sheet.write(row,group_sum['budget_ytd']['col_per'],0,style_total)
					sheet.write(row,group_sum['variance']['col'],abs(group_sum['variance']['balance']),style_total)
					sheet.write(row,group_sum['variance']['col_per'],0,style_total)
					sheet.write(row,group_sum['variance_budget']['col'],abs(group_sum['variance_budget']['balance']),style_total)
					sheet.write(row,group_sum['variance_budget']['col_per'],0,style_total)

					col=0
				row = row+1
		workbook.close()
		output.seek(0)
		# excel_file = base64.encodestring(output.read())
		excel_file = base64.encodebytes(output.read())
		self.write({'excel_file':excel_file,'file_name':filename})
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.account.pl.report.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }



