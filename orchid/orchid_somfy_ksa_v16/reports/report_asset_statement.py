# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models
from datetime import datetime


class ReportAssetStatement(models.AbstractModel):
	_name = 'report.orchid_somfy_ksa_v16.report_asset_statement'


	@api.model
	def _get_report_values(self, docids, data=None):
		model = self.env.context.get('active_model')
		docs = self.env[model].browse(self.env.context.get('active_id'))
		date = datetime.now()
		domain=[('x_studio_purchase_date','<=',data['date_to'])]

		if data['od_report_level']=='dispose':
			domain+=[('state','=','close')]
	
		if data['od_report_level']=='running':
			domain+=[('state','!=','close')]

		asset_details=self.env['account.asset'].search(domain)
		category_ls=asset_details
		
		if data['od_report_level']=='depreciation':
			category_ls=[]
			for ass in asset_details:
				if not (ass.state=='close') or (ass.state=='close' and ass.value>0):
					category_ls.append(ass)
		data['date_from'] = datetime.strptime(data.get('date_from'), '%Y-%m-%d').date()
		data['date_to'] = datetime.strptime(data.get('date_to'), '%Y-%m-%d').date()
		docargs = {
			'doc_ids': self.ids,
			'doc_model': model,
			'docs': docs,
			'filters':data,
			'get_category_by_id':self.get_category_by_id,
			# 'get_cost_center_by_id':self.get_cost_center_by_id,
			'get_category_ids':self.get_category_ids,
			'get_asset_by_category':self.get_asset_by_category,
			'get_open_bal_depr':self.get_open_bal_depr,
			'get_depreciation_values':self.get_depreciation_values,
			'date':date,
			# 'get_category_by_cost_center':self.get_category_by_cost_center,
			# 'currency_id':self.env.ref('base.EUR'),
			'currency_id':self.env.company.currency_id,
			'company':self.env.user.company_id
		}
		return docargs


	def get_category_by_id(self,category_id):
		if category_id:
			# return self.env['account.asset.category'].browse(category_id).name
			return self.env['account.asset'].browse(category_id).name
		return {}

	def get_category_ids(self,vals):
		if vals:
			result=[]
			for line in vals:
				print("vvv",vals)
				# cat_name=self.env['account.asset.category'].browse(line).name
				cat_name=self.env['account.asset'].browse(line).name
				result.append(cat_name)
		result=','.join(result)
		print("result",result)
		return result


	def get_asset_by_category(self,category_id,filters):
		domain=[('model_id','=',category_id),('x_studio_purchase_date','<=',filters.get('date_to'))]
		
		if filters.get('od_report_level')=='dispose':
			domain+=[('state','=','close')]
		
		if filters.get('od_report_level')=='running':
			domain+=[('state','!=','close')]
		
		asset_obj = self.env['account.asset']
		asset_ids = asset_obj.search(domain, order='x_studio_purchase_date')
		category_ls = asset_ids
		
		if filters.get('od_report_level')=='depreciation':
			category_ls=[]
			for ass in asset_ids:
				if not (ass.state=='close') or (ass.state=='close' and ass.value>0):
					category_ls.append(ass)

		return category_ls

	def get_open_bal_depr(self,asset,filters):
		open_bal_depr=0
		asset_obj = self.env['account.asset'].search([('id','=',asset.id)])
		if asset_obj.x_studio_depreciation==asset_obj.x_studio_purchase_value:
			open_bal_depr=asset_obj.x_studio_depreciation
		else:
			if str(filters['date_from']) >= '2018-01-01':
				if asset_obj.x_studio_purchase_date >=filters['date_from'] and asset_obj.x_studio_purchase_date <= filters['date_to']:
					open_bal_depr=0
				else:
					open_bal_depr = asset_obj.x_studio_depreciation
					# asset_move_line_pool = self.env['account.asset.depreciation.line']
					asset_move_line_pool = self.env['account.move']
					# line_ids = asset_move_line_pool.search([('depreciation_date','<',filters.get('date_from')),('asset_id','=',asset.id)])
					line_ids = asset_move_line_pool.search([('date','<',filters.get('date_from')),('asset_id','=',asset.id)])
					# if asset_obj.first_depreciation_manual_date and filters['date_from']>=asset_obj.first_depreciation_manual_date:
					if asset_obj.acquisition_date and filters['date_from']>=asset_obj.acquisition_date:
						open_bal_depr+=asset_obj.salvage_value
					for val in line_ids:
						# if val.move_check:
						if val.state!='draft':
							# open_bal_depr = open_bal_depr + val.amount
							open_bal_depr = open_bal_depr + abs(val.depreciation_value)
			else:
				open_bal_depr=asset_obj.x_studio_depreciation
		print("lllll",open_bal_depr,asset_obj.name)
				
		return open_bal_depr


	def get_depreciation_values(self,asset,filters,open_bal_depr):
		asset_obj = self.env['account.asset'].search([('id','=',asset.id)])
		depreciation_value=0
		
		if asset_obj.x_studio_depreciation==asset_obj.x_studio_purchase_value:
			depreciation_value=0
		
		else:
			# asset_move_line_pool = self.env['account.asset.depreciation.line']
			asset_move_line_pool = self.env['account.move']
			# line_ids = asset_move_line_pool.search([('depreciation_date','>=',filters.get('date_from')),('depreciation_date','<=',filters.get('date_to')),('asset_id','=',asset.id)])
			line_ids = asset_move_line_pool.search([('date','>=',filters.get('date_from')),('date','<=',filters.get('date_to')),('asset_id','=',asset.id)])
			for val in line_ids:
				# if val.move_check:
				if val.state!='draft':
					# depreciation_value = depreciation_value + val.amount
					depreciation_value = depreciation_value + abs(val.depreciation_value)
			# if depreciation_value > asset_obj.value:
			# 	depreciation_value = asset_obj.value
			if depreciation_value > asset_obj.x_studio_purchase_value:
				depreciation_value = asset_obj.x_studio_purchase_value
					
		return depreciation_value

	