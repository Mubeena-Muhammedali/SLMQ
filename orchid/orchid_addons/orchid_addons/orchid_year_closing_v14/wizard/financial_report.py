# -*- coding: utf-8 -*-
import re
from odoo import api, models, fields


class FinancialReport(models.TransientModel):
	_inherit = "financial.report"

	def view_report_pdf(self):
		"""This function will be executed when we click the view button
		from the wizard. Based on the values provided in the wizard, this
		function will print pdf report"""
		self.ensure_one()
		data = dict()
		data['ids'] = self.env.context.get('active_ids', [])
		data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
		data['form'] = self.read(
			['date_from', 'enable_filter', 'debit_credit', 'date_to',
			 'account_report_id', 'target_move', 'view_format',
			 'company_id','od_with_closing'])[0]
		used_context = self._build_contexts(data)
		data['form']['used_context'] = dict(
			used_context,
			lang=self.env.context.get('lang') or 'en_US')

		report_lines = self.get_account_lines(data['form'])
		# find the journal items of these accounts
		journal_items = self.find_journal_items(report_lines, data['form'])

		def set_report_level(rec):
			"""This function is used to set the level of each item.
			This level will be used to set the alignment in the dynamic reports."""
			level = 1
			if not rec['parent']:
				return level
			else:
				for line in report_lines:
					key = 'a_id' if line['type'] == 'account' else 'id'
					if line[key] == rec['parent']:
						return level + set_report_level(line)

		# finding the root
		for item in report_lines:
			item['balance'] = round(item['balance'], 2)
			if not item['parent']:
				item['level'] = 1
				parent = item
				report_name = item['name']
				id = item['id']
				report_id = item['r_id']
			else:
				item['level'] = set_report_level(item)
		currency = self._get_currency()
		data['currency'] = currency
		data['journal_items'] = journal_items
		data['report_lines'] = report_lines
		# checking view type
		return self.env.ref(
			'orchid_account_enhancement_v14.financial_report_pdf').report_action(self,
																	  data)

	def find_journal_items(self, report_lines, form):
		cr = self.env.cr
		journal_items = []
		for i in report_lines:
			if i['type'] == 'account':
				account = i['account']
				if form['od_with_closing']:
					if form['target_move'] == 'posted':
						search_query = "select aml.id, am.id as j_id, aml.account_id, aml.date," \
									   " aml.name as label, am.name, " \
									   + "(aml.debit-aml.credit) as balance, aml.debit, aml.credit, aml.partner_id " \
									   + " from account_move_line aml join account_move am " \
										 "on (aml.move_id=am.id and am.state=%s) " \
									   + " where aml.account_id=%s"
						vals = [form['target_move']]
					else:
						search_query = "select aml.id, am.id as j_id, aml.account_id, aml.date, " \
									   "aml.name as label, am.name, " \
									   + "(aml.debit-aml.credit) as balance, aml.debit, aml.credit, aml.partner_id " \
									   + " from account_move_line aml join account_move am on (aml.move_id=am.id) " \
									   + " where aml.account_id=%s"
						vals = []

				if not form['od_with_closing']:
					if form['target_move'] == 'posted':
						search_query = "select aml.id, am.id as j_id, aml.account_id, aml.date," \
									   " aml.name as label, am.name, " \
									   + "(aml.debit-aml.credit) as balance, aml.debit, aml.credit, aml.partner_id " \
									   + " from account_move_line aml join account_move am " \
										 " on (aml.move_id=am.id and am.state=%s) join account_journal aj" \
										 " on (aj.id=am.journal_id)" \
									   + " where aj.od_closing_journal is not true and aml.account_id=%s"
						vals = [form['target_move']]
					else:
						search_query = "select aml.id, am.id as j_id, aml.account_id, aml.date, " \
									   "aml.name as label, am.name, " \
									   + "(aml.debit-aml.credit) as balance, aml.debit, aml.credit, aml.partner_id " \
									   + " from account_move_line aml join account_move am on (aml.move_id=am.id) join account_journal aj" \
										 " on (aj.id=am.journal_id)" \
									   + " where aj.od_closing_journal is not true and aml.account_id=%s"
						vals = []
				# if form['od_with_closing']:
				# 	search_query += " and am.journal_id="
					# vals += [account, form['date_from'], form['date_to']]
				if form['date_from'] and form['date_to']:
					search_query += " and aml.date>=%s and aml.date<=%s"
					vals += [account, form['date_from'], form['date_to']]
				elif form['date_from']:
					search_query += " and aml.date>=%s"
					vals += [account, form['date_from']]
				elif form['date_to']:
					search_query += " and aml.date<=%s"
					vals += [account, form['date_to']]
				else:
					vals += [account]
				print("serrrrr",search_query)
				cr.execute(search_query, tuple(vals))
				items = cr.dictfetchall()

				for j in items:
					temp = j['id']
					j['id'] = re.sub('[^0-9a-zA-Z]+', '', i['name']) + str(
						temp)
					j['p_id'] = str(i['a_id'])
					j['type'] = 'journal_item'
					journal_items.append(j)
		return journal_items

	def _compute_account_balance(self, accounts):
		""" compute the balance, debit
		and credit for the provided accounts
		"""
		mapping = {
			'balance':
				"COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0)"
				" as balance",
			'debit': "COALESCE(SUM(debit), 0) as debit",
			'credit': "COALESCE(SUM(credit), 0) as credit",
		}

		res = {}
		res_ls = []
		for account in accounts:
			res[account.id] = dict((fn, 0.0)
								   for fn in mapping.keys())
		if accounts:
			tables, where_clause, where_params = (
				self.env['account.move.line']._query_get())
			tables = tables.replace(
				'"', '') if tables else "account_move_line"
			wheres = [""]
			if where_clause.strip():
				wheres.append(where_clause.strip())
			filters = " AND ".join(wheres)
			if not self.od_with_closing:
				tables = tables+', account_journal aj'
				filters = filters+"AND aj.od_closing_journal is not true and aj.id=account_move_line__move_id.journal_id"

			request = ("SELECT account_id as id, " +
					   ', '.join(mapping.values()) +
					   " FROM " + tables +
					   " WHERE account_id IN %s " +
					   filters +
					   " GROUP BY account_id")
			params = (tuple(accounts._ids),) + tuple(where_params)
			self.env.cr.execute(request, params)
			for row in self.env.cr.dictfetchall():
				res[row['id']] = row
				res_ls.append(row)
		if self.od_groupby:
			return res_ls
		else:
			return res