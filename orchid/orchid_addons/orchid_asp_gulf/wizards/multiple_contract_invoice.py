# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pandas as pd
import datetime
from datetime import datetime

class OrchidCreateContractAll(models.TransientModel):
	_name = 'od.contract.invoice.wiz.all'
	_description = "Create Invoice For Multiple Contracts"

	date = fields.Date(string="Due Date")
	invoice_date = fields.Date(string="Invoice Date")
	contract_id = fields.Many2one('od.asp.contract', string="Contract")
	partner_id = fields.Many2one('res.partner', string="Customer")
	invoice_line = fields.One2many('od.contract.invoice.wiz.line.all','wiz_id', string="Lines")

	@api.onchange('date')
	def onchange_date(self):
		if self.date:
			self.invoice_date = self.date
	def search_lines(self):
		if self.date:
			if self.invoice_line:
				self.invoice_line.unlink()
			wiz_lines=[]
			# getting all contract lines with next invoice date <= given date
			domain=[('next_invoice_date', '<=', self.date)]
			if self.partner_id:
				p_domain=('order_id.partner_id', '=', self.partner_id.id)
				domain.append(p_domain)
			if self.contract_id:
				c_domain=('order_id', '=', self.contract_id.id)
				domain.append(c_domain)
			for line in self.env['od.asp.contract.line'].search(domain):
				#normal cases---invoice after activation
				if line.state=='active':
					# if (line.product_id.categ_id.id!=40 or line.frequency>1):
					tax_ls=[t.id for t in line.tax_id]
					print("taxxxxxxsearcccc",tax_ls)
					# if line.frequency!=1:no probs if there is paymnt line for freq 1
					get_lines=('''SELECT pl.id FROM od_contract_payment_line pl, od_contract_payment cp
					WHERE  cp.contract_line_id=%s AND pl.service_id=cp.id AND pl.invoiced is not true AND pl.period_from<='%s' AND cp.states='active' ''')%(line.id,self.date)
					self._cr.execute(get_lines)
					results = self._cr.fetchall()
					print("resrrrrr",results)
					if results:
						results = [z[0] for z in results]
						for result in results:
							payment_line = self.env['od.contract.payment.line'].browse(result)
							print("ppppp")
							vals = {
							'wiz_id':self.id,
							'contract_line_id':line.id,
							'invoice_date':payment_line.period_from,
							'amount_to_invoice':payment_line.amount,
							# 'amount':line.price_total,changed here for vat case
							'amount':line.price_subtotal,
							'payment_line':payment_line.id,
							'contract_id':line.order_id.id,
							'customer_id':line.order_id.partner_id.id,
							'contract_name':line.order_id.contract_code,
							'tax_id':[(6,0,tax_ls)],
							}
							if line.billing_cycle == 'annually':
								vals['amount'] = payment_line.amount
							self.env['od.contract.invoice.wiz.line.all'].create(vals)
					# else:
					# 	if not line.invoice_line_ids:
					# 		vals = {
					# 				'wiz_id':self.id,
					# 				'contract_line_id':line.id,
					# 				'invoice_date':line.next_invoice_date,
					# 				# 'amount_to_invoice':line.price_total,changed here for vat case
					# 				'amount_to_invoice':line.price_subtotal,
					# 				# 'amount':line.price_total,changed here for vat case
					# 				'amount':line.price_subtotal,
					# 				'contract_id':line.order_id.id,
					# 				'customer_id':line.order_id.partner_id.id,
					# 				'contract_name':line.order_id.contract_code,
					# 				'tax_id':[(6,0,tax_ls)],
					# 				}	
					# 		self.env['od.contract.invoice.wiz.line.all'].create(vals)
				# elif line.state=='draft' and not line.effective_date:
				# 	#special case ---invoice before activation
				# 	# if (line.product_id.categ_id.id==40 and not line.invoice_line_ids) or line.product_id.categ_id.id!=40:
				# 	if line.product_id.categ_id.id==40 and not line.invoice_line_ids:
				# 		vals = {
				# 				'wiz_id':self.id,
				# 				'contract_line_id':line.id,
				# 				'invoice_date':line.next_invoice_date,
				# 				'amount_to_invoice':0,
				# 				'amount':line.price_total,
				# 				'contract_id':line.order_id.id,
				# 				}
				# 		self.env['od.contract.invoice.wiz.line.all'].create(vals)
			if not self.invoice_line:
				raise UserError(_("No Invoiceable Lines !!!"))
			return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.contract.invoice.wiz.all',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }

	
	# def create_invoice(self):
	# 	print("innnnnnnnnnnn")
	# 	# getting lines from wizard group by partner
	# 	# get_invoice_vals = ('''SELECT c.partner_id as partner,c.currency_id as currency,c.od_exchange_rate as rate, c.payment_term_id as payment_term_id FROM od_contract_invoice_wiz_line_all l, od_asp_contract c
	# 	# 				  WHERE l.contract_id=c.id and l.wiz_id=%s Group BY c.partner_id,c.currency_id,c.od_exchange_rate,c.payment_term_id''')%(self.id)
	# 	# need contract wise invoice hence commentec above
	# 	get_invoice_vals = ('''SELECT c.id as contract,c.partner_id as partner,c.currency_id as currency,c.od_exchange_rate as rate, c.payment_term_id as payment_term_id FROM od_contract_invoice_wiz_line_all l, od_asp_contract c
	# 					  WHERE l.contract_id=c.id and l.wiz_id=%s Group BY c.id,c.partner_id,c.currency_id,c.od_exchange_rate,c.payment_term_id''')%(self.id)
	# 	self._cr.execute(get_invoice_vals)
	# 	partners_currency = self._cr.dictfetchall()
	# 	if partners_currency:
	# 		# partners = [z[0] for z in partners]
	# 		invoice_ids = []
	# 		for pc_vals in partners_currency:
	# 			user_id=self.env.user.id
	# 			partner_id = self.env['res.partner'].browse(pc_vals['partner'])
	# 			contract_id=self.env['od.asp.contract'].browse(pc_vals['contract'])
	# 			invoice_vals={
	# 			'od_contract_id': pc_vals['contract'],
	# 			'partner_id': pc_vals['partner'],
	# 			'journal_id': self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal().id,
	# 			'invoice_origin': 'Contract Bulk '+str(self.date),
	# 			'invoice_user_id': partner_id.user_id and partner_id.user_id.id or user_id,
	# 			'move_type':'out_invoice',
	# 			'invoice_date':self.invoice_date,
	# 			'currency_id':pc_vals['currency'],
	# 			'invoice_payment_term_id':pc_vals['payment_term_id'],
	# 			'od_exchange_rate':pc_vals['rate'],
	# 			'date':self.invoice_date,
	# 			'partner_bank_id':1,
	# 			'ref':contract_id.client_order_ref,
	# 			'payment_reference':contract_id.client_order_ref,
	# 			'od_contact_id':contract_id.contact_id and contract_id.contact_id.id,

	# 			}
	# 			invoice_id = self.env['account.move'].create(invoice_vals)
	# 			invoice_id.od_contract_name=invoice_id.od_contract_id.contract_code
	# 			invoice_id.od_onchange_exchange_rate()
	# 			invoice_ids.append(invoice_id.id)
	# 			invoice_lines=[]
	# 			pdt_lines=[]
	# 			flitered_line=self.invoice_line.filtered(lambda r: r.contract_id.partner_id.id ==pc_vals['partner'] and r.contract_id.id==pc_vals['contract'])
	# 			print(flitered_line)
	# 			# fluctuated_line=flitered_line.filtered(lambda r: r.payment_line.service_id.fluctuating_contract==True)
	# 			fluctuated_line=[z for z in flitered_line if z.payment_line.service_id.fluctuating_contract==True]
	# 			print("fluct",fluctuated_line)
	# 			parent_lines =[z for z in flitered_line if any(z.contract_line_id.id==fl.contract_line_id.flctng_parent_contract_line_id.id for fl in fluctuated_line)]
	# 			print("pppare",parent_lines)
	# 			# fluctuated_line=[z for z in fluctuated_line if (z.contract_line_id.flctng_parent_contract_line_id.id==pl.contract_line_id.id and pl.payment_line.period_from==z.payment_line.period_from 
	# 			# 	and pl.payment_line.period_to==z.payment_line.period_to and pl.contract_line_id.product_id.id==z.contract_line_id.product_id.id for pl in parent_lines)]
				
	# 			fluct_lines = []
	# 			for fl in fluctuated_line:
	# 				for pl in parent_lines:
	# 					if fl.contract_line_id.flctng_parent_contract_line_id.id==pl.contract_line_id.id and pl.payment_line.period_from==fl.payment_line.period_from and pl.payment_line.period_to==fl.payment_line.period_to and pl.contract_line_id.product_id.id==fl.contract_line_id.product_id.id:
	# 						fluct_lines.append(fl)
	# 			fluctuated_line=fluct_lines
							
	# 			print("flucttttttttttttt",fluctuated_line)
	# 			group_lines=[]
	# 			for pl in parent_lines:
	# 				group_dict={'parent_line':pl}
	# 				child_ls=[]
	# 				for fl in fluctuated_line:
	# 					if fl.contract_line_id.flctng_parent_contract_line_id.id==pl.contract_line_id.id and pl.payment_line.period_from==fl.payment_line.period_from and pl.payment_line.period_to==fl.payment_line.period_to and pl.contract_line_id.product_id.id==fl.contract_line_id.product_id.id and pl.contract_line_id.billing_cycle==fl.contract_line_id.billing_cycle: 
	# 						child_ls.append(fl)
	# 				group_dict['child_ls']=child_ls
	# 				group_lines.append(group_dict)
	# 			non_group_lines=[z for z in flitered_line if (z not in fluctuated_line and z not in parent_lines)]
	# 			print("drggg",group_lines)
	# 			print("kooo",non_group_lines)
	# 			# print(s)
	# 			# for line in self.invoice_line.filtered(lambda r: r.contract_id.partner_id.id ==pc_vals['partner'] and r.contract_id.id==pc_vals['contract']):
	# 			for line in non_group_lines:
	# 				if line.contract_line_id.product_uom_qty==0:
	# 					raise UserError(_("The Quantity should be non-zero!! Refer the line for contract '%s' ")%(line.contract_id.name))
	# 				tax_ls=[t.id for t in line.tax_id]
	# 				print("taxxxxxx",tax_ls)
	# 				no_freq_months=1
	# 				if line.payment_line.period_from and line.payment_line.period_to:
	# 					freq_start_date = line.payment_line.period_from
	# 					freq_end_date = line.payment_line.period_to
	# 					freq_months = pd.date_range(freq_start_date, freq_end_date, freq='M')
	# 					no_freq_months=len(freq_months)
	# 				if no_freq_months==0:
	# 					no_freq_months=1
					
	# 				vals={
	# 				'product_id':line.contract_line_id.product_id.id,
	# 				# 'quantity':no_freq_months,
	# 				'quantity':line.contract_line_id.product_uom_qty,
	# 				'move_id':invoice_id.id,
	# 				'display_type':False,
	# 				'name':line.contract_line_id.product_id.name,
	# 				'od_period_from':line.payment_line.period_from,
	# 				'od_period_to':line.payment_line.period_to,
	# 				'price_unit':(line.amount_to_invoice/(no_freq_months or 1.0))/line.contract_line_id.product_uom_qty,
	# 				'tax_ids':[(6,0,tax_ls)],
	# 				'od_contract_line_id':[(6,0,line.contract_line_id.ids)],
	# 				'name':line.contract_line_id.name,
	# 				'analytic_account_id':line.contract_id.analytic_account_id.id or False,
	# 				'od_frequency':no_freq_months,
	# 				}
	# 				# onetime case change
	# 				if line.payment_line.service_id.billing_cycle=='one_time':
	# 					vals['quantity']=line.contract_line_id.product_uom_qty
	# 					vals['price_unit']=(line.amount_to_invoice/line.contract_line_id.product_uom_qty)/line.contract_line_id.frequency
	# 					vals['od_frequency']=line.contract_line_id.frequency
	# 				# annual case change
	# 				if line.payment_line.service_id.billing_cycle=='annually':
	# 					vals['quantity']=line.contract_line_id.product_uom_qty
	# 					vals['price_unit']=line.amount_to_invoice/line.contract_line_id.product_uom_qty
	# 					vals['od_frequency']=1

	# 				print("valssssss",vals)
	# 				# print(s)
	# 				if vals['price_unit']==0:
	# 					raise UserError(_("The Price Unit should be non-zero!! Refer the line for contract '%s' ")%(line.contract_id.name))
	# 				w_line=(0,0,vals)
	# 				invoice_lines.append(w_line)

	# 			for line_dict in group_lines:
	# 				print("hereeeeeeeeeeeeeecccc")
	# 				line=line_dict['parent_line']
	# 				if line.contract_line_id.product_uom_qty==0:
	# 					raise UserError(_("The Quantity should be non-zero!! Refer the line for contract '%s' ")%(line.contract_id.name))
	# 				tax_ls=[t.id for t in line.tax_id]
	# 				contract_line_ls=[line.contract_line_id.id]
	# 				amount_to_invoice=line.amount_to_invoice
	# 				print("amtto invvv",amount_to_invoice)
	# 				description = line.contract_line_id.name

	# 				for child_line in line_dict['child_ls']:
	# 					print("chiiii",child_line)
	# 					for t in child_line.tax_id:
	# 						tax_ls.append(t.id)
	# 					# get fluctuated_contract_id
	# 					fluctuated_contract_id = self.env['od.fluctuating.contract'].search([('new_contract_line_id','=',child_line.contract_line_id.id)])
	# 					# description = child_line.contract_line_id.name
	# 					print("kpppppppp",fluctuated_contract_id,fluctuated_contract_id.inv_desc)
	# 					description = fluctuated_contract_id.inv_desc
	# 					print("pppppp",description)
	# 					amount_to_invoice=amount_to_invoice+child_line.amount_to_invoice
	# 					contract_line_ls.append(child_line.contract_line_id.id)
	# 				tax_ls=list(set(tax_ls))
	# 				print("amtto invvv",amount_to_invoice)
	# 				print("taxxxxxx",tax_ls)
	# 				no_freq_months=1
	# 				if line.payment_line.period_from and line.payment_line.period_to:
	# 					freq_start_date = line.payment_line.period_from
	# 					freq_end_date = line.payment_line.period_to
	# 					freq_months = pd.date_range(freq_start_date, freq_end_date, freq='M')
	# 					no_freq_months=len(freq_months)
	# 				if no_freq_months==0:
	# 					no_freq_months=1
					
	# 				print("oiii",description)
	# 				vals={
	# 				'product_id':line.contract_line_id.product_id.id,
	# 				'quantity':line.contract_line_id.product_uom_qty,
	# 				'move_id':invoice_id.id,
	# 				'display_type':False,
	# 				# 'name':line.contract_line_id.product_id.name,
	# 				'od_period_from':line.payment_line.period_from,
	# 				'od_period_to':line.payment_line.period_to,
	# 				'price_unit':(amount_to_invoice/(no_freq_months or 1.0))/line.contract_line_id.product_uom_qty,
	# 				'tax_ids':[(6,0,tax_ls)],
	# 				'od_contract_line_id':[(6,0,contract_line_ls)],
	# 				'name':description,
	# 				'analytic_account_id':line.contract_id.analytic_account_id.id or False,
	# 				'od_frequency':no_freq_months,
	# 				}
	# 				# onetime case change
	# 				if line.payment_line.service_id.billing_cycle=='one_time':
	# 					vals['quantity']=line.contract_line_id.product_uom_qty
	# 					vals['price_unit']=(amount_to_invoice/line.contract_line_id.product_uom_qty)/line.contract_line_id.frequency
	# 					vals['od_frequency']=line.contract_line_id.frequency
	# 				# annual case change
	# 				if line.payment_line.service_id.billing_cycle=='annually':
	# 					vals['quantity']=line.contract_line_id.product_uom_qty
	# 					vals['price_unit']=line.amount_to_invoice/line.contract_line_id.product_uom_qty
	# 					vals['od_frequency']=1
	# 				print("valssssss",vals)
	# 				# print(s)
	# 				if vals['price_unit']==0:
	# 					raise UserError(_("The Price Unit should be non-zero!! Refer the line for contract '%s' ")%(line.contract_id.name))
	# 				w_line=(0,0,vals)
	# 				invoice_lines.append(w_line)











	# 			print(invoice_lines)
	# 			# print(s)
	# 			print("!!!!!")
	# 			invoice_id.invoice_line_ids = invoice_lines
	# 			print("???????????")
	# 			invoice_id.post()
	# 			for line in self.invoice_line.filtered(lambda r: r.contract_id.partner_id.id == pc_vals['partner'] and r.contract_id.id==pc_vals['contract']):
	# 				print("jokkkkkkkkkkk")
	# 				inv_line_id = invoice_id.invoice_line_ids.search([('od_contract_line_id','=',line.contract_line_id.id),('od_period_from','=',line.payment_line.period_from),('od_period_to','=',line.payment_line.period_to),('move_id.payment_state','!=','reversed'),('move_id.move_type','=','out_invoice')])
	# 				print("invoiceeeee",line.payment_line.period_from,line.payment_line.period_to,inv_line_id,invoice_id)
	# 				c_line_inv_ids=[ivl.id for ivl in line.contract_line_id.invoice_line_ids]
	# 				c_line_inv_ids.append(inv_line_id.id)
	# 				c_line_inv_ids = list(set(c_line_inv_ids))
	# 				line.contract_line_id.invoice_line_ids = [(6,0,c_line_inv_ids)]#linking invoice line to contract line
	# 				if line.payment_line:
	# 					line.payment_line.invoice_line_id = inv_line_id.id#linking invoice line to payment table line for the active contracts
	# 					line.payment_line.invoiced=True
	# 					get_lines=('''SELECT pl.id FROM od_contract_payment_line pl, od_contract_payment cp
	# 						WHERE cp.contract_line_id=%s AND pl.service_id=cp.id AND pl.invoiced is not true and pl.period_from>'%s' and cp.states='active' order by period_from limit 1''')%(line.contract_line_id.id,line.invoice_date)
						
	# 					self._cr.execute(get_lines)
	# 					results = self._cr.fetchall()
	# 					if results:
	# 						results = [z[0] for z in results]
	# 						next_payment_line=self.env['od.contract.payment.line'].browse(results)
	# 						line.contract_line_id.next_invoice_date = next_payment_line.period_from#updating next payment date
	# 					get_revenue_lines = ('''UPDATE  od_contract_monthly_line pl set due=true FROM od_contract_payment cp
	# 						WHERE cp.contract_line_id=%s AND pl.service_id=cp.id AND pl.invoiced is not true and pl.period_from>='%s' AND  pl.period_to<='%s' and cp.states='active' ''')%(line.contract_line_id.id,line.payment_line.period_from,line.payment_line.period_to)
	# 					self._cr.execute(get_revenue_lines)


	# 	invoices = invoice_ids
	# 	action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
	# 	if len(invoices) > 1:
	# 		action['domain'] = [('id', 'in', invoices)]
	# 	elif len(invoices) == 1:
	# 		form_view = [(self.env.ref('account.view_move_form').id, 'form')]
	# 		if 'views' in action:
	# 			action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
	# 		else:
	# 			action['views'] = form_view
	# 		action['res_id'] = invoices[0]
	# 	else:
	# 		action = {'type': 'ir.actions.act_window_close'}

	# 	context = {
	# 		'default_move_type': 'out_invoice',
	# 	}
	# 	action['context'] = context
	# 	return action


	def create_invoice(self):
		print("innnnnnnnnnnn")
		# getting lines from wizard group by partner
		# get_invoice_vals = ('''SELECT c.partner_id as partner,c.currency_id as currency,c.od_exchange_rate as rate, c.payment_term_id as payment_term_id FROM od_contract_invoice_wiz_line_all l, od_asp_contract c
		# 				  WHERE l.contract_id=c.id and l.wiz_id=%s Group BY c.partner_id,c.currency_id,c.od_exchange_rate,c.payment_term_id''')%(self.id)
		# need contract wise invoice hence commentec above
		get_invoice_vals = ('''SELECT c.id as contract,c.partner_id as partner,c.currency_id as currency,c.od_exchange_rate as rate, c.payment_term_id as payment_term_id FROM od_contract_invoice_wiz_line_all l, od_asp_contract c
						  WHERE l.contract_id=c.id and l.wiz_id=%s Group BY c.id,c.partner_id,c.currency_id,c.od_exchange_rate,c.payment_term_id''')%(self.id)
		self._cr.execute(get_invoice_vals)
		partners_currency = self._cr.dictfetchall()
		if partners_currency:
			# partners = [z[0] for z in partners]
			invoice_ids = []
			for pc_vals in partners_currency:
				user_id=self.env.user.id
				partner_id = self.env['res.partner'].browse(pc_vals['partner'])
				contract_id=self.env['od.asp.contract'].browse(pc_vals['contract'])
				invoice_vals={
				'od_contract_id': pc_vals['contract'],
				'partner_id': pc_vals['partner'],
				'journal_id': self.env['account.move'].with_context(default_move_type='out_invoice')._get_default_journal().id,
				'invoice_origin': 'Contract Bulk '+str(self.date),
				'invoice_user_id': partner_id.user_id and partner_id.user_id.id or user_id,
				'move_type':'out_invoice',
				'invoice_date':self.invoice_date,
				'currency_id':pc_vals['currency'],
				'invoice_payment_term_id':pc_vals['payment_term_id'],
				'od_exchange_rate':pc_vals['rate'],
				'date':self.invoice_date,
				'partner_bank_id':3,
				'ref':contract_id.client_order_ref,
				'payment_reference':contract_id.client_order_ref,
				'od_contact_id':contract_id.contact_id and contract_id.contact_id.id,

				}
				invoice_id = self.env['account.move'].create(invoice_vals)
				invoice_id.od_contract_name=invoice_id.od_contract_id.contract_code
				invoice_id.od_onchange_exchange_rate()
				invoice_ids.append(invoice_id.id)
				invoice_lines=[]
				pdt_lines=[]
				flitered_line=self.invoice_line.filtered(lambda r: r.contract_id.partner_id.id ==pc_vals['partner'] and r.contract_id.id==pc_vals['contract'])
				print(flitered_line)
				# fluctuated_line=flitered_line.filtered(lambda r: r.payment_line.service_id.fluctuating_contract==True)
				fluctuated_line=[z for z in flitered_line if z.payment_line.service_id.fluctuating_contract==True]
				print("fluct",fluctuated_line)
				parent_lines =[z for z in flitered_line if any(z.contract_line_id.id==fl.contract_line_id.flctng_parent_contract_line_id.id for fl in fluctuated_line)]
				print("pppare",parent_lines)
				# fluctuated_line=[z for z in fluctuated_line if (z.contract_line_id.flctng_parent_contract_line_id.id==pl.contract_line_id.id and pl.payment_line.period_from==z.payment_line.period_from 
				# 	and pl.payment_line.period_to==z.payment_line.period_to and pl.contract_line_id.product_id.id==z.contract_line_id.product_id.id for pl in parent_lines)]
				
				fluct_lines = []
				for fl in fluctuated_line:
					for pl in parent_lines:
						if fl.contract_line_id.flctng_parent_contract_line_id.id==pl.contract_line_id.id and pl.payment_line.period_from==fl.payment_line.period_from and pl.payment_line.period_to==fl.payment_line.period_to and pl.contract_line_id.product_id.id==fl.contract_line_id.product_id.id:
							fluct_lines.append(fl)
				fluctuated_line=fluct_lines
							
				print("flucttttttttttttt",fluctuated_line)
				group_lines=[]
				for pl in parent_lines:
					group_dict={'parent_line':pl}
					child_ls=[]
					for fl in fluctuated_line:
						if fl.contract_line_id.flctng_parent_contract_line_id.id==pl.contract_line_id.id and pl.payment_line.period_from==fl.payment_line.period_from and pl.payment_line.period_to==fl.payment_line.period_to and pl.contract_line_id.product_id.id==fl.contract_line_id.product_id.id and pl.contract_line_id.billing_cycle==fl.contract_line_id.billing_cycle: 
							child_ls.append(fl)
					group_dict['child_ls']=child_ls
					group_lines.append(group_dict)
				non_group_lines=[z for z in flitered_line if (z not in fluctuated_line and z not in parent_lines)]
				print("drggg",group_lines)
				print("kooo",non_group_lines)
				# print(s)
				# for line in self.invoice_line.filtered(lambda r: r.contract_id.partner_id.id ==pc_vals['partner'] and r.contract_id.id==pc_vals['contract']):
				for line in non_group_lines:
					if line.contract_line_id.product_uom_qty==0:
						raise UserError(_("The Quantity should be non-zero!! Refer the line for contract '%s' ")%(line.contract_id.name))
					tax_ls=[t.id for t in line.tax_id]
					print("taxxxxxx",tax_ls)
					no_freq_months=1
					if line.payment_line.period_from and line.payment_line.period_to:
						freq_start_date = line.payment_line.period_from
						freq_end_date = line.payment_line.period_to
						freq_months = pd.date_range(freq_start_date, freq_end_date, freq='M')
						no_freq_months=len(freq_months)
					if no_freq_months==0:
						no_freq_months=1
					
					vals={
					'product_id':line.contract_line_id.product_id.id,
					# 'quantity':no_freq_months,
					'quantity':line.contract_line_id.product_uom_qty,
					'move_id':invoice_id.id,
					'display_type':False,
					'name':line.contract_line_id.product_id.name,
					'od_period_from':line.payment_line.period_from,
					'od_period_to':line.payment_line.period_to,
					'price_unit':(line.amount_to_invoice/(no_freq_months or 1.0))/line.contract_line_id.product_uom_qty,
					'tax_ids':[(6,0,tax_ls)],
					'od_contract_line_id':[(6,0,line.contract_line_id.ids)],
					'name':line.contract_line_id.name,
					'analytic_account_id':line.contract_id.analytic_account_id.id or False,
					'od_frequency':no_freq_months,
					}
					# onetime case change
					if line.payment_line.service_id.billing_cycle=='one_time':
						vals['quantity']=line.contract_line_id.product_uom_qty
						vals['price_unit']=(line.amount_to_invoice/line.contract_line_id.product_uom_qty)/line.contract_line_id.frequency
						vals['od_frequency']=line.contract_line_id.frequency
					# annual case change
					if line.payment_line.service_id.billing_cycle=='annually':
						vals['quantity']=line.contract_line_id.product_uom_qty
						vals['price_unit']=line.amount_to_invoice/line.contract_line_id.product_uom_qty
						vals['od_frequency']=1

					print("valssssss",vals)
					# print(s)
					if vals['price_unit']==0:
						raise UserError(_("The Price Unit should be non-zero!! Refer the line for contract '%s' ")%(line.contract_id.name))
					w_line=(0,0,vals)
					invoice_lines.append(w_line)

				for line_dict in group_lines:
					print("hereeeeeeeeeeeeeecccc")
					line=line_dict['parent_line']
					if line.contract_line_id.product_uom_qty==0:
						raise UserError(_("The Quantity should be non-zero!! Refer the line for contract '%s' ")%(line.contract_id.name))
					tax_ls=[t.id for t in line.tax_id]
					contract_line_ls=[line.contract_line_id.id]
					amount_to_invoice=line.amount_to_invoice
					product_uom_qty = line.contract_line_id.product_uom_qty
					print("amtto invvv",amount_to_invoice)
					description = line.contract_line_id.name

					actual_quantity = line.contract_line_id.product_uom_qty

					for child_line in line_dict['child_ls']:
						print("chiiii",child_line)
						for t in child_line.tax_id:
							tax_ls.append(t.id)
						# get fluctuated_contract_id
						# fluctuated_contract_id = self.env['od.fluctuating.contract'].search([('new_contract_line_id','=',child_line.contract_line_id.id)])
						fluctuated_contract_id = self.env['od.fluctuating.contract.line'].search([('new_contract_line_id','=',child_line.contract_line_id.id)])
						# description = child_line.contract_line_id.name
						# print("kpppppppp",fluctuated_contract_id,fluctuated_contract_id.inv_desc)
						if fluctuated_contract_id.new_desc:
							description = fluctuated_contract_id.new_desc
						print("pppppp",description)
						amount_to_invoice=amount_to_invoice+child_line.amount_to_invoice
						product_uom_qty = product_uom_qty + child_line.contract_line_id.product_uom_qty# changed here to crct unit price
						actual_quantity = fluctuated_contract_id.new_qty
						contract_line_ls.append(child_line.contract_line_id.id)
					tax_ls=list(set(tax_ls))
					print("amtto invvv",amount_to_invoice)
					print("taxxxxxx",tax_ls)
					no_freq_months=1
					if line.payment_line.period_from and line.payment_line.period_to:
						freq_start_date = line.payment_line.period_from
						freq_end_date = line.payment_line.period_to
						freq_months = pd.date_range(freq_start_date, freq_end_date, freq='M')
						no_freq_months=len(freq_months)
					if no_freq_months==0:
						no_freq_months=1
					
					print("oiii",description)
					vals={
					'product_id':line.contract_line_id.product_id.id,
					# 'quantity':line.contract_line_id.product_uom_qty,
					'quantity':actual_quantity,
					'move_id':invoice_id.id,
					'display_type':False,
					# 'name':line.contract_line_id.product_id.name,
					'od_period_from':line.payment_line.period_from,
					'od_period_to':line.payment_line.period_to,
					# 'price_unit':(amount_to_invoice/(no_freq_months or 1.0))/line.contract_line_id.product_uom_qty,
					'price_unit':(amount_to_invoice/(no_freq_months or 1.0))/product_uom_qty,
					'tax_ids':[(6,0,tax_ls)],
					'od_contract_line_id':[(6,0,contract_line_ls)],
					'name':description,
					'analytic_account_id':line.contract_id.analytic_account_id.id or False,
					'od_frequency':no_freq_months,
					}
					# onetime case change
					if line.payment_line.service_id.billing_cycle=='one_time':
						# vals['quantity']=line.contract_line_id.product_uom_qty
						vals['quantity']=actual_quantity
						vals['price_unit']=(amount_to_invoice/product_uom_qty)/line.contract_line_id.frequency
						vals['od_frequency']=line.contract_line_id.frequency
					# annual case change
					if line.payment_line.service_id.billing_cycle=='annually':
						# vals['quantity']=line.contract_line_id.product_uom_qty
						vals['quantity']=actual_quantity
						vals['price_unit']=line.amount_to_invoice/product_uom_qty
						vals['od_frequency']=1
					print("valssssss",vals)
					# print(s)
					if vals['price_unit']==0:
						raise UserError(_("The Price Unit should be non-zero!! Refer the line for contract '%s' ")%(line.contract_id.name))
					w_line=(0,0,vals)
					invoice_lines.append(w_line)











				print(invoice_lines)
				# print(s)
				print("!!!!!")
				invoice_id.invoice_line_ids = invoice_lines
				print("???????????")
				invoice_id.post()
				for line in self.invoice_line.filtered(lambda r: r.contract_id.partner_id.id == pc_vals['partner'] and r.contract_id.id==pc_vals['contract']):
					print("jokkkkkkkkkkk",line,line.contract_line_id.name,line.payment_line)
					inv_line_id = invoice_id.invoice_line_ids.search([('od_contract_line_id','=',line.contract_line_id.id),('od_period_from','=',line.payment_line.period_from),('od_period_to','=',line.payment_line.period_to),('move_id.payment_state','!=','reversed'),('move_id.move_type','=','out_invoice')])
					print("invoiceeeee",line.payment_line.period_from,line.payment_line.period_to,inv_line_id,invoice_id)
					c_line_inv_ids=[ivl.id for ivl in line.contract_line_id.invoice_line_ids]
					c_line_inv_ids.append(inv_line_id.id)
					c_line_inv_ids = list(set(c_line_inv_ids))
					line.contract_line_id.invoice_line_ids = [(6,0,c_line_inv_ids)]#linking invoice line to contract line
					if line.payment_line:
						line.payment_line.invoice_line_id = inv_line_id.id#linking invoice line to payment table line for the active contracts
						line.payment_line.invoiced=True
						get_lines=('''SELECT pl.id FROM od_contract_payment_line pl, od_contract_payment cp
							WHERE cp.contract_line_id=%s AND pl.service_id=cp.id AND pl.invoiced is not true and pl.period_from>'%s' and cp.states='active' order by period_from limit 1''')%(line.contract_line_id.id,line.invoice_date)
						
						self._cr.execute(get_lines)
						results = self._cr.fetchall()
						if results:
							results = [z[0] for z in results]
							next_payment_line=self.env['od.contract.payment.line'].browse(results)
							line.contract_line_id.next_invoice_date = next_payment_line.period_from#updating next payment date
						
						# dbt @28 dec 2022
						# get_revenue_lines = ('''UPDATE  od_contract_monthly_line pl set due=true FROM od_contract_payment cp
						# 	WHERE cp.contract_line_id=%s AND pl.service_id=cp.id AND pl.invoiced is not true and pl.period_from>='%s' AND  pl.period_to<='%s' and cp.states='active' ''')%(line.contract_line_id.id,line.payment_line.period_from,line.payment_line.period_to)
						# self._cr.execute(get_revenue_lines)
						# date update
						print("invvvvvvtttttt",invoice_id.invoice_date, type(invoice_id.invoice_date))
						# # datetime_obj = invoice_id.invoice_date.strftime("%Y-%m-%d")
						# # print("srfff",datetime_obj)
						# datetime_obj = datetime.strptime(str(invoice_id.invoice_date),"%Y-%m-%d")
						# print("datetimeee",datetime_obj,type(datetime_obj))
						# print("datetimeee",type(datetime_obj.date()))
						# datetime_obj = datetime_obj
						# get_revenue_lines_date = ('''UPDATE  od_contract_monthly_line pl set due=true, invoice_date='%s', invoice_line_id=%s FROM od_contract_payment cp
						# 	WHERE cp.contract_line_id=%s AND pl.service_id=cp.id AND pl.invoiced is not true 
						# 	and pl.period_from<='%s' AND invoice_line_id is null
						# 	and cp.states='active' ''')%(invoice_id.invoice_date,inv_line_id.id,line.contract_line_id.id,invoice_id.invoice_date)

						# get_revenue_lines_date = ('''UPDATE  od_contract_monthly_line pl set due=true, invoice_date='%s', invoice_line_id=%s FROM od_contract_payment cp
						# 	WHERE cp.contract_line_id=%s AND pl.service_id=cp.id AND pl.invoiced is not true 
						# 	and pl.period_from<='%s' AND invoice_line_id is null
						# 	and cp.states='active' ''')%(inv_line_id.od_period_to,inv_line_id.id,line.contract_line_id.id,invoice_id.invoice_date)
						# get_revenue_lines_date = ('''UPDATE  od_contract_monthly_line pl set due=true, invoice_date='%s', invoice_line_id=%s FROM od_contract_payment cp
						# 	WHERE cp.contract_line_id=%s AND pl.service_id=cp.id AND pl.invoiced is not true 
						# 	and pl.period_from<='%s' AND invoice_line_id is null
						# 	and cp.states='active' ''')%(invoice_id.invoice_date,inv_line_id.id,line.contract_line_id.id,invoice_id.invoice_date)
						# print("jjjjjkk",get_revenue_lines_date)
						# self._cr.execute(get_revenue_lines_date)
						line.payment_line.update_monthly_lines_details()



		invoices = invoice_ids
		action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
		if len(invoices) > 1:
			action['domain'] = [('id', 'in', invoices)]
		elif len(invoices) == 1:
			form_view = [(self.env.ref('account.view_move_form').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
			action['res_id'] = invoices[0]
		else:
			action = {'type': 'ir.actions.act_window_close'}

		context = {
			'default_move_type': 'out_invoice',
		}
		action['context'] = context
		return action


class OrchidCreateContractLineAll(models.TransientModel):
	_name = 'od.contract.invoice.wiz.line.all'
	_description = "Multiple Contracts Invoice Wiz Lines"
	_order = 'contract_id'

	wiz_id=fields.Many2one('od.contract.invoice.wiz.all', string="Wizard", ondelete='cascade')
	contract_line_id = fields.Many2one('od.asp.contract.line', string="Service Line")
	contract_id = fields.Many2one('od.asp.contract', string="Contract")
	invoice_date = fields.Date(string="Due Date")
	amount_to_invoice = fields.Float(digits='Product Price', string="Invoice Amount")
	amount = fields.Float(digits='Product Price', string="Total Amount")
	payment_line = fields.Many2one('od.contract.payment.line', string="payment Line")
	sequence = fields.Integer(string="Sequence", default=1)
	customer_id = fields.Many2one('res.partner',string="Customer")
	contract_name = fields.Char(string="Contract Name")

	# vatcase
	tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])