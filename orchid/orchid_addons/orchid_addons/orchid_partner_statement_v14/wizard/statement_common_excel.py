# Copyright 2018 Graeme Gellatly
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from odoo import _, api, fields, models

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from odoo.tools import float_is_zero
from collections import defaultdict
import xlsxwriter
from io import BytesIO
import base64



class StatementCommon(models.AbstractModel):

	_inherit = "statement.common.wizard"

	excel_file = fields.Binary(string='Excel Report')
	file_name = fields.Char(string='Excel File')


	def button_export_excel(self):
		# #print("hlooooexcellllllllllllll")
		self.ensure_one()
		return self.xl_export()

	def xl_export(self):
		raise NotImplementedError

class OutstandingStatementWizard(models.TransientModel):
	_inherit = "outstanding.statement.wizard"

	def xl_export(self):
		# #print("xlllllllllllllllllhereeee")
		data = self._prepare_statement()
		# #print("dataaa",data)
		xl_data = self.get_data(data)
		#print("xlllllllll daatta",xl_data)

		# xl formating
		# oustanding daatta {'data': 
		# {189: 
			# {'today': '27/09/2022', 'start': '', 'end': '27/09/2022', 
		# 	'currencies': {2: 
			# {'lines': [], 'buckets': 
							# {'currency_id': 2, 'current': 0.0, 'b_1_30': 0.0, 'b_30_60': 0.0, 'b_60_90': 0.0, 'b_90_120': 0.0, 'b_over_120': 0.0, 'balance': 0.0}, 
							# 'balance_forward': 0.0, 'amount_due': 0.0}, 
		# 131: {'lines': [], 'buckets': {'currency_id': 131, 'current': 0.0, 'b_1_30': 0.0, 'b_30_60': 0.0, 'b_60_90': 0.0, 'b_90_120': 0.0, 'b_over_120': 0.0, 'balance': -2e-14}, 'balance_forward': 0.0, 'amount_due': 0.0}}}},
		 # 'company': res.company(1,), 
		# 'Currencies': {131: res.currency(131,), 1: res.currency(1,), 2: res.currency(2,)}, 'account_type': 'receivable', 'bucket_labels': ['Current', '1 - 30 Days', '31 - 60 Days', '61 - 90 Days', '91 - 120 Days', '121 Days +', 'Total'], 
		# 'get_inv_addr': <bound method OutstandingStatementWizard._get_invoice_address of outstanding.statement.wizard(15,)>}

		# for d in xl_data:
		# 	#print("ddddddddddddd",d)
		partner_dict = xl_data['data']
		Currencies = xl_data['Currencies']
		if self.show_aging_buckets:
			bucket_labels = xl_data['bucket_labels']
		d = partner_dict[self.partner_id.id]
		# xl_dict = xl_data['xl_dict']
		print("dddddddddddddddddd")
		print(d)
		#print(s)
		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		sheet= workbook.add_worksheet('Partner Statement')
		title_format = workbook.add_format({
			'bold': True,
			'align': 'center',
			'fg_color': '#D7E4BC',
			'border': 0}) 
		header_style = workbook.add_format({
			'bold': True,
			'align': 'center',
			'bg_color':'#aeadad',
			'border':0})
		# tot_format = workbook.add_format({
		# 	'bold': True,
		# 	'align': 'left',
		# 	'border': 0})
		tot_format1 = workbook.add_format({
			'bold': True,
			'align': 'right',
			'num_format': '#,##0.00',
			'border': 0})
		info_style = workbook.add_format({
			'bold': True,
			'border': 0})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'})	

		header_range = 'A1:I1'
		header = "STATEMENT OF ACCOUNTS Between "+str(self.date_start)+" and "+str(self.date_end)

		if self.mode == 'outstanding':
			header_range = 'A1:J1'
			header = "STATEMENT OF ACCOUNTS As on "+ str(self.date_end)


		sheet.merge_range(header_range,header,title_format)
		row = 0
		row = row + 2
		col = 0
		sheet.merge_range(row,col,row,2,"Customer"+" :"+self.partner_id.name,info_style)
		row = row + 1
		vat = self.partner_id.vat or ""
		sheet.merge_range(row,col,row,2,"TRN"+" :"+ vat,info_style)
		row = row + 1
		sheet.merge_range(row,col,row,2,"Salesperson"+" :"+self.partner_id.user_id.name,info_style)
				
		if d.get('no_entries'):
			raise UserError(_("The partner doesn't have due entries.!!!"))

		sheet.set_column('A:A',15)
		sheet.set_column('B:B',15)
		sheet.set_column('C:C',15)
		sheet.set_column('D:D',15)
		sheet.set_column('E:E',15)
		sheet.set_column('F:F',15)
		sheet.set_column('G:G',15)
		sheet.set_column('H:H',15)
		sheet.set_column('I:I',15)
		sheet.set_column('J:J',15)
		for currency in d['currencies'].items():
			# #print("currencyyyyyyyy",currency)
			display_currency = Currencies[currency[0]]
			# #print("ooo0000",currency[1])
			currency = currency[1]
			#print("ccc",currency)
			#print("2cuuu",currency)
			if currency['lines'] or (currency['balance_forward'] and self.mode == 'details'):
				#print("linessss")
				row = row + 3
				col = 0
				sheet.merge_range(row,col,row,2,"Currency"+" :"+display_currency.name,info_style)
				row = row + 1
				col = 0

				headers = ['Date','Due Date','LPO/Doc Ref.','Inv. No','Terms','Days','Debit','Credit','Bal','Cum.Bal']
				if self.mode == 'details':
					headers.remove('Days')

				for heading in headers:
					sheet.write(row,col,heading,header_style)
					col = col + 1
				if currency['balance_forward'] and self.mode == 'details':
					col = 0
					row = row + 1
					col = col + 1
					sheet.write(row,col,d['start'])
					col = col + 1
					sheet.write(row,col,"Balance Forwarded")
					col = col + 5
					sheet.write(row,col,currency['balance_forward'])
					col = col + 1
					sheet.write(row,col,currency['balance_forward'])

				for line in currency['lines']:
					col = 0
					row = row + 1
					sheet.write(row,col,line['date'])
					col = col + 1
					sheet.write(row,col,line['date_maturity'])
					col = col + 1
					lpo = line['lpo'] or ""
					sheet.write(row,col,lpo)
					col = col + 1
					move_id = line['move_id'] or ""
					sheet.write(row,col,move_id)
					col = col + 1
					payment_terms = line['payment_terms'] or ""
					sheet.write(row,col,payment_terms)
					col = col + 1
					if self.mode == 'outstanding':
						days = line['days']
						sheet.write(row,col,days)
						col = col + 1
					sheet.write(row,col,line['debit'], row_num_style)
					col = col + 1
					sheet.write(row,col,line['credit'], row_num_style)
					col = col + 1
					if self.mode == 'outstanding':
						amount = line['open_amount']
					if self.mode == 'details':
						amount = line['amount']
					sheet.write(row,col,amount, row_num_style)
					col = col + 1
					sheet.write(row,col,line['balance'], row_num_style)
					col = col + 1
				col = 0
				row = row + 1
				col_merge = 7
				if self.mode == 'details':
					col_merge = 6

				sheet.merge_range(row,col,row,col_merge,'Total Outstanding',info_style)	
				col = col_merge +1
				#print("collll",col)
				#print("currency['amount_due']",currency['amount_due'])
				sheet.write(row,col,currency['amount_due'], tot_format1)


				if currency['buckets']:
					# aging bucket
					row = row + 2
					col = 0 
					heading_row = row
					row = row + 1
					for bl in bucket_labels:
						sheet.write(row,col,bl,header_style)
						col = col + 1
					heading_col_merge = col
					col = 0
					header ="Aging Report at "+str(self.date_end)
					sheet.merge_range(heading_row,col,heading_row,heading_col_merge,header,info_style)
					row = row + 1
					buckets = currency['buckets']
					value = buckets.get('current', 0.0)
					sheet.write(row,col,value)
					col = col + 1
					value = buckets.get('b_1_30', 0.0)
					sheet.write(row,col,value)
					col = col + 1
					value = buckets.get('b_30_60', 0.0)
					sheet.write(row,col,value)
					col = col + 1
					value = buckets.get('b_60_90', 0.0)
					sheet.write(row,col,value)
					col = col + 1
					value = buckets.get('b_90_120', 0.0)
					sheet.write(row,col,value)
					col = col + 1
					value = buckets.get('b_over_120', 0.0)
					sheet.write(row,col,value)
					col = col + 1
					value = buckets.get('balance', 0.0)
					sheet.write(row,col,value)


		workbook.close()
		output.seek(0)
		excel_file = base64.encodestring(output.read())
		self.excel_file = excel_file
		filename= 'PartnerStatement.xlsx'
		self.file_name =filename
		return {            
		'type': 'ir.actions.act_window',            
		'view_type': 'form',            
		'view_mode': 'form',            
		'res_model': 'outstanding.statement.wizard',            
		'res_id': self.id,           
		# 'view_id': compose_form_id,            
		'target': 'new',            
		}




	def get_data(self, data):
		"""@return: returns a dict of parameters to pass to qweb report.
		  the most important pair is {'data': res} which contains all
		  the data for each partner.  It is structured like:
			{partner_id: {
				'start': date string,
				'end': date_string,
				'today': date_string
				'currencies': {
					currency_id: {
						'lines': [{'date': date string, ...}, ...],
						'balance_forward': float,
						'amount_due': float,
						'buckets': {
							'p1': float, 'p2': ...
				  }
			  }
		  }
		}
		"""
		company_id = data["company_id"]
		partner_ids = data["partner_ids"]
		date_start = data.get("date_start")
		mode = data.get("mode")
		company_currency = data.get("company_currency")#added for company_currency filter
		if date_start and isinstance(date_start, str):
			date_start = datetime.strptime(
				date_start, DEFAULT_SERVER_DATE_FORMAT
			).date()
		date_end = data["date_end"]
		if isinstance(date_end, str):
			date_end = datetime.strptime(date_end, DEFAULT_SERVER_DATE_FORMAT).date()
		account_type = data["account_type"]
		aging_type = data["aging_type"]
		today = fields.Date.today()
		amount_field = data.get("amount_field", "amount")
		if data.get('mode') == 'details':
			data["amount_field"] = "amount"
		else:
			data["amount_field"] = "open_amount"

		# There should be relatively few of these, so to speed performance
		# we cache them - default needed if partner lang not set
		self._cr.execute(
			"""
			SELECT p.id, l.date_format
			FROM res_partner p LEFT JOIN res_lang l ON p.lang=l.code
			WHERE p.id IN %(partner_ids)s
			""",
			{"partner_ids": tuple(partner_ids)},
		)
		date_formats = {r[0]: r[1] for r in self._cr.fetchall()}
		default_fmt = self.env["res.lang"]._lang_get(self.env.user.lang).date_format
		currencies = {x.id: x for x in self.env["res.currency"].search([])}

		res = {}
		# get base data
		# lines = self._get_account_display_lines(
		#     company_id, partner_ids, date_start, date_end, account_type
		# )





		if data.get('mode') == 'outstanding':
			lines = self._get_outstanding_account_display_lines(
				company_id, partner_ids, date_start, date_end, account_type, company_currency
			)
		if data.get('mode') == 'details':
			lines = self._get_detail_account_display_lines(
				company_id, partner_ids, date_start, date_end, account_type, company_currency
			)
		#print("llllllllllllllllll",lines)

		balances_forward = {}
		if data.get('mode') == 'details':
			balances_forward = self._get_account_initial_balance(
				company_id, partner_ids, date_start, account_type, company_currency
			) #To be checked


		#print("balances_forward",balances_forward)
		if data["show_aging_buckets"]:
			# buckets = self._get_account_show_buckets(
			#     company_id, partner_ids, date_end, account_type, aging_type
			# )
			buckets = self._get_account_show_buckets(
				company_id, partner_ids, date_end, account_type, aging_type, company_currency
			)
			bucket_labels = self._get_bucket_labels(date_end, aging_type)
		else:
			bucket_labels = {}

		# organise and format for report
		format_date = self._format_date_to_partner_lang
		partners_to_remove = set()
		xl_currencies = {}
		for partner_id in partner_ids:
			res[partner_id] = {
				"today": format_date(today, date_formats.get(partner_id, default_fmt)),
				"start": format_date(
					date_start, date_formats.get(partner_id, default_fmt)
				),
				"end": format_date(date_end, date_formats.get(partner_id, default_fmt)),
				"currencies": {},
			}
			currency_dict = res[partner_id]["currencies"]

			for line in balances_forward.get(partner_id, []):
				(
					currency_dict[line["currency_id"]],
					currencies,
				) = self._get_line_currency_defaults(
					line["currency_id"], currencies, line["balance"]
				)
			#print("currency_dict",currency_dict)

			for line in lines[partner_id]:
				if line["currency_id"] not in currency_dict:
					(
						currency_dict[line["currency_id"]],
						currencies,
					) = self._get_line_currency_defaults(
						line["currency_id"], currencies, 0.0
					)
				line_currency = currency_dict[line["currency_id"]]
				if not line["blocked"]:
					line_currency["amount_due"] += line[amount_field]
				line["balance"] = line_currency["amount_due"]
				line["date"] = format_date(
					line["date"], date_formats.get(partner_id, default_fmt)
				)
				line["date_maturity"] = format_date(
					line["date_maturity"], date_formats.get(partner_id, default_fmt)
				)
				

				move_id = self.env['account.move'].search([('id','=',line['move'])])
				payment_id = self.env['account.payment'].search([('move_id','=',line['move'])])
				line['payment_terms'] = move_id.invoice_payment_term_id.name if move_id.invoice_payment_term_id else False
				line['lpo'] = move_id.ref
				# line['chq'] = []
				# if move_id.state == 'posted' and move_id.is_invoice(include_receipts=True):
				#     payments_widget_vals = move_id._get_reconciled_info_JSON_values()
				#     for payment in payments_widget_vals:
				#         move_payment_id = self.env['account.payment'].search([('id','=',payment['account_payment_id'])])
				#         if move_payment_id and move_payment_id.payment_method_code=='pdc':
				#             chq_dict = {}
				#             payment_date = move_payment_id.effective_date if move_payment_id.effective_date else move_payment_id.date
				#             payment_date =datetime.strptime(str(payment_date), '%Y-%m-%d').strftime('%d/%m/%Y')
				#             chq_dict = {
				#             'amount':payment['amount'],
				#             'date':payment_date,
				#             'chq_no':move_payment_id.cheque_reference or False
				#             }
				#             line['chq'].append(chq_dict)

				# if payment_id and payment_id.payment_method_code=='pdc':
				#     payment_date = payment_id.effective_date if payment_id.effective_date else payment_id.date
				#     payment_date =datetime.strptime(str(payment_date), '%Y-%m-%d').strftime('%d/%m/%Y')
				#     chq_dict = {
				#         'amount':payment_id.amount,
				#         'date':payment_date,
				#         'chq_no':payment_id.cheque_reference or False,
				#         }
				#     line['chq'].append(chq_dict)
				# # #print("tttttttrr",line['chq'],not line['chq'])
				# if not line['chq']:
				#     chq_dict = {
				#         'amount':0,
				#         'date':False,
				#         'chq_no':False,
				#         }
				#     line['chq'].append(chq_dict)
				date_inv = datetime.strptime(line['date'], '%d/%m/%Y').strftime('%Y-%m-%d')
				date_inv = datetime.strptime(date_inv, '%Y-%m-%d')
				date_end_wiz = datetime.strptime(str(data['date_end']), '%Y-%m-%d')
				line['days'] = abs((date_end_wiz - date_inv).days)
				line_currency["lines"].append(line)
				# #print("lineeeeeeeeeeee",line)

			if data["show_aging_buckets"]:
				for line in buckets[partner_id]:
					if line["currency_id"] not in currency_dict:
						(
							currency_dict[line["currency_id"]],
							currencies,
						) = self._get_line_currency_defaults(
							line["currency_id"], currencies, 0.0
						)
					line_currency = currency_dict[line["currency_id"]]
					line_currency["buckets"] = line

			if len(partner_ids) > 1:
				values = currency_dict.values()
				if not any([v["lines"] or v["balance_forward"] for v in values]):
					if data["filter_non_due_partners"]:
						partners_to_remove.add(partner_id)
						continue
					else:
						res[partner_id]["no_entries"] = True
				if data["filter_negative_balances"]:
					if not all([v["amount_due"] >= 0.0 for v in values]):
						partners_to_remove.add(partner_id)

		for partner in partners_to_remove:
			del res[partner]
			partner_ids.remove(partner)
		print("yyyyyyyyyyyyyyy",currency_dict)
		print("llliii",lines)
		print("reeee",res)
		# for items in res:
			#print("gggggggffff",items)
			# for line in items[1]:
			# 	#print("lllllllrrr",line)

		return {
			# "doc_ids": partner_ids,
			# "doc_model": "res.partner",
			# "docs": self.env["res.partner"].browse(partner_ids),
			"data": res,
			# "company": self.env["res.company"].browse(company_id),
			"Currencies": currencies,
			"account_type": account_type,
			"bucket_labels": bucket_labels,
			# "get_inv_addr": self._get_invoice_address,
		}



	# outstanding functions
	def _display_lines_sql_q1(self, partners, date_end, account_type):
		partners = tuple(partners)
		return str(
			self._cr.mogrify(
				"""
			SELECT m.name AS move_id, l.partner_id, l.date, l.name,
							l.ref, l.blocked, l.currency_id, l.company_id,m.id as move,
			CASE WHEN (l.currency_id is not null AND l.amount_currency > 0.0)
				THEN avg(l.amount_currency)
				ELSE avg(l.debit)
			END as debit,
			CASE WHEN (l.currency_id is not null AND l.amount_currency < 0.0)
				THEN avg(l.amount_currency * (-1))
				ELSE avg(l.credit)
			END as credit,
			CASE WHEN l.balance > 0.0
				THEN l.balance - sum(coalesce(pd.amount, 0.0))
				ELSE l.balance + sum(coalesce(pc.amount, 0.0))
			END AS open_amount,
			CASE WHEN l.balance > 0.0
				--THEN l.amount_currency - sum(coalesce(pd.amount_currency, 0.0))
			   -- ELSE l.amount_currency + sum(coalesce(pc.amount_currency, 0.0))
				THEN l.amount_currency - sum(coalesce(pd.debit_amount_currency, 0.0))
				ELSE l.amount_currency + sum(coalesce(pc.credit_amount_currency, 0.0))
			END AS open_amount_currency,
			CASE WHEN l.date_maturity is null
				THEN l.date
				ELSE l.date_maturity
			END as date_maturity
			FROM account_move_line l
			JOIN account_move m ON (l.move_id = m.id)
			LEFT JOIN (SELECT pr.*
				FROM account_partial_reconcile pr
				INNER JOIN account_move_line l2
				ON pr.credit_move_id = l2.id
				WHERE l2.date <= %(date_end)s
			) as pd ON pd.debit_move_id = l.id
			LEFT JOIN (SELECT pr.*
				FROM account_partial_reconcile pr
				INNER JOIN account_move_line l2
				ON pr.debit_move_id = l2.id
				WHERE l2.date <= %(date_end)s
			) as pc ON pc.credit_move_id = l.id

			LEFT JOIN account_account aa on aa.id = l.account_id
			LEFT JOIN account_account_type at on at.id = aa.user_type_id
			WHERE l.partner_id IN %(partners)s
								AND at.type = %(account_type)s
								AND (
								  (pd.id IS NOT NULL AND
									  pd.max_date <= %(date_end)s) OR
								  (pc.id IS NOT NULL AND
									  pc.max_date <= %(date_end)s) OR
								  (pd.id IS NULL AND pc.id IS NULL)
								) AND l.date <= %(date_end)s AND m.state IN ('posted')
			GROUP BY l.partner_id, m.name, l.date, l.date_maturity, l.name,
								l.ref, l.blocked, l.currency_id,
								l.balance, l.amount_currency, l.company_id,m.id
			""",
				locals(),
			),
			"utf-8",
		)

	def _display_lines_sql_q1_company_currency(self, partners, date_end, account_type):
		partners = tuple(partners)
		return str(
			self._cr.mogrify(
				"""
			SELECT m.name AS move_id, l.partner_id, l.date, l.name,
							l.ref, l.blocked, c.currency_id, l.company_id,m.id as move,
			-- CASE WHEN (l.currency_id is not null AND l.amount_currency > 0.0)
			--     THEN avg(l.amount_currency)
			--     ELSE avg(l.debit)
			-- END as debit,
			avg(l.debit) as debit,
			-- CASE WHEN (l.currency_id is not null AND l.amount_currency < 0.0)
			--     THEN avg(l.amount_currency * (-1))
			--     ELSE avg(l.credit)
			-- END as credit,
			avg(l.credit) as credit,
			CASE WHEN l.balance > 0.0
				THEN l.balance - sum(coalesce(pd.amount, 0.0))
				ELSE l.balance + sum(coalesce(pc.amount, 0.0))
			END AS open_amount,
			CASE WHEN l.balance > 0.0
				--THEN l.amount_currency - sum(coalesce(pd.amount_currency, 0.0))
			   -- ELSE l.amount_currency + sum(coalesce(pc.amount_currency, 0.0))
				THEN l.amount_currency - sum(coalesce(pd.debit_amount_currency, 0.0))
				ELSE l.amount_currency + sum(coalesce(pc.credit_amount_currency, 0.0))
			END AS open_amount_currency,
			CASE WHEN l.date_maturity is null
				THEN l.date
				ELSE l.date_maturity
			END as date_maturity
			FROM account_move_line l
			JOIN account_move m ON (l.move_id = m.id)
			LEFT JOIN (SELECT pr.*
				FROM account_partial_reconcile pr
				INNER JOIN account_move_line l2
				ON pr.credit_move_id = l2.id
				WHERE l2.date <= %(date_end)s
			) as pd ON pd.debit_move_id = l.id
			LEFT JOIN (SELECT pr.*
				FROM account_partial_reconcile pr
				INNER JOIN account_move_line l2
				ON pr.debit_move_id = l2.id
				WHERE l2.date <= %(date_end)s
			) as pc ON pc.credit_move_id = l.id

			LEFT JOIN account_account aa on aa.id = l.account_id
			LEFT JOIN account_account_type at on at.id = aa.user_type_id
			JOIN res_company c ON (c.id = l.company_id)
			WHERE l.partner_id IN %(partners)s
								AND at.type = %(account_type)s
								AND (
								  (pd.id IS NOT NULL AND
									  pd.max_date <= %(date_end)s) OR
								  (pc.id IS NOT NULL AND
									  pc.max_date <= %(date_end)s) OR
								  (pd.id IS NULL AND pc.id IS NULL)
								) AND l.date <= %(date_end)s AND m.state IN ('posted')
			GROUP BY l.partner_id, m.name, l.date, l.date_maturity, l.name,
								l.ref, l.blocked, l.currency_id,c.currency_id,
								l.balance,l.amount_currency, l.debit,l.credit, l.company_id,m.id
			""",
				locals(),
			),
			"utf-8",
		)

	def _display_lines_sql_q2(self):
		return str(
			self._cr.mogrify(
				"""
				SELECT Q1.partner_id, Q1.currency_id, Q1.move_id,
					Q1.date, Q1.date_maturity, Q1.debit, Q1.credit,
					Q1.name, Q1.ref, Q1.blocked, Q1.company_id,
				CASE WHEN Q1.currency_id is not null
					THEN Q1.open_amount_currency
					ELSE Q1.open_amount
				END as open_amount,
				Q1.move
				FROM Q1
				""",
				locals(),
			),
			"utf-8",
		)

	def _display_lines_sql_q2_company_currency(self):
		return str(
			self._cr.mogrify(
				"""
				SELECT Q1.partner_id, Q1.currency_id, Q1.move_id,
					Q1.date, Q1.date_maturity, Q1.debit, Q1.credit,
					Q1.name, Q1.ref, Q1.blocked, Q1.company_id,
				-- CASE WHEN Q1.currency_id is not null
				--     THEN Q1.open_amount_currency
				--     ELSE Q1.open_amount
				-- END as open_amount,
				Q1.open_amount as open_amount,
				Q1.move
				FROM Q1
				""",
				locals(),
			),
			"utf-8",
		)

	def _display_lines_sql_q3(self, company_id):
		return str(
			self._cr.mogrify(
				"""
			SELECT Q2.partner_id, Q2.move_id, Q2.date, Q2.date_maturity,
			  Q2.name, Q2.ref, Q2.debit, Q2.credit,
			  Q2.debit-Q2.credit AS amount, blocked,
			  COALESCE(Q2.currency_id, c.currency_id) AS currency_id,
			  Q2.open_amount,
			  Q2.move
			FROM Q2
			JOIN res_company c ON (c.id = Q2.company_id)
			WHERE c.id = %(company_id)s AND Q2.open_amount != 0.0
			""",
				locals(),
			),
			"utf-8",
		)

	# def _get_account_display_lines(
	#     self, company_id, partner_ids, date_start, date_end, account_type
	# ):
	def _get_outstanding_account_display_lines(
		self, company_id, partner_ids, date_start, date_end, account_type, company_currency
	):
		partners = tuple(partner_ids)
		if company_currency:
			table1=self._display_lines_sql_q1_company_currency(partners, date_end, account_type)
			table2=self._display_lines_sql_q2_company_currency()
		else:
			table1=self._display_lines_sql_q1(partners, date_end, account_type)
			table2=self._display_lines_sql_q2()
		res = dict(map(lambda x: (x, []), partner_ids))
		# partners = tuple(partner_ids)
		# pylint: disable=E8103
		self.env.cr.execute(
			"""
		WITH Q1 as (%s),
			 Q2 AS (%s),
			 Q3 AS (%s)
		SELECT partner_id, currency_id, move_id, date, date_maturity, debit,
							credit, amount, open_amount, name, ref, blocked, move
		FROM Q3
		ORDER BY date, date_maturity, move_id"""
			% (
				table1,
				table2,
				self._display_lines_sql_q3(company_id),
			)
		)
		for row in self.env.cr.dictfetchall():
			if float_is_zero(row['open_amount'],precision_rounding=0.010000):
				continue
			res[row.pop("partner_id")].append(row)
		return res




	# detail functions
	def _initial_balance_sql_q1(self, partners, date_start, account_type):
		return str(
			self._cr.mogrify(
				"""
			SELECT l.partner_id, l.currency_id, l.company_id,
			CASE WHEN l.currency_id is not null AND l.amount_currency > 0.0
				THEN sum(l.amount_currency)
				ELSE sum(l.debit)
			END as debit,
			CASE WHEN l.currency_id is not null AND l.amount_currency < 0.0
				THEN sum(l.amount_currency * (-1))
				ELSE sum(l.credit)
			END as credit
			FROM account_move_line l
			JOIN account_move m ON (l.move_id = m.id)

			LEFT JOIN account_account aa on aa.id = l.account_id
			LEFT JOIN account_account_type at on at.id = aa.user_type_id
			WHERE l.partner_id IN %(partners)s
								AND at.type = %(account_type)s
								AND l.date < %(date_start)s AND not l.blocked
								AND m.state IN ('posted')
			GROUP BY l.partner_id, l.currency_id, l.amount_currency,
								l.company_id
		""",
				locals(),
			),
			"utf-8",
		)

	def _initial_balance_sql_q1_company_currency(self, partners, date_start, account_type):
		return str(
			self._cr.mogrify(
				"""
			SELECT l.partner_id, c.currency_id, l.company_id,
			sum(l.debit) as debit,
			sum(l.credit) as credit
			FROM account_move_line l
			JOIN account_move m ON (l.move_id = m.id)

			LEFT JOIN account_account aa on aa.id = l.account_id
			LEFT JOIN account_account_type at on at.id = aa.user_type_id
			JOIN res_company c ON (c.id = l.company_id)
			WHERE l.partner_id IN %(partners)s
								AND at.type = %(account_type)s
								AND l.date < %(date_start)s AND not l.blocked
								AND m.state IN ('posted')
			GROUP BY l.partner_id, c.currency_id, l.debit, l.credit,
								l.company_id
		""",
				locals(),
			),
			"utf-8",
		)

	def _initial_balance_sql_q2(self, company_id):
		return str(
			self._cr.mogrify(
				"""
			SELECT Q1.partner_id, debit-credit AS balance,
			COALESCE(Q1.currency_id, c.currency_id) AS currency_id
			FROM Q1
			JOIN res_company c ON (c.id = Q1.company_id)
			WHERE c.id = %(company_id)s
		""",
				locals(),
			),
			"utf-8",
		)

	def _get_account_initial_balance(
		self, company_id, partner_ids, date_start, account_type, company_currency
	):
		balance_start = defaultdict(list)
		partners = tuple(partner_ids)
		if company_currency:
			table1 = self._initial_balance_sql_q1_company_currency(partners, date_start, account_type)
		else:
			table1 =  self._initial_balance_sql_q1(partners, date_start, account_type)
		# pylint: disable=E8103
		a = (
			"""WITH Q1 AS (%s), Q2 AS (%s)
		SELECT partner_id, currency_id, balance
		FROM Q2"""
			% (
				# self._initial_balance_sql_q1(partners, date_start, account_type),
				table1,
				self._initial_balance_sql_q2(company_id),
			)
		)
		#print(a)
		self.env.cr.execute(
			"""WITH Q1 AS (%s), Q2 AS (%s)
		SELECT partner_id, currency_id, balance
		FROM Q2"""
			% (
				# self._initial_balance_sql_q1(partners, date_start, account_type),
				table1,
				self._initial_balance_sql_q2(company_id),
			)
		)
		for row in self.env.cr.dictfetchall():
			#print("rrrrr",row)

			if float_is_zero(row['balance'],precision_rounding=0.010000):
				continue
			balance_start[row.pop("partner_id")].append(row)
		#print(balance_start)
		return balance_start

	def _display_detail_lines_sql_q1(self, partners, date_start, date_end, account_type):
		return str(
			self._cr.mogrify(
				"""
			SELECT m.name AS move_id, l.partner_id, l.date,m.id as move,
	   CASE WHEN (aj.type IN ('sale', 'purchase'))
				THEN l.name
				ELSE '/'
			END as name,
	   CASE WHEN (aj.type IN ('sale', 'purchase'))
				THEN l.ref
		   WHEN (aj.type in ('bank', 'cash'))
				THEN 'Payment'
				ELSE ''
			END as ref,
			l.blocked, l.currency_id, l.company_id,
			CASE WHEN (l.currency_id is not null AND l.amount_currency > 0.0)
				THEN sum(l.amount_currency)
				ELSE sum(l.debit)
			END as debit,
			CASE WHEN (l.currency_id is not null AND l.amount_currency < 0.0)
				THEN sum(l.amount_currency * (-1))
				ELSE sum(l.credit)
			END as credit,
			CASE WHEN l.date_maturity is null
				THEN l.date
				ELSE l.date_maturity
			END as date_maturity
			FROM account_move_line l
			JOIN account_move m ON (l.move_id = m.id)
			JOIN account_journal aj ON (l.journal_id = aj.id)

			LEFT JOIN account_account aa on aa.id = l.account_id
			LEFT JOIN account_account_type at on at.id = aa.user_type_id
			WHERE l.partner_id IN %(partners)s
				AND at.type = %(account_type)s
				AND %(date_start)s <= l.date
				AND l.date <= %(date_end)s
				AND m.state IN ('posted')
			GROUP BY l.partner_id, m.name, l.date, l.date_maturity,m.id,
				CASE WHEN (aj.type IN ('sale', 'purchase'))
					THEN l.name
					ELSE '/'
				END,
				CASE WHEN (aj.type IN ('sale', 'purchase'))
					THEN l.ref
				WHEN (aj.type in ('bank', 'cash'))
					THEN 'Payment'
					ELSE ''
				END,
				l.blocked, l.currency_id, l.amount_currency, l.company_id
		""",
				locals(),
			),
			"utf-8",
		)

	def _display_detail_lines_sql_q1_company_currency(self, partners, date_start, date_end, account_type):
		return str(
			self._cr.mogrify(
				"""
			SELECT m.name AS move_id, l.partner_id, l.date,m.id as move,
	   CASE WHEN (aj.type IN ('sale', 'purchase'))
				THEN l.name
				ELSE '/'
			END as name,
	   CASE WHEN (aj.type IN ('sale', 'purchase'))
				THEN l.ref
		   WHEN (aj.type in ('bank', 'cash'))
				THEN 'Payment'
				ELSE ''
			END as ref,
			l.blocked, c.currency_id, l.company_id,
			sum(l.debit) as debit,
			sum(l.credit) as credit,
			CASE WHEN l.date_maturity is null
				THEN l.date
				ELSE l.date_maturity
			END as date_maturity
			FROM account_move_line l
			JOIN account_move m ON (l.move_id = m.id)
			JOIN account_journal aj ON (l.journal_id = aj.id)

			LEFT JOIN account_account aa on aa.id = l.account_id
			LEFT JOIN account_account_type at on at.id = aa.user_type_id
			JOIN res_company c ON (c.id = l.company_id)
			WHERE l.partner_id IN %(partners)s
				AND at.type = %(account_type)s
				AND %(date_start)s <= l.date
				AND l.date <= %(date_end)s
				AND m.state IN ('posted')
			GROUP BY l.partner_id, m.name, l.date, l.date_maturity,m.id,
				CASE WHEN (aj.type IN ('sale', 'purchase'))
					THEN l.name
					ELSE '/'
				END,
				CASE WHEN (aj.type IN ('sale', 'purchase'))
					THEN l.ref
				WHEN (aj.type in ('bank', 'cash'))
					THEN 'Payment'
					ELSE ''
				END,
				l.blocked, c.currency_id, l.debit,l.credit, l.company_id
		""",
				locals(),
			),
			"utf-8",
		)

	def _display_detail_lines_sql_q2(self, company_id):
		return str(
			self._cr.mogrify(
				"""
			SELECT Q1.partner_id, Q1.move_id, Q1.date, Q1.date_maturity,
				Q1.name, Q1.ref, Q1.debit, Q1.credit,
				Q1.debit-Q1.credit as amount, Q1.blocked,
				COALESCE(Q1.currency_id, c.currency_id) AS currency_id, Q1.move
			FROM Q1
			JOIN res_company c ON (c.id = Q1.company_id)
			WHERE c.id = %(company_id)s
		""",
				locals(),
			),
			"utf-8",
		)


	def _get_detail_account_display_lines(
		self, company_id, partner_ids, date_start, date_end, account_type, company_currency
	):
		res = dict(map(lambda x: (x, []), partner_ids))
		partners = tuple(partner_ids)
		#print(":companyyyy",company_currency)
		if company_currency:
			table1=self._display_detail_lines_sql_q1_company_currency(partners, date_start, date_end, account_type)
		else:
			table1=self._display_detail_lines_sql_q1(partners, date_start, date_end, account_type)

		# pylint: disable=E8103
		self.env.cr.execute(
			"""
		WITH Q1 AS (%s),
			 Q2 AS (%s)
		SELECT partner_id, move_id, date, date_maturity, name, ref, debit,
							credit, amount, blocked, currency_id,move
		FROM Q2
		ORDER BY date, date_maturity, move_id"""
			% (
				# self._display_lines_sql_q1(
				#     partners, date_start, date_end, account_type
				# ),
				table1,
				self._display_detail_lines_sql_q2(company_id),
			)
		)
		for row in self.env.cr.dictfetchall():
			#print("rwww",row)
			if float_is_zero(row['amount'],precision_rounding=0.010000):
				continue
			res[row.pop("partner_id")].append(row)
		return res





	# common
	def _get_line_currency_defaults(self, currency_id, currencies, balance_forward):
		if currency_id not in currencies:
			# This will only happen if currency is inactive
			currencies[currency_id] = self.env["res.currency"].browse(currency_id)
		#print("kkkksssss",balance_forward)
		return (
			{
				"lines": [],
				"buckets": [],
				"balance_forward": balance_forward,
				"amount_due": balance_forward,
			},
			currencies,
		)
		
	def _get_invoice_address(self, part):
		inv_addr_id = part.address_get(["invoice"]).get("invoice", part.id)
		return self.env["res.partner"].browse(inv_addr_id)

	def _format_date_to_partner_lang(
		self, date, date_format=DEFAULT_SERVER_DATE_FORMAT
	):
		if isinstance(date, str):
			date = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
		return date.strftime(date_format) if date else ""

	def _show_buckets_sql_q1(self, partners, date_end, account_type):
		return str(
			self._cr.mogrify(
				"""
			SELECT l.partner_id, l.currency_id, l.company_id, l.move_id,
			CASE WHEN l.balance > 0.0
				THEN l.balance - sum(coalesce(pd.amount, 0.0))
				ELSE l.balance + sum(coalesce(pc.amount, 0.0))
			END AS open_due,
			CASE WHEN l.balance > 0.0
				-- THEN l.amount_currency - sum(coalesce(pd.amount_currency, 0.0))
				-- ELSE l.amount_currency + sum(coalesce(pc.amount_currency, 0.0))
				THEN l.amount_currency - sum(coalesce(pd.debit_amount_currency, 0.0))
				ELSE l.amount_currency + sum(coalesce(pc.credit_amount_currency, 0.0))
			END AS open_due_currency,
			CASE WHEN l.date_maturity is null
				THEN l.date
				ELSE l.date_maturity
			END as date_maturity
			FROM account_move_line l
			JOIN account_move m ON (l.move_id = m.id)
			LEFT JOIN (SELECT pr.*
				FROM account_partial_reconcile pr
				INNER JOIN account_move_line l2
				ON pr.credit_move_id = l2.id
				WHERE l2.date <= %(date_end)s
			) as pd ON pd.debit_move_id = l.id
			LEFT JOIN (SELECT pr.*
				FROM account_partial_reconcile pr
				INNER JOIN account_move_line l2
				ON pr.debit_move_id = l2.id
				WHERE l2.date <= %(date_end)s
			) as pc ON pc.credit_move_id = l.id

			LEFT JOIN account_account aa on aa.id = l.account_id
			LEFT JOIN account_account_type at on at.id = aa.user_type_id
			WHERE l.partner_id IN %(partners)s
								AND at.type = %(account_type)s
								AND (
								  (pd.id IS NOT NULL AND
									  pd.max_date <= %(date_end)s) OR
								  (pc.id IS NOT NULL AND
									  pc.max_date <= %(date_end)s) OR
								  (pd.id IS NULL AND pc.id IS NULL)
								) AND l.date <= %(date_end)s AND not l.blocked
								  AND m.state IN ('posted')
			GROUP BY l.partner_id, l.currency_id, l.date, l.date_maturity,
								l.amount_currency, l.balance, l.move_id,
								l.company_id, l.id
		""",
				locals(),
			),
			"utf-8",
		)

	def _show_buckets_sql_q2(self, date_end, minus_30, minus_60, minus_90, minus_120):
		return str(
			self._cr.mogrify(
				"""
			SELECT partner_id, currency_id, date_maturity, open_due,
							open_due_currency, move_id, company_id,
			CASE
				WHEN %(date_end)s <= date_maturity AND currency_id is null
								THEN open_due
				WHEN %(date_end)s <= date_maturity AND currency_id is not null
								THEN open_due_currency
				ELSE 0.0
			END as current,
			CASE
				WHEN %(minus_30)s < date_maturity
					AND date_maturity < %(date_end)s
					AND currency_id is null
				THEN open_due
				WHEN %(minus_30)s < date_maturity
					AND date_maturity < %(date_end)s
					AND currency_id is not null
				THEN open_due_currency
				ELSE 0.0
			END as b_1_30,
			CASE
				WHEN %(minus_60)s < date_maturity
					AND date_maturity <= %(minus_30)s
					AND currency_id is null
				THEN open_due
				WHEN %(minus_60)s < date_maturity
					AND date_maturity <= %(minus_30)s
					AND currency_id is not null
				THEN open_due_currency
				ELSE 0.0
			END as b_30_60,
			CASE
				WHEN %(minus_90)s < date_maturity
					AND date_maturity <= %(minus_60)s
					AND currency_id is null
				THEN open_due
				WHEN %(minus_90)s < date_maturity
					AND date_maturity <= %(minus_60)s
					AND currency_id is not null
				THEN open_due_currency
				ELSE 0.0
			END as b_60_90,
			CASE
				WHEN %(minus_120)s < date_maturity
					AND date_maturity <= %(minus_90)s
					AND currency_id is null
				THEN open_due
				WHEN %(minus_120)s < date_maturity
					AND date_maturity <= %(minus_90)s
					AND currency_id is not null
				THEN open_due_currency
				ELSE 0.0
			END as b_90_120,
			CASE
				WHEN date_maturity <= %(minus_120)s
					AND currency_id is null
				THEN open_due
				WHEN date_maturity <= %(minus_120)s
					AND currency_id is not null
				THEN open_due_currency
				ELSE 0.0
			END as b_over_120
			FROM Q1
			GROUP BY partner_id, currency_id, date_maturity, open_due,
								open_due_currency, move_id, company_id
		""",
				locals(),
			),
			"utf-8",
		)

	def _show_buckets_sql_q2_company_currency(self, date_end, minus_30, minus_60, minus_90, minus_120):
		return str(
			self._cr.mogrify(
				"""
			SELECT Q1.partner_id, c.currency_id as currency_id, date_maturity, open_due,
							open_due_currency, move_id, company_id,
			CASE
				WHEN %(date_end)s <= date_maturity
					THEN sum(open_due)
				ELSE 0.0
			END as current,
			CASE
				WHEN %(minus_30)s < date_maturity
					AND date_maturity < %(date_end)s
				THEN sum(open_due)
				ELSE 0.0
			END as b_1_30,
			CASE
				WHEN %(minus_60)s < date_maturity
					AND date_maturity <= %(minus_30)s
				THEN sum(open_due)
				ELSE 0.0
			END as b_30_60,
			CASE
				WHEN %(minus_90)s < date_maturity
					AND date_maturity <= %(minus_60)s
					THEN sum(open_due)
					ELSE 0.0
			END as b_60_90,
			CASE
				WHEN %(minus_120)s < date_maturity
					AND date_maturity <= %(minus_90)s
					THEN sum(open_due)
					ELSE 0.0
			END as b_90_120,
			CASE
				WHEN date_maturity <= %(minus_120)s
					THEN sum(open_due)
					ELSE 0.0
			END as b_over_120
			FROM Q1
			JOIN res_company c ON (c.id = company_id)
			GROUP BY Q1.partner_id, c.currency_id, date_maturity, open_due,
								open_due_currency, move_id, company_id
		""",
				locals(),
			),
			"utf-8",
		)

	def _show_buckets_sql_q3(self, company_id):
		return str(
			self._cr.mogrify(
				"""
			SELECT Q2.partner_id, current, b_1_30, b_30_60, b_60_90, b_90_120,
								b_over_120,
			COALESCE(Q2.currency_id, c.currency_id) AS currency_id
			FROM Q2
			JOIN res_company c ON (c.id = Q2.company_id)
			WHERE c.id = %(company_id)s
		""",
				locals(),
			),
			"utf-8",
		)

	def _show_buckets_sql_q4(self):
		return """
			SELECT partner_id, currency_id, sum(current) as current,
								sum(b_1_30) as b_1_30,
								sum(b_30_60) as b_30_60,
								sum(b_60_90) as b_60_90,
								sum(b_90_120) as b_90_120,
								sum(b_over_120) as b_over_120
			FROM Q3
			GROUP BY partner_id, currency_id
		"""

	def _get_bucket_dates(self, date_end, aging_type):
		# commented because for monthwise and date wise the days passed is different and days wise is correct
		# return getattr(
		#     self, "_get_bucket_dates_%s" % aging_type, self._get_bucket_dates_days
		# )(date_end)
		return getattr(
			self, "_get_bucket_dates_days", self._get_bucket_dates_days
		)(date_end)

	def _get_bucket_dates_days(self, date_end):
		return {
			"date_end": date_end,
			"minus_30": date_end - timedelta(days=30),
			"minus_60": date_end - timedelta(days=60),
			"minus_90": date_end - timedelta(days=90),
			"minus_120": date_end - timedelta(days=120),
		}

	def _get_bucket_dates_months(self, date_end):
		res = {}
		d = date_end
		for k in ("date_end", "minus_30", "minus_60", "minus_90", "minus_120"):
			res[k] = d
			d = d.replace(day=1) - timedelta(days=1)
		return res

	# def _get_account_show_buckets(
	#     self, company_id, partner_ids, date_end, account_type, aging_type
	# ):
	def _get_account_show_buckets(
		self, company_id, partner_ids, date_end, account_type, aging_type, company_currency
	):
		buckets = dict(map(lambda x: (x, []), partner_ids))
		partners = tuple(partner_ids)
		full_dates = self._get_bucket_dates(date_end, aging_type)
		# pylint: disable=E8103
		# All input queries are properly escaped - false positive
		if company_currency:
			table2=self._show_buckets_sql_q2_company_currency(
					full_dates["date_end"],
					full_dates["minus_30"],
					full_dates["minus_60"],
					full_dates["minus_90"],
					full_dates["minus_120"],
				)
		else:
			# #print("fgggggggggggg",full_dates)
			table2=self._show_buckets_sql_q2(
					full_dates["date_end"],
					full_dates["minus_30"],
					full_dates["minus_60"],
					full_dates["minus_90"],
					full_dates["minus_120"],
				)
		self.env.cr.execute(
			"""
			WITH Q1 AS (%s),
				Q2 AS (%s),
				Q3 AS (%s),
				Q4 AS (%s)
			SELECT partner_id, currency_id, current, b_1_30, b_30_60, b_60_90,
							b_90_120, b_over_120,
							current+b_1_30+b_30_60+b_60_90+b_90_120+b_over_120
							AS balance
			FROM Q4
			GROUP BY partner_id, currency_id, current, b_1_30, b_30_60,
				b_60_90, b_90_120, b_over_120"""
			% (
				self._show_buckets_sql_q1(partners, date_end, account_type),
				table2,
				self._show_buckets_sql_q3(company_id),
				self._show_buckets_sql_q4(),
			)
		)
		for row in self.env.cr.dictfetchall():
			if float_is_zero(row['current'],precision_rounding=0.010000):
				row['current']=0.00
			if float_is_zero(row['b_1_30'],precision_rounding=0.010000):
				row['b_1_30']=0.00
			if float_is_zero(row['b_30_60'],precision_rounding=0.010000):
				row['b_30_60']=0.00
			if float_is_zero(row['b_60_90'],precision_rounding=0.010000):
				row['b_60_90']=0.00
			if float_is_zero(row['b_90_120'],precision_rounding=0.010000):
				row['b_90_120']=0.00
			if float_is_zero(row['b_over_120'],precision_rounding=0.010000):
				row['b_over_120']=0.00
			buckets[row.pop("partner_id")].append(row)
		return buckets

	def _get_bucket_labels(self, date_end, aging_type):
		return getattr(
			self, "_get_bucket_labels_%s" % aging_type, self._get_bucket_dates_days
		)(date_end)

	def _get_bucket_labels_days(self, date_end):
		return [
			_("Current"),
			_("1 - 30 Days"),
			_("31 - 60 Days"),
			_("61 - 90 Days"),
			_("91 - 120 Days"),
			_("121 Days +"),
			_("Total"),
		]

	def _get_bucket_labels_months(self, date_end):
		return [
			_("Current"),
			_("1 Month"),
			_("2 Months"),
			_("3 Months"),
			_("4 Months"),
			_("Older"),
			_("Total"),
		]
