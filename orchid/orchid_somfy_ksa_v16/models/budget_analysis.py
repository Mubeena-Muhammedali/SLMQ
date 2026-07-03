from odoo import models, fields, api,_
from datetime import  timedelta, tzinfo, time, date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from io import BytesIO
import base64
import pandas as pd

class OrchidBudgetAnalysis(models.Model):
	_inherit = 'orchid.budget.analysis'


	def fetch_budget_data(self):
		if self.od_date_start and self.od_date_end:
			# find budget
			budget_id = self.env['orchid.budget'].search([('company_id','=',self.company_id.id),('od_date_start','<=',self.od_date_start),('od_date_end','>=',self.od_date_end),('od_state','=','approved')])			
			if not budget_id:
				raise UserError(_("No approved budget set for this period!!!"))	
			if len(budget_id)>1:
				budget_names = ""
				for b in budget_id:
					budget_names+=b.name+","
				raise UserError(_("More than 1 approved budgets found!! '%s' ")%(budget_names))
			line_ls = []
			if self.od_budget_line:
				self.od_budget_line.unlink()
			for bl in budget_id.od_budget_line_mnth:
				budget_amount = 0
				planned_amount = 0
				actual_amount = 0
				last_year_actual_amount = 0
				variation_amount = 0
				if self.od_date_end.month == 1:
					budget_amount = bl.od_month1
					planned_amount = bl.od_month1
				if self.od_date_end.month == 2:
					budget_amount = bl.od_month2
					planned_amount = bl.od_month1+bl.od_month2
				if self.od_date_end.month == 3:
					budget_amount = bl.od_month3
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3
				if self.od_date_end.month == 4:
					budget_amount = bl.od_month3
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3+bl.od_month4
					print("planned_amountplanned_amount",planned_amount)
				if self.od_date_end.month == 5:
					budget_amount = bl.od_month5
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3+bl.od_month4+bl.od_month5
				if self.od_date_end.month == 6:
					budget_amount = bl.od_month6
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3+bl.od_month4+bl.od_month5+bl.od_month6
				if self.od_date_end.month == 7:
					budget_amount = bl.od_month6
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3+bl.od_month4+bl.od_month5+bl.od_month6+bil.od_month7
				if self.od_date_end.month == 8:
					budget_amount = bl.od_month8
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3+bl.od_month4+bl.od_month5+bl.od_month6+bil.od_month7+bil.od_month8
				if self.od_date_end.month == 9:
					budget_amount = bl.od_month9
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3+bl.od_month4+bl.od_month5+bl.od_month6+bil.od_month7+bil.od_month8+bil.od_month9
				if self.od_date_end.month == 10:
					budget_amount = bl.od_month10
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3+bl.od_month4+bl.od_month5+bl.od_month6+bil.od_month7+bil.od_month8+bil.od_month9+bil.od_month10
				if self.od_date_end.month == 11:
					budget_amount = bl.od_month11
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3+bl.od_month4+bl.od_month5+bl.od_month6+bil.od_month7+bil.od_month8+bil.od_month9+bil.od_month10+bil.od_month11
				if self.od_date_end.month == 12:
					budget_amount = bl.od_month12
					planned_amount = bl.od_month1+bl.od_month2+bl.od_month3+bl.od_month4+bl.od_month5+bl.od_month6+bil.od_month7+bil.od_month8+bil.od_month9+bil.od_month10+bil.od_month11+bil.od_month12
				
				year_start_date = fields.Date.today()
				year_start_date = year_start_date.replace(day=1,month=1)
				account_ids = bl.account_id
				if bl.report_template_id:
					account_ids = bl.report_template_id.account_account_ids.mapped('name')
				month_params = (tuple(account_ids.ids),year_start_date,self.od_date_end)
				print("monthh",month_params)
				actual_amount_qry = """SELECT COALESCE(sum(aml.debit-aml.credit),0) as actual_amount
										FROM account_move_line aml
										LEFT JOIN account_move am ON am.id = aml.move_id
										WHERE account_id IN %s AND am.state='posted' AND aml.date>=%s AND aml.date<=%s """
				self._cr.execute(actual_amount_qry,month_params)
				results = self._cr.dictfetchall()
				for result in results:
					actual_amount+=result['actual_amount']
				variation_amount = planned_amount - abs(actual_amount)

				last_year_date_end = self.od_date_end- relativedelta(years=1)
				last_year_date_start= last_year_date_end.replace(day=1,month=1)

				year_params = (tuple(account_ids.ids),last_year_date_start,last_year_date_end)
				last_year_actual_amount_qry = """SELECT COALESCE(sum(aml.debit-aml.credit),0) as actual_amount
										FROM account_move_line aml
										LEFT JOIN account_move am ON am.id = aml.move_id
										WHERE account_id IN %s AND am.state='posted' AND aml.date>=%s AND aml.date<=%s """
				self._cr.execute(last_year_actual_amount_qry,year_params)
				last_results = self._cr.dictfetchall()
				for res in last_results:
					last_year_actual_amount+=res['actual_amount']
				name = False
				if bl.account_id:
					name=bl.account_id.display_name
				if bl.report_template_id:
					name=bl.report_template_id.name
				vals = {
				'account_id':bl.account_id.id if bl.account_id else False,
				'report_template_id':bl.report_template_id.id if bl.report_template_id else False,
				'name':name,
				'budget_amount':bl.od_month1,
				'planned_amount':planned_amount,
				'actual_amount':actual_amount,
				'variation_amount':variation_amount,
				'last_year_actual_amount':last_year_actual_amount,
				}
				line_ls.append((0,0,vals))
			self.od_budget_id = budget_id.id
			self.od_budget_line = line_ls

	def button_excel(self):
		result = []
		for line in self.od_budget_line:
			vals = {
			'Code':line.account_id.code if line.account_id else "",
			'Account/Group':line.account_id.name if line.account_id else line.report_template_id.name,
			'Budget':line.budget_amount,
			'Planned Amount':line.planned_amount,
			'Actual Amount':line.actual_amount,
			'Variation Amount':line.variation_amount,
			'Remarks':line.od_remarks or "",
			}
			result.append(vals)
		header_rage ='A1:G1'
		dataframe= pd.DataFrame(result,columns=["Code","Account/Group","Budget","Planned Amount","Actual Amount","Variation Amount","Remarks"])
		filename ='BudgetAnalysis.xlsx'
		from_date =datetime.strptime(str(self.od_date_start),'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(str(self.od_date_end),'%Y-%m-%d').strftime('%d-%m-%Y')
		title="Budget Analysis- "+ from_date + " "+"to " +to_date
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
		worksheet.set_column('A:A',20)
		worksheet.set_column('B:B',40)
		worksheet.set_column('C:C',20,row_num_style)
		worksheet.set_column('D:D',20,row_num_style)
		worksheet.set_column('E:E',20,row_num_style)
		worksheet.set_column('F:F',20,row_num_style)
		row=len(dataframe.index)+3
		col = 0
		worksheet.write(row,col,"Total",tot_format)
		col=col+2
		total_ls = ["Budget","Planned Amount","Actual Amount","Variation Amount"]
		for column in dataframe[total_ls]:
			total=dataframe[column].sum()
			print("total",total)
			worksheet.write(row,col,total,tot_format1)
			col=col+1
		writer.close()
		excel_file = base64.encodebytes(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()


class OrchidBudgetAnalysisLines(models.Model):
	_inherit = 'orchid.budget.analysis.line'

	report_template_id=fields.Many2one('od.report.template',string='Report Template')
	name = fields.Char(string="Account/Group")

	def view_budget_line(self):
		domain = [('company_id','=',self.company_id.id),('od_state','=','approved'),('od_date_start','<=',self.od_date_start),('od_date_end','>=',self.od_date_end)]
		if self.report_template_id:
			domain.append(('report_template_id','=',self.report_template_id.id))
		elif self.account_id:
			domain.append(('account_id','=',self.account_id.id))
		budget_line_ids = self.env['orchid.budget.line'].search(domain)
		if budget_line_ids:
			return {
			  'view_type': 'tree',
			  "view_mode": 'tree',
			  'res_model': 'orchid.budget.line',
			  'domain': [('id','in',budget_line_ids.ids)],
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }
