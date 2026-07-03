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

class OrchidAccountBalanceSheetReport(models.TransientModel):

	_name = 'od.account.bs.report.wiz'
	description = 'Balance Report'

	from_date = fields.Date(string="Start Date")	
	to_date = fields.Date(string="End Date")
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)
	cost_center_id = fields.Many2one('orchid.account.cost.center', string="Cost Center")
	cost_center = fields.Boolean(string="Cost Center Wise", default=False)

	# @api.model
	# def default_get(self, fields):
	# 	res = super(OrchidAccountBalanceSheetReport, self).default_get(fields)
	# 	cost_center_ids = self.env['orchid.account.cost.center'].search([('include_pl','=',True)]).sorted('id')
	# 	values = {
	# 		'cost_center_ids':[(6,0,cost_center_ids.ids)],
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
			# self.year_validation()
	
	# @api.onchange('to_date')
	# def year_validation(self):
	# 	if self.from_date and self.to_date:
	# 		date_to = datetime.strptime(str(self.to_date),'%Y-%m-%d')
	# 		date_from = datetime.strptime(str(self.from_date),'%Y-%m-%d')
	# 		if date_from and date_to:
	# 			if date_from.year!=date_to.year:
	# 				raise UserError(_("Please select dates of same year !!!"))

	def generate_excel(self):

		title="Balance Sheet"
		report_name = "BalanceSheet"
		filename =str(report_name)+'.xlsx'
		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		sheet= workbook.add_worksheet(str(report_name))
		style_main_header=workbook.add_format({'bold':True,'font_size':15,'align':'center','valign':'vcenter','bg_color':'#D7E4BC','border':0})
		style_sub_header=workbook.add_format({'bold':True,'bg_color':'#cccccc','border':0})
		style_detail_header=workbook.add_format({'bold':True,'border':0})
		style_balance=workbook.add_format({'bold':False,'num_format':'#,##0.00'})
		style_balance1=workbook.add_format({'bold':False,'align':'right'})
		style_total=workbook.add_format({'bold':True,'num_format':'#,##0.00','bg_color':'#cccccc'})
		style_total_text=workbook.add_format({'bold':True,'bg_color':'#cccccc'})
		style_total_text1=workbook.add_format({'bold':True,'bg_color':'#cccccc'})
		style_total1=workbook.add_format({'bold':True,'num_format':'#,##0.00','bg_color':'#cccccc'})
		style_total2=workbook.add_format({'bold':False,'align':'right','bg_color':'#cccccc'})
		style_total3=workbook.add_format({'bold':False,'align':'right','bg_color':'#cccccc'})
		sheet.set_column('A:A',50)
		sheet.set_column('B:B',15,style_balance)
		sheet.set_column('C:C',15,style_balance)
		sheet.set_column('D:D',15,style_balance)
		row = 0
		col =0
		headings = ['Name','Debit','Credit','Balance']
		col_merge = len(headings)
		row_merge=row
		sheet.merge_range(row,col,row,col_merge,title,style_main_header)
		row = row+1
		col=0
		if self.from_date:
			from_date =datetime.strptime(str(self.from_date),'%Y-%m-%d').strftime('%d-%m-%Y')
			date_from='Date From: '+str(from_date)
			sheet.write(row,col,date_from,style_detail_header)
			row = row+1

		if self.to_date:
			to_date =datetime.strptime(str(self.to_date),'%Y-%m-%d').strftime('%d-%m-%Y')
			date_to='Date To: '+str(to_date)
			sheet.write(row,col,date_to,style_detail_header)
			row = row+1

		if self.cost_center and self.cost_center_id:
			cost_center='Cost Center: '+str(self.cost_center_id.name)
			sheet.write(row,col,cost_center,style_detail_header)
		row = row+1
		col = 0
		for header in headings:
			sheet.write(row,col,header,style_sub_header)
			col = col+1
		row =row+1
		if self.to_date:
			to_date=self.to_date
		else:
			to_date=fields.Date.today()
		# print("to******",to_date,type(to_date))
		# print("to******",self.from_date,type(self.from_date))



		for group in self.env['od.report.template'].search([('report_value','=','balance_sheet')], order='sequence asc'):
			row = row+1
			group_row = row
			col=0
			if group.display_details == 'accounts':
				sheet.write(row,col,group.name,style_total_text1)
				debit_sum=0
				credit_sum=0
				balance_sum=0
				for account in group.account_account_ids:
					account_row_total = 0
					col=0
					row=row+1
					sheet.write(row,col,account.name.display_name)
					where_qry = ''' WHERE am.company_id IN %s AND aml.account_id IN %s AND aa.account_type=%s AND aml.date<=%s AND am.state='posted' '''
					params=[tuple([self.company_id.id]),tuple([account.name.id]),account.name.account_type,str(to_date)]
					# params=[tuple(self.company_id.id)]
					if self.from_date:
						where_qry += " AND aml.date >=%s"
						params+=[str(self.from_date)]
					if self.cost_center and self.cost_center_id:
						where_qry += " AND aml.orchid_cc_id=%s"
						params+=[tuple([self.cost_center_id.id])]
					# account_balance_qry = ''' SELECT 
					# 							CASE WHEN aa.account_type in ('expense','expense_depreciation','expense_direct_cost') 
					# 							THEN sum(COALESCE((aml.balance*-1),0)) 
					# 							ELSE (sum(COALESCE(aml.balance*-1,0))) end as balance,
					#  							CASE WHEN aml.orchid_cc_id is not null
					#  							THEN aml.orchid_cc_id 
					#  							ELSE 0 END AS cost_center_id 
					#  							FROM account_move_line aml
					#  							LEFT JOIN account_move am ON (aml.move_id=am.id)
					#  							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
					#  							WHERE am.company_id=%s AND am.state='posted' 
					#  							AND aml.account_id=%s AND aa.account_type='%s' AND aml.date >='%s' AND aml.date<='%s' 
					#  							GROUP BY aml.orchid_cc_id, aa.account_type '''%(self.company_id.id, account.name.id,account.name.account_type,self.from_date,self.to_date)
					account_balance_qry = ''' SELECT 
												sum(aml.debit) as debit,
												sum(aml.credit) as credit,
												sum(aml.debit)-sum(aml.credit) as balance
					 							FROM account_move_line aml
					 							LEFT JOIN account_move am ON (aml.move_id=am.id)
					 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
					 							 '''+where_qry+'''
					 							GROUP BY aa.id '''
					print("accc",params)
					
					print(account_balance_qry)
					self._cr.execute(account_balance_qry,params)
					account_data = self._cr.dictfetchall()
					print("account dataaaa",account_data)
					for data in account_data:
						col=col+1
						sheet.write(row,col,data['debit'])	
						col=col+1
						sheet.write(row,col,data['credit'])
						col=col+1
						sheet.write(row,col,data['balance'])
						debit_sum+=data['debit']					
						credit_sum+=data['credit']					
						balance_sum+=data['balance']					
					# row=row+1
					col=0
				col=col+1
				sheet.write(group_row,col,debit_sum,style_total1)
				col=col+1
				sheet.write(group_row,col,credit_sum,style_total1)
				col=col+1
				sheet.write(group_row,col,balance_sum,style_total1)

			if group.display_details == 'compute':
				sheet.write(row,col,group.name,style_total_text1)
				debit_sum=0
				credit_sum=0
				balance_sum=0
				group_accounts = []
				for subgroup in group.account_group_ids:
					for acc in subgroup.name.account_account_ids:
						group_accounts.append(acc.name)
				account_data = []
				for account in group_accounts:
					where_qry = ''' WHERE am.company_id IN %s AND aml.account_id IN %s AND aa.account_type=%s AND aml.date<=%s AND am.state='posted' '''
					params=[tuple([self.company_id.id]),tuple([account.id]),account.account_type,str(to_date)]
					if self.from_date:
						where_qry += " AND aml.date >=%s"
						params+=[str(self.from_date)]
					if self.cost_center and self.cost_center_id:
						where_qry += " AND aml.orchid_cc_id=%s"
						params+=[tuple([self.cost_center_id.id])]
					account_balance_qry = ''' SELECT 
												sum(aml.debit) as debit,
												sum(aml.credit) as credit,
												sum(aml.debit)-sum(aml.credit) as balance
					 							FROM account_move_line aml
					 							LEFT JOIN account_move am ON (aml.move_id=am.id)
					 							LEFT JOIN account_account aa ON (aa.id=aml.account_id)
					 							'''+where_qry+'''
					 							GROUP BY aa.id'''
					print(account_balance_qry)
					self._cr.execute(account_balance_qry,params)
					account_data = self._cr.dictfetchall()
					print("account groupppppppppp",account_data)
					for data in account_data:
						debit_sum+=data['debit']
						credit_sum+=data['credit']
						balance_sum+=data['balance']
				col=col+1
				sheet.write(row,col,debit_sum,style_total1)
				col=col+1
				sheet.write(row,col,credit_sum,style_total1)
				col=col+1
				sheet.write(row,col,balance_sum,style_total1)
				col=0
			# row = row+1

		workbook.close()
		output.seek(0)
		# excel_file = base64.encodestring(output.read())
		excel_file = base64.encodebytes(output.read())
		self.write({'excel_file':excel_file,'file_name':filename})
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.account.bs.report.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }



















