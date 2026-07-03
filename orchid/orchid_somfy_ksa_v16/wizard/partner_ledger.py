# -*- coding: utf-8 -*-
from odoo import api,fields, models, _
from datetime import datetime
import xlsxwriter
import base64
from io import BytesIO
import time
from odoo.exceptions import UserError

class AccountPartnerLedger(models.TransientModel):
	_inherit = "account.report.partner.ledger"

	fc_currency = fields.Boolean(string='With FC Currency', default=True)

	def _print_report(self, data):
		data = self.pre_print_report(data)
		data['form'].update({'reconciled': self.reconciled, 'amount_currency': self.amount_currency,
							 'od_initial': self.od_initial, 'fc_currency': self.fc_currency})
		if data['form'].get('od_initial') and not data['form'].get('date_from'):
			raise UserError(_("You must define a Start Date"))
		records = self.env[data['model']].browse(data.get('ids', []))
		return self.env.ref('account.action_report_partnerledger').with_context(landscape=True).report_action(records, data=data)

	def print_xl_report(self):
		data = {}
		data['ids'] = self.env.context.get('active_ids', [])
		data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(['date_from','date_to','journal_ids','target_move','partner_id','reconciled','amount_currency','result_selection','fc_currency', 'od_initial'])[0]
		used_context = self._build_contexts(data)
		data['form']['used_context'] = dict(used_context, lang=self.env.context.get('lang', 'en_US'))

		date_from=self.date_from and fields.Date.from_string(self.date_from).strftime('%d/%m/%Y')  or ''
		date_to=self.date_to and fields.Date.from_string(self.date_to).strftime('%d/%m/%Y') or ''
		separator=" - " if date_from and date_to else ''
		company_id = self.env.user.company_id
		title="PARTNER LEDGER  "+str(date_from)+str(separator)+str(date_to)

		if data['form'].get('od_initial') and not data['form'].get('date_from'):
			raise UserError(_("You must define a Start Date"))
		
		val=0
		header=['DATE','JRNL','ACCOUNT','REF','DEBIT','CREDIT','BALANCE','OUTSTANDING']
		if data['form']['amount_currency']:
			header.append('Currency')
			val=1
		result=self.get_xl_values(data)
		res_data=result.get('data')
		report_obj=self.env['report.account.report_partnerledger']

		
		filename= 'PartnerLedger.xlsx'
		# workbook= xlwt.Workbook(encoding="UTF-8")
		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		# xlwt.add_palette_colour("sea_blue", 0x10)
		# workbook.set_colour_RGB(0x10,30,144,255)
		# xlwt.add_palette_colour("tint_blue", 0x11)
		# workbook.set_colour_RGB(0x11,236,242,233)
		# sheet=workbook.add_sheet('PartnerLedger',cell_overwrite_ok=True)
		sheet= workbook.add_worksheet('PartnerLedger')

		# style1=xlwt.easyxf('font:color white, bold True;align: horiz center, vert center;pattern:fore_color sea_blue,pattern solid;')
		style1=workbook.add_format({'font_color':'white','bold':True,'align':'center','valign':'vcenter','bg_color':'#1E90FF'})

		# style2=xlwt.easyxf('font:bold True;align: horiz center, vert center;pattern:fore_color tint_blue,pattern solid;')
		style2=workbook.add_format({'bold':True,'align':'center','valign':'vcenter','bg_color':'#ecf2e9','font_size':10})

		# style3=xlwt.easyxf('font:bold True;')
		# style3.num_format_str="0.00"
		style3=workbook.add_format({'bold':True,'num_format':'#,##0.00','font_size':10})

		# style4=xlwt.easyxf()
		# style4.num_format_str="0.00"
		style4=workbook.add_format({'num_format':'#,##0.00','font_size':10})

		# sheet.col(3).width=256*50
		sheet.set_column('D:D',45)
		sheet.set_column('E:E',12)
		sheet.set_column('F:F',12)
		sheet.set_column('G:G',12)
		sheet.set_column('H:H',12)


		row=0
		col=0
		row_merge=row
		col_merge=col+7+val
		# sheet.row(row).height=256*2
		sheet.set_row(row,25)

		# sheet.merge_range(row,row_merge,col,col_merge,title,style1)
		sheet.merge_range(row,col,row,col_merge,title,style1)

		row=row+1
		col=0
		# sheet.row(row).height=256*2
		sheet.set_row(row,25)

		sheet.write(row,col,'COMPANY:')
		col=col+1
		sheet.write(row,col,company_id.name)

		row=row+1
		col = 0
		sheet.write(row,col,'TARGET MOVES:')		
		target = 'ALL ENTRIES' if data['form']['target_move'] == 'all' else 'ALL POSTED ENTRIES' 
		col=col+1
		sheet.write(row,col,target)

		row=row+1
		col=0
		sheet.write(row,col,'STATUS:')
		status = 'ALL' 
		if data['form']['reconciled'] == 'rec':
			status = 'RECONCILED'
		if data['form']['reconciled'] == 'unrec':
			status = 'UNRECONCILED' 
		col=col+1
		sheet.write(row,col,status)

		for partner in result.get('partners'):
			row=row+1
			col=0
			for head in header:
				sheet.write(row,col,head,style2)
				col=col+1
				# sheet.row(row).height=256*2
				sheet.set_row(row,25)


			row=row+1
			col=0
			part_ref=str(partner.ref) + '-' + str(partner.name)
			row_merge=row
			col_merge=col+3
			# sheet.merge_range(row,row_merge,col,col_merge,part_ref,style3)
			sheet.merge_range(row,col,row,col_merge,part_ref,style3)
			col = col_merge+1
			debit_total = report_obj._sum_partner(res_data, partner, 'debit')
			sheet.write(row,col,debit_total,style3)
			total_row = row
			total_col = col
			col=col+1
			credit_total = report_obj._sum_partner(res_data, partner, 'credit')
			sheet.write(row,col,credit_total,style3)
			col=col+1
			balance_total = report_obj._sum_partner(res_data, partner, 'debit - credit')
			sheet.write(row,col,balance_total,style3)
			col=col+1
			outstanding_total = report_obj._sum_partner(res_data, partner, 'amount_residual')
			sheet.write(row,col,outstanding_total,style3)
			balance = 0
			deb_total_fc =0
			cr_total_fc =0
			balance_total_fc =0
			outstand_total_fc =0

			# for line in report_obj._lines(res_data, partner, data['form']['initial_balance']):
			for line in report_obj._lines(res_data, partner):
				if data['form']['fc_currency']:
					if data['form']['od_initial'] and (line['displayed_name'] == 'Initial Balance'):
						line['credit'] =line['credit']
						line['debit'] = line['debit']
						deb_total_fc = deb_total_fc + line['debit']
						cr_total_fc = cr_total_fc + line['credit']

					else:
						if (line['amount_currency'] >0):
							line['debit'] = abs(line['amount_currency'])
							deb_total_fc = deb_total_fc + line['debit']
						if (line['amount_currency'] <0):
							line['credit'] = abs(line['amount_currency'])
							cr_total_fc = cr_total_fc + line['credit']
						if (line['amount_currency'] == 0):
							line['credit'] = 0
							line['debit'] = 0
				
				if data['form']['amount_currency']:
					condition = (round(line['credit'],2)) !=0 or (round(line['debit'],2)) !=0 or (round(line['amount_currency']),2) !=0
				if not data['form']['amount_currency']:
					condition=round(line['credit'],2) !=0 or round(line['debit'],2) !=0
				if condition:
					col=0
					row=row+1
					sheet.write(row,col,line['date'])
					col=col+1
					sheet.write(row,col,line['code'])
					col=col+1
					sheet.write(row,col,line['a_code'])
					col=col+1
					sheet.write(row,col,line['displayed_name'])
					col=col+1
					# if data['form']['fc_currency'] and (line['debit'] !=0):
					# 	line['debit'] = abs(line['amount_currency'])
						# deb_total_fc = deb_total_fc + line['debit']

					sheet.write(row,col,line['debit'],style4)
					col=col+1
					# if data['form']['fc_currency'] and (line['credit'] !=0):
					# 	line['credit'] = abs(line['amount_currency'])
					# 	cr_total_fc = cr_total_fc + line['credit']
					sheet.write(row,col,line['credit'],style4)
					col=col+1
					if data['form']['fc_currency']:
						balance = balance +(line['debit'] - line['credit'])
						line['progress'] = balance
					sheet.write(row,col,line['progress'],style4)
					col=col+1
					if data['form']['fc_currency']:
						line['amount_residual'] = line['amount_residual_currency']
						outstand_total_fc =outstand_total_fc + line['amount_residual']
					sheet.write(row,col,line['amount_residual'],style4)
					if data['form']['amount_currency']:
						col=col+1
						currency=line['amount_currency'] or ''
						sheet.write(row,col,currency)
			balance_total_fc = balance



			if data['form']['fc_currency']:
				sheet.write(total_row,total_col,deb_total_fc,style3)
				total_col = total_col+1
				sheet.write(total_row,total_col,cr_total_fc,style3)
				total_col = total_col+1
				sheet.write(total_row,total_col,balance_total_fc,style3)
				total_col = total_col+1
				sheet.write(total_row,total_col,outstand_total_fc,style3)



		# fp = BytesIO()
		# workbook.save(fp)
		# excel_file = base64.encodestring(fp.getvalue())
		# self.excel_file = excel_file
		# self.file_name =filename
		# fp.close()
		workbook.close()
		output.seek(0)
		excel_file = base64.encodestring(output.read())
		self.excel_file = excel_file
		self.file_name =filename
		ir_model_data = self.env['ir.model.data']
		compose_form_id = ir_model_data.get_object_reference('account', 'account_report_partner_ledger_view')[1]
		return {            
		'type': 'ir.actions.act_window',            
		'view_type': 'form',            
		'view_mode': 'form',            
		'res_model': 'account.report.partner.ledger',            
		'views': [(compose_form_id, 'form')], 
		'res_id': self.id,           
		'view_id': compose_form_id,            
		'target': 'new',            
		}


	def get_xl_values(self,data):
		data['computed'] = {}
		od_partner_id = False
		if data['form'].get('partner_id'):
			od_partner_id = data['form'].get('partner_id')[0]	
			
		obj_partner = self.env['res.partner']
		query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
		data['computed']['move_state'] = ['draft', 'posted']
		
		if data['form'].get('target_move', 'all') == 'posted':
			data['computed']['move_state'] = ['posted']
		
		result_selection = data['form'].get('result_selection', 'customer')
		if result_selection == 'supplier':
			data['computed']['ACCOUNT_TYPE'] = ['payable']
		elif result_selection == 'customer':
			data['computed']['ACCOUNT_TYPE'] = ['receivable']
		else:
			data['computed']['ACCOUNT_TYPE'] = ['payable', 'receivable']

		self.env.cr.execute("""
			SELECT a.id
			FROM account_account a
			WHERE a.internal_type IN %s
			AND NOT a.deprecated""", (tuple(data['computed']['ACCOUNT_TYPE']),))
		data['computed']['account_ids'] = [a for (a,) in self.env.cr.fetchall()]
		params = [tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
		
		# if data['form']['reconciled']=='unrec':
		# 	reconcile_clause = ' AND "account_move_line".amount_residual <> 0'
		# elif data['form']['reconciled']=='rec':
		# 	reconcile_clause = ' AND "account_move_line".balance <>	 "account_move_line".amount_residual'
		# else:
		# 	reconcile_clause=""

		if data['form']['reconciled']=='unrec':
			reconcile_clause = ' AND "account_move_line".amount_residual <> 0'
			if data['form']['fc_currency']:
				reconcile_clause = ' AND "account_move_line".amount_residual_currency <> 0'
		elif data['form']['reconciled']=='rec':
			reconcile_clause = ' AND "account_move_line".balance <>	 "account_move_line".amount_residual'
		else:
			reconcile_clause=""
		
		
		if od_partner_id:
			partner_clause=' AND "account_move_line".partner_id ='+str(od_partner_id)
		else:
			partner_clause=""
		partner_ids = []

		#partners for initial balance
		init_balance = data['form'].get('od_initial')
		if init_balance:
			init_used_context = data['form'].get('used_context', {})
			init_used_context['date_to'] =False
			init_tables, init_where_clause, init_where_params = self.env['account.move.line'].with_context(init_used_context, initial_bal=True)._query_get()
			init_params = [tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + init_where_params
			init_wheres = [""]
			if init_where_clause.strip():
				init_wheres.append(init_where_clause.strip())
			init_filters = " AND ".join(init_wheres)
			filters = init_filters
			
			init_query = """
			SELECT DISTINCT "account_move_line".partner_id
			FROM """ + init_tables + """, account_account AS account, account_move AS am
			WHERE "account_move_line".partner_id IS NOT NULL
				AND "account_move_line".account_id = account.id
				AND am.id = "account_move_line".move_id
				AND am.state IN %s
				AND "account_move_line".account_id IN %s
				AND NOT account.deprecated
				""" + filters + reconcile_clause+partner_clause
			self.env.cr.execute(init_query, tuple(init_params))
			init_res = self.env.cr.dictfetchall()
			for r in init_res:
				partner_ids.append(r['partner_id'])


		query = """
			SELECT DISTINCT "account_move_line".partner_id
			FROM """ + query_get_data[0] + """, account_account AS account, account_move AS am
			WHERE "account_move_line".partner_id IS NOT NULL
				AND "account_move_line".account_id = account.id
				AND am.id = "account_move_line".move_id
				AND am.state IN %s
				AND "account_move_line".account_id IN %s
				AND NOT account.deprecated
				AND """ + query_get_data[1] + reconcile_clause+partner_clause
		self.env.cr.execute(query, tuple(params))
		
		# partner_ids = [res['partner_id'] for res in self.env.cr.dictfetchall()]
		res = self.env.cr.dictfetchall()
		for r in res:
			partner_ids.append(r['partner_id'])
		partner_ids = list(set(partner_ids))
		partners = obj_partner.browse(partner_ids)
		partners = sorted(partners, key=lambda x: (x.ref, x.name))
		vals={	'data': data,
				'partners': partners,
			}
		return vals

