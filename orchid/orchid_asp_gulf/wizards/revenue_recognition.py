# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidRevenueRecognition(models.TransientModel):
	_name = 'od.revenue.recognition.wiz'
	_description = "Revenue Recognition Utility"


	date = fields.Date(string="Date", required=True)
	date_from = fields.Date(string="Date From")
	contract_id = fields.Many2one('od.asp.contract', string="Contract")
	partner_id = fields.Many2one('res.partner', string="Customer")
	current_date = fields.Boolean(string="Current Dated")#if true, all entries will be posted as one entry with current date
	revenue_line = fields.One2many('od.revenue.recognition.wiz.line','wiz_id', string="Lines")
	company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
	amount_to_be_posted = fields.Float(string="Amount to be posted")

	@api.onchange('date')
	def onchange_date_from(self):
		for revenue in self:
			if revenue.date:
				revenue.date_from = revenue.date.replace(day=1)
	
	@api.onchange('current_date')
	def onchange_current_date(self):
		for wiz in self:
			if wiz.revenue_line:
				wiz.revenue_line.unlink()

	def search_lines_view(self):
		if self.date:
			where_qry =""" WHERE rlv.due is true AND rlv.invoiced is false AND rlv.recognition_date>=%s AND  rlv.recognition_date<=%s """
			params = [self.date_from, self.date]
			if self.current_date:#if true all entries posted as one and from date is not considered
				domain=[('period_to', '<=', self.date),('invoiced','=',False),('due','=',True)]
			else:#if false  from date is considered and can only post month by month
				domain=[('recognition_date', '>=', self.date_from),('recognition_date', '<=', self.date),('invoiced','=',False),('due','=',True)]#changed on august 1
			if self.partner_id:
				p_domain=('service_id.partner_id', '=', self.partner_id.id)
				domain.append(p_domain)
				where_qry+=""" AND rlv.partner_id IN %s """
				params += [tuple(self.partner_id.ids)]
			if self.contract_id:
				c_domain=('service_id.contract_id', '=', self.contract_id.id)
				domain.append(c_domain)
				where_qry+=""" AND rlv.contract_id IN %s """
				params += [tuple(self.contract_id.ids)]

			qry= """ SELECT rlv.id FROM od_revenue_line_view rlv """+where_qry+""" GROUP BY rlv.id"""
			self._cr.execute(qry,params)
			results = [l[0] for l in self._cr.fetchall()]
			print("results",results)
			if not results:
				raise UserError(_("No Data to Generate !!!"))
			line_ls = []
			credit = 0
			debit = 0
			credit_account=False
			self._cr.execute('''DELETE FROM od_revenue_recognition_report''')
			credit_accounts = {}
			for result in results:
				line_id = self.env['od.contract.monthly.line'].browse(result)
				
				credit_account=line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id and line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id.id or line_id.service_id.contract_line_id.product_id.categ_id.property_account_expense_categ_id and line_id.service_id.contract_line_id.product_id.categ_id.property_account_expense_categ_id.id
				
				if line_id.amount >=0:
					debit = line_id.amount
					credit = 0
				else:
					debit = 0
					credit = abs(line_id.amount)	
				# get the invoice from payment line
				
				payment_lines = self.env['od.contract.payment.line'].search([('period_from','<=',line_id.period_to),('period_to','>=',line_id.period_to),('service_id','=',line_id.service_id.id)])

				invoice_name = ''
				for pl in payment_lines:
					if pl.invoice_line_id:
						invoice_name = invoice_name+pl.invoice_line_id.move_id.name
				line_vals={
				'account_id':line_id.service_id.contract_line_id.product_id.property_account_income_id and line_id.service_id.contract_line_id.product_id.property_account_income_id.id or line_id.service_id.contract_line_id.product_id.categ_id.property_account_income_categ_id and line_id.service_id.contract_line_id.product_id.categ_id.property_account_income_categ_id.id,
				'product_id':line_id.service_id.contract_line_id.product_id.id,
				'partner_id':line_id.service_id.partner_id.id,
				'debit': debit,
				'credit': credit,
				'revenue_line_id':line_id.id,
				'contract_number': line_id.service_id.contract_id.name,
				'name': line_id.service_id.contract_name,
				'company_id': line_id.service_id.contract_id.company_id.id,
				'date': self.date,
				'revenue_date_from': line_id.period_from,
				'revenue_date_to': line_id.period_to,
				'invoice': invoice_name,
				'revenue_account_id':line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id and line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id.id,
				}
				self.env['od.revenue.recognition.report'].create(line_vals)
				if credit_account not in credit_accounts:
					credit_vals={
						'account_id':credit_account,
						'debit':credit if line_id.amount<0 else 0,
						'credit':debit if line_id.amount>=0 else 0,
						'company_id': line_id.service_id.contract_id.company_id.id,
						}
					credit_accounts.update({credit_account:credit_vals})
				else:
					if line_id.amount>=0:
						credit_accounts[credit_account]['credit'] += debit
						credit_accounts[credit_account]['credit'] -= credit
					if line_id.amount<0:
						credit_accounts[credit_account]['debit'] += credit
				
			for credit_account in credit_accounts:
				credit_vals = credit_accounts.get(credit_account)
				self.env['od.revenue.recognition.report'].create(credit_vals)
		return self.env["ir.actions.actions"]._for_xml_id("orchid_asp_gulf.od_revenue_recognition_report_action")
	
	def search_lines(self):
		if self.date:
			where_qry =""" WHERE rlv.due is true AND rlv.invoiced is false AND rlv.recognition_date>=%s AND  rlv.recognition_date<=%s """
			params = [self.date_from, self.date]
			if self.current_date:#if true all entries posted as one and from date is not considered
				domain=[('period_to', '<=', self.date),('invoiced','=',False),('due','=',True)]
			else:#if false  from date is considered and can only post month by month
				
				domain=[('recognition_date', '>=', self.date_from),('recognition_date', '<=', self.date),('invoiced','=',False),('due','=',True)]#changed on august 1 2023


			if self.partner_id:
				p_domain=('service_id.partner_id', '=', self.partner_id.id)
				domain.append(p_domain)
				where_qry+=""" AND rlv.partner_id IN %s """
				params += [tuple(self.partner_id.ids)]
			if self.contract_id:
				c_domain=('service_id.contract_id', '=', self.contract_id.id)
				domain.append(c_domain)
				where_qry+=""" AND rlv.contract_id IN %s """
				params += [tuple(self.contract_id.ids)]
			qry= """ SELECT rlv.id FROM od_revenue_line_view rlv """+where_qry+""" GROUP BY rlv.id"""
			self._cr.execute(qry,params)
			results = [l[0] for l in self._cr.fetchall()]
			if not results:
				raise UserError(_("No Data to Generate !!!"))
			line_ls = []
			credit = 0
			debit = 0
			amount_to_be_posted = 0
			credit_account=False
			if self.revenue_line:
				self.revenue_line.unlink()
			credit_accounts = {}
			for result in results:
				line_id = self.env['od.contract.monthly.line'].browse(result)
				
				credit_account=line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id and line_id.service_id.contract_line_id.product_id.od_property_account_revenue_id.id or line_id.service_id.contract_line_id.product_id.categ_id.property_account_expense_categ_id and line_id.service_id.contract_line_id.product_id.categ_id.property_account_expense_categ_id.id
				
				if line_id.amount >=0:
					debit = line_id.amount
					credit = 0
				else:
					debit = 0
					credit = abs(line_id.amount)				
				line_vals={
				'account_id':line_id.service_id.contract_line_id.product_id.property_account_income_id and line_id.service_id.contract_line_id.product_id.property_account_income_id.id or line_id.service_id.contract_line_id.product_id.categ_id.property_account_income_categ_id and line_id.service_id.contract_line_id.product_id.categ_id.property_account_income_categ_id.id,
				'product_id':line_id.service_id.contract_line_id.product_id.id,
				'partner_id':line_id.service_id.partner_id.id,
				'debit': debit,
				'credit': credit,
				'revenue_line_id':line_id.id,
				}
				w_line=(0,0,line_vals)
				line_ls.append(w_line)
			
				credit_vals={
					'account_id':credit_account,
					'product_id':line_id.service_id.contract_line_id.product_id.id,
					'partner_id':line_id.service_id.partner_id.id,
					'debit':credit if line_id.amount<0 else 0,
					'credit':debit if line_id.amount>=0 else 0,
					}
				amount_to_be_posted += (credit_vals['debit']-credit_vals['credit'])
				w_line=(0,0,credit_vals)
				line_ls.append(w_line)
				

			self.revenue_line=line_ls
			self.amount_to_be_posted = (amount_to_be_posted*(-1))
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.revenue.recognition.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }

	def generate_lines(self):
		if self.revenue_line:
			param_id = self.env['ir.config_parameter'].sudo().search([('key','=','revenue_journal_id')])
			if not param_id:
				raise UserError(_("Please set the 'revenue_journal_id' system parameter"))
			entry_vals={
			'date':self.date,
			'move_type':'entry',
			'currency_id':self.env.company.currency_id.id,
			'journal_id':int(param_id.value),
			}
			entry_id = self.env['account.move'].create(entry_vals)
			mv_line = []
			for line_id in self.revenue_line:
				
				
				line_id.revenue_line_id.move_id=entry_id.id #linking move to corresponding revenue line
				balance=line_id.debit-line_id.credit

				line_vals={
				'account_id':line_id.account_id and line_id.account_id.id,
				'product_id':line_id.product_id and line_id.product_id.id,
				'partner_id':line_id.partner_id and line_id.partner_id.id,
				'debit': balance if balance>=0 else 0,
				'credit': abs(balance) if balance<0 else 0,
				'od_revenue_line_id':line_id.revenue_line_id and line_id.revenue_line_id.id,
				'move_id':entry_id.id,
				}
				w_line=(0,0,line_vals)
				mv_line.append(w_line)
				line_id.revenue_line_id.invoiced=True
			entry_id.line_ids=mv_line
			entry_id.action_post()

			param_id = self.env['ir.config_parameter'].sudo().search([('key','=','od_last_revenue_post_date')])
			print("jjjj",param_id)
			if not param_id:
				raise UserError(_("od_last_revenue_post_date param is not set!!!"))
			param_id.value = entry_id.date
			return {
				'view_type': 'form',
				"view_mode": 'form',
				'res_model': 'account.move',
				'res_id': entry_id.id,
				'type': 'ir.actions.act_window',
				}

class OrchidRevenueRecognitionLine(models.TransientModel):
	_name = 'od.revenue.recognition.wiz.line'
	_description = "Revenue Recognition Wiz Lines"

	wiz_id=fields.Many2one('od.revenue.recognition.wiz', string="Wizard", ondelete='cascade')
	revenue_line_id = fields.Many2one('od.contract.monthly.line', string="Revenue Line")
	partner_id = fields.Many2one('res.partner', string="Partner")
	product_id = fields.Many2one('product.product', string="Product")
	account_id = fields.Many2one('account.account', string="Account")
	company_id = fields.Many2one('res.company', string="Company", related="wiz_id.company_id")
	company_currency_id = fields.Many2one('res.currency',string='Company Currency', readonly=True, related='company_id.currency_id')
	debit = fields.Monetary(string='Debit', currency_field='company_currency_id')
	credit = fields.Monetary(string='Credit', currency_field='company_currency_id')

