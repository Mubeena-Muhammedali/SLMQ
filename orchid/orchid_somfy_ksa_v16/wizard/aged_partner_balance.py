# -*- coding: utf-8 -*-
from odoo import fields, models,api,_
from odoo.exceptions import UserError
# import xlwt
import xlsxwriter
from io import BytesIO
import base64
from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

class AccountAgedTrialBalance(models.TransientModel):

	_inherit = 'account.aged.trial.balance'

	od_with_currency = fields.Boolean(string="With FC", default=True)
	period_length = fields.Integer(string='Period Length (days)', required=True, default=90)

	@api.model
	def default_get(self, fields):
		res = super(AccountAgedTrialBalance, self).default_get(fields)
		account = self.env['account.account'].search([('id','=',2)])
		acc_ids = []
		for acc in account:
			acc_ids.append(acc and acc.id)
		values = {
			'account_ids':[(6,0,acc_ids)],
		}
		res.update(values)
		return res

	def get_header_details(self,data):
		period1 = str(data['form']['4']['name'])
		period2 = str(data['form']['3']['name'])
		period3 = str(data['form']['2']['name'])
		period4 = str(data['form']['1']['name'])
		period5 = str(data['form']['0']['name'])
		header = ['CODE','PARTNERS','SALESMAN','PAYMENT BEHAVIOUR','PAYMENT TERMS','CREDIT LIMIT','INSURED CREDIT LIMIT','TOTAL','NOT DUE','DUE AMOUNT',period1,period2,period3,period4,period5,'COMPUTED PROVISION']
		return header 
	def _print_report(self, data):
		res = super(AccountAgedTrialBalance,self)._print_report(data)
		data['form']['od_with_currency'] = self.od_with_currency or False
		return res
	def get_data_for_xls(self):
		data=super(AccountAgedTrialBalance, self).get_data_for_xls()
		data['form']['od_with_currency']=self.od_with_currency or False
		return data

	def print_excel(self):
		filename= 'PartnerAging.xlsx'
		data = self.get_data_for_xls()
		header = self.get_header_details(data)
		
		account_type = ['receivable']
		date_from = data['form']['date_from']
		target_move = data['form']['target_move']
		if data['form']['result_selection'] == 'customer':
			account_type = ['receivable']
			partner_type = 'RECEIVABLE ACCOUNTS'
		elif data['form']['result_selection'] == 'supplier':
			account_type = ['payable']
			partner_type = 'PAYABLE ACCOUNTS'
		else:
			account_type = ['payable', 'receivable']
			partner_type = 'RECEIVABLE AND PAYABLE ACCOUNTS'
		od_search_cond = '''  '''
		if self.partner_ids or self.account_ids or self.journal_ids:
			od_move_lines = self.get_move_line_ids()
			if not od_move_lines:
				raise UserError(_("no data for selected search codition"))	
			od_move_lines = self.env['account.move.line'].browse(od_move_lines)
			if od_move_lines:
				if len(od_move_lines) ==1:
					od_search_cond = od_search_cond + ''' AND l.id ='''+str(od_move_lines.id)
				else:
					od_search_cond = od_search_cond + ''' AND l.id in '''+str(tuple(od_move_lines.ids))
		od_with_currency = data['form']['od_with_currency']
		movelines, total, dummy = self.env['report.account.report_agedpartnerbalance']._get_partner_move_lines(account_type, date_from, target_move, data['form']['period_length'], od_search_cond,self.od_include_reconciled,self.od_include_not_due,od_with_currency)
		if not movelines and not total :
			raise UserError(_("no data for selected search codition"))	
		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		sheet= workbook.add_worksheet('Aging Report Report')
		style=workbook.add_format({'bold':True,'font_size':15,'align':'center','valign':'vcenter','fg_color': '#D7E4BC','border':0})
		row = 0
		col =0
		style2=workbook.add_format({'bold':True,'align':'left','valign':'vcenter','font_size':10})
		style3=workbook.add_format({'bold':True,'align':'center','valign':'vcenter','bg_color':'#ecf2e9','font_size':10})
		style4=workbook.add_format({'bold':False,'num_format':'#,##0.00','font_size':10})
		style5=workbook.add_format({'bold':True,'align':'right','valign':'vcenter','font_size':10,'num_format':'#,##0.00'})

		
		title="AGED PARTNER BALANCE"
		row_merge=row
		col_merge=col+15
		sheet.set_row(row,25)
		sheet.merge_range(row,col,row,col_merge,title,style)
		sheet.set_column('A:A',12)
		sheet.set_column('B:B',50)
		sheet.set_column('C:C',25)
		sheet.set_column('D:D',25)
		sheet.set_column('E:E',25)
		sheet.set_column('F:F',25)
		sheet.set_column('G:G',25)
		sheet.set_column('H:H',25)
		sheet.set_column('I:I',25)
		sheet.set_column('J:J',25)
		sheet.set_column('K:K',25)
		sheet.set_column('L:L',25)
		sheet.set_column('M:M',25)
		sheet.set_column('N:N',25)
		sheet.set_column('O:O',25)
		sheet.set_column('P:P',25)

		col=0
		row=row+1
		sheet.write(row,col,'START DATE:',style2)
		col=col+1
		sheet.write(row,col,datetime.strptime(date_from,'%Y-%m-%d').strftime('%d-%m-%Y'),style2)
		col=0
		row=row+1
		sheet.write(row,col,'PERIOD LENGTH (DAYS):',style2)
		col=col+1
		sheet.write(row,col,data['form']['period_length'],style2)
		col=0
		row=row+1
		sheet.write(row,col,"PARTNER'S:",style2)
		col=col+1
		sheet.write(row,col,partner_type,style2)
		col=0
		row=row+1
		sheet.write(row,col,"TARGET MOVES:",style2)
		col=col+1
		if target_move=='all':
			target_move_name='ALL ENTRIES'
		else:
			target_move_name='All POSTED ENTRIES'
		sheet.write(row,col,target_move_name,style2)
		row = row+1
		for index,data in enumerate(header):
			sheet.write(row,index,data,style3)
		col=0
		row=row+1
		sheet.write(row,col,'ACCOUNT TOTAL',style2)
		# col=col+3
		col=col+5
		sheet.write(row,col,total[9],style5)
		col=col+1
		sheet.write(row,col,total[10],style5)
		col=col+1
		sheet.write(row,col,total[5],style5)
		col=col+1
		sheet.write(row,col,total[6],style5)
		col=col+1
		sheet.write(row,col,total[7],style5)
		col=col+1
		sheet.write(row,col,total[4],style5)
		col=col+1
		sheet.write(row,col,total[3],style5)
		col=col+1
		sheet.write(row,col,total[2],style5)
		col=col+1
		sheet.write(row,col,total[1],style5)
		col=col+1
		sheet.write(row,col,total[0],style5)
		col=col+1
		sheet.write(row,col,total[8],style5)
		
		col=0
		row=row+1
		for index,data in enumerate(movelines):
			code = data.get('code')
			sheet.write(index+row,col,code)
			name = data.get('name')
			sheet.write(index+row,col+1,name)
			sales_man = data.get('sales_man') or " "
			sheet.write(index+row,col+2,sales_man)
			trust = data.get('trust')
			sheet.write(index+row,col+3,trust)
			payment_term = data.get('payment_term') or " "
			sheet.write(index+row,col+4,payment_term)
			credit_limit = data.get('credit_limit')
			sheet.write(index+row,col+5,credit_limit,style4)
			insured_credit_limit = data.get('insured_credit_limit')
			sheet.write(index+row,col+6,insured_credit_limit,style4)

			total = data.get('total')
			sheet.write(index+row,col+7,total,style4)

			not_due = data.get('direction')
			sheet.write(index+row,col+8,not_due,style4)

			due_amt = data.get('due_amt')
			sheet.write(index+row,col+9,due_amt,style4)
			period3 = data.get('4')
			sheet.write(index+row,col+10,period3,style4)
			
			period4 = data.get('3')
			sheet.write(index+row,col+11,period4,style4)
			
			period5 = data.get('2')
			sheet.write(index+row,col+12,period5,style4)
			
			period6 = data.get('1')
			sheet.write(index+row,col+13,period6,style4)
			
			
			period7 = data.get('0')
			sheet.write(index+row,col+14,period7,style4)
			
			# if trust == 'Doubtful':
			provision_value = data.get('provision')
			# else:
			# 	provision_value = 0
			sheet.write(index+row,col+15,provision_value,style4)
			
		workbook.close()
		output.seek(0)
		excel_file = base64.encodestring(output.read())
		self.excel_file = excel_file
		self.file_name =filename
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'account.aged.trial.balance',
			  'res_id': self.id,
			  'type': 'ir.actions.do_nothing',
			  'target': 'new'
			  }

	@api.multi
	def check_report(self):
		if not self.partner_ids:
			if not self.user_has_groups('account.group_account_invoice'):
				raise UserError(_("You must define partners !!"))
		res = super(AccountAgedTrialBalance, self).check_report()
		return res
