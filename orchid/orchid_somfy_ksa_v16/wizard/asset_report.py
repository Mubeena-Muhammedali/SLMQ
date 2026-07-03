# -*- encoding: utf-8 -*-
import time
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime as dt
import base64
import xlsxwriter
from io import BytesIO

class od_asset_report(models.TransientModel):
	_name = 'od.asset.report' 
	_description = 'Asset Report'

	company_id = fields.Many2one('res.company', string='Company',readonly=True,default=lambda self: self.env.user.company_id)
	# category_ids = fields.Many2many('account.asset.category',string='Asset Category')
	category_ids = fields.Many2many('account.asset',string='Asset Category')
	date_from = fields.Date('Start Date',required=True)
	date_to = fields.Date('End Date',required=True)
	od_report_level = fields.Selection([('dispose','Disposed'),('depreciation','with Depreciation'),
										('running','Running'),('running_dispose','Running & Disposed')],default='running',string='Report')
	excel_file = fields.Binary(string='Download Report Excel',readonly=True)
	file_name = fields.Char(string='Excel File',readonly=True)

	@api.onchange('date_from')
	def last_day_of_month(self):
		for wiz in self:
			if wiz.date_from:
				any_day=wiz.date_from
				next_month = any_day.replace(day=28) + dt.timedelta(days=4)  # this will never fail
				date_to=next_month - dt.timedelta(days=next_month.day)
				wiz.date_to=date_to


	def build_filter(self):
		data = self.read(['date_from', 'date_to', 'category_ids', 'company_id','od_report_level'])[0]
		
		if not data.get('category_ids'):
			# category_ids = self.env['account.asset.category'].search([('company_id','=',data.get('company_id')[0])])
			category_ids = self.env['account.asset'].search([('asset_type','=','purchase'),('state','=','model'),('company_id','=',data.get('company_id')[0])])
			data['category_ids'] = category_ids.ids
		if not data.get('date_from') or not data.get('date_to') or data.get('date_from') > data.get('date_to'):
			raise UserError(('Date field should be proper'))
		return data

	def print_report(self):        
		data = self.build_filter()
		return self.env.ref('orchid_somfy_ksa_v16.action_report_asset_statement').with_context(landscape=True).report_action(self, data=data)

	def print_excel(self):
		model = self.env.context.get('active_model')
		data = self.build_filter()
		report_asset = self.env['report.orchid_somfy_ksa_v16.report_asset_statement']
		
		filename ='CategoryAssetReport.xlsx'
		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		sheet= workbook.add_worksheet('CategoryAssetReport')
		title_format = workbook.add_format({
			'bold': True,
			'align': 'center',
			'fg_color': '#1E90FF',
			'border': 0})
		categ_style = workbook.add_format({
			'bold': True,
			'align': 'left',
			'border': 0})
		code_style = workbook.add_format({
			'align': 'center',
			'border': 0})
		subtitle_style = workbook.add_format({
			'bold': True,
			'align': 'center',
			'fg_color': '#ecf2e9',
			'border': 0})
		total_style =  workbook.add_format({
			'bold': True,
			'align': 'left',
			'fg_color': '#ecf2e9',
			'border': 0})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'})
		row_num_style1 = workbook.add_format({
			'num_format': '#,##0.00',
			'fg_color': '#ecf2e9',
			'bold': True})
		
		report_obj = self.env['report.orchid_somfy_ksa_v16.report_asset_statement']
		
		header = 'CATEGORY ASSET REPORT ' + str(self.date_from) + ' To ' +str(self.date_to)
		row=0
		col = 0
		net_open_bal_cost=0
		net_addition_cost=0
		net_deletion_cost=0
		net_balance_cost=0
		net_open_bal_depr=0
		net_addition_depr=0
		net_deletion_depr=0
		net_balance_depr=0
		net_nbv=0
		row_merge = row
		col_merge = col+11
		sheet.set_column('A:A',20)
		sheet.set_column('B:B',50)
		# sheet.set_column('C:K',20)
		sheet.set_column('C:L',20)
		sheet.merge_range(row,col,row_merge,col_merge,header,title_format)

		# categ report
		for category_id in data['category_ids'] :
			col=0
			row = row +2
			categoryname = report_obj.get_category_by_id(category_id)
			assets = report_obj.get_asset_by_category(category_id, data)
			if assets:
				sheet.write(row,col,categoryname,categ_style)
				row = row+1
				row_merge=row
				# col =2
				col =3
				col_merge =col+3
				sheet.merge_range(row,col,row_merge,col_merge,'ASSET',subtitle_style)
				col=col+4
				col_merge =col+3
				sheet.merge_range(row,col,row_merge,col_merge,'DEPRECIATION',subtitle_style)
				col=col+4
				sheet.write(row,col,'NBV',subtitle_style)
				row=row+1
				col=1
				sheet.write(row,col,'ASSEST DEPRECIATION',subtitle_style)
				col=col+1
				sheet.write(row,col,'PURCHASE DATE',subtitle_style)
				col=col+1
				sheet.write(row,col,'OPENING BALANCE',subtitle_style)
				col=col+1
				sheet.write(row,col,'ADDITION',subtitle_style)
				col=col+1
				sheet.write(row,col,'DELETION',subtitle_style)
				col=col+1
				sheet.write(row,col,'BALANCE',subtitle_style)
				col=col+1
				sheet.write(row,col,'OPENING BALANCE',subtitle_style)
				col=col+1
				sheet.write(row,col,'ADDITION',subtitle_style)
				col=col+1
				sheet.write(row,col,'DELETION',subtitle_style)
				col=col+1
				sheet.write(row,col,'BALANCE',subtitle_style)
				
				tot_open_bal_cost = 0
				tot_addition_cost=0
				tot_deletion_cost=0
				tot_balance_cost=0
				tot_open_bal_depr=0
				tot_addition_depr=0
				tot_deletion_depr=0
				tot_balance_depr=0
				tot_nbv=0
				for assest in assets:
					row=row+1
					col=0
					sl_no=assest.x_studio_code

					sheet.write(row,col,sl_no)

					col=col+1
					sheet.write(row,col,assest.name)
					col=col+1
					sheet.write(row,col,str(assest.x_studio_purchase_date))

					if not (assest.x_studio_purchase_date >= data['date_from'] and assest.x_studio_purchase_date <= data['date_to']):
						open_bal_cost=assest.x_studio_purchase_value
						addition_cost =0.00
						tot_open_bal_cost=tot_open_bal_cost+open_bal_cost
					else:
						open_bal_cost=0.00
						addition_cost =assest.x_studio_purchase_value
						tot_addition_cost=tot_addition_cost+addition_cost
					deletion_cost=0.00
					tot_deletion_cost = tot_deletion_cost+deletion_cost
					balance_cost = open_bal_cost+addition_cost
					tot_balance_cost = tot_balance_cost+balance_cost
					open_bal_depr = report_obj.get_open_bal_depr(assest,data)
					tot_open_bal_depr = tot_open_bal_depr+open_bal_depr

					addition_depr = report_obj.get_depreciation_values(assest,data,open_bal_depr)
					tot_addition_depr = tot_addition_depr+addition_depr
					deletion_depr=0
					tot_deletion_depr = tot_deletion_depr+deletion_depr
					balance_depr = open_bal_depr+addition_depr
					tot_balance_depr = tot_balance_depr+balance_depr

					nbv = balance_cost-balance_depr
					tot_nbv = tot_nbv+nbv
					col=col+1
					sheet.write(row,col,open_bal_cost,row_num_style)
					col=col+1
					sheet.write(row,col,addition_cost,row_num_style)
					col=col+1
					sheet.write(row,col,deletion_cost,row_num_style)
					col=col+1
					sheet.write(row,col,balance_cost,row_num_style)
					col=col+1
					sheet.write(row,col,open_bal_depr,row_num_style)
					col=col+1
					sheet.write(row,col,addition_depr,row_num_style)
					col=col+1
					sheet.write(row,col,deletion_depr,row_num_style)
					col=col+1
					sheet.write(row,col,balance_depr,row_num_style)
					col=col+1
					sheet.write(row,col,nbv,row_num_style)

				row = row+1
				col =0
				# col_merge=col+1
				col_merge=col+2
				row_merge=row
				sheet.merge_range(row,col,row_merge,col_merge,str(categoryname)+' TOTAL',total_style)
				# col=col+2
				col=col+3
				sheet.write(row,col,tot_open_bal_cost,row_num_style1)
				col=col+1
				sheet.write(row,col,tot_addition_cost,row_num_style1)
				col=col+1
				sheet.write(row,col,tot_deletion_cost,row_num_style1)
				col=col+1
				sheet.write(row,col,tot_balance_cost,row_num_style1)
				col=col+1
				sheet.write(row,col,tot_open_bal_depr,row_num_style1)
				col=col+1
				sheet.write(row,col,tot_addition_depr,row_num_style1)
				col=col+1
				sheet.write(row,col,tot_deletion_depr,row_num_style1)
				col=col+1
				sheet.write(row,col,tot_balance_depr,row_num_style1)
				col=col+1
				sheet.write(row,col,tot_nbv,row_num_style1)


				net_open_bal_cost=net_open_bal_cost+tot_open_bal_cost
				net_addition_cost=net_addition_cost+tot_addition_cost
				net_deletion_cost=net_deletion_cost+tot_deletion_cost
				net_balance_cost=net_balance_cost+tot_balance_cost
				net_open_bal_depr=net_balance_depr+tot_open_bal_depr
				net_addition_depr=net_addition_depr+tot_addition_depr
				net_deletion_depr=net_deletion_depr+tot_deletion_depr
				net_balance_depr=net_balance_depr+tot_balance_depr
				net_nbv=net_nbv+tot_nbv


		row = row+1
		col =0
		# col_merge=col+1
		col_merge=col+2
		row_merge=row
		sheet.merge_range(row,col,row_merge,col_merge,'GRAND TOTAL',total_style)
		# col=col+2
		col=col+3
		sheet.write(row,col,net_open_bal_cost,row_num_style1)
		col=col+1
		sheet.write(row,col,net_addition_cost,row_num_style1)
		col=col+1
		sheet.write(row,col,net_deletion_cost,row_num_style1)
		col=col+1
		sheet.write(row,col,net_balance_cost,row_num_style1)
		col=col+1
		sheet.write(row,col,net_open_bal_depr,row_num_style1)
		col=col+1
		sheet.write(row,col,net_addition_depr,row_num_style1)
		col=col+1
		sheet.write(row,col,net_deletion_depr,row_num_style1)
		col=col+1
		sheet.write(row,col,net_balance_depr,row_num_style1)
		col=col+1
		sheet.write(row,col,net_nbv,row_num_style1)

		workbook.close()
		output.seek(0)
		excel_file = base64.encodebytes(output.read())
		self.excel_file = excel_file
		self.file_name =filename
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.asset.report',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }



	