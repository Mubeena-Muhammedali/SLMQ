# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pandas as pd
import datetime

class OrchidASPContract(models.Model):
	_name = "od.asp.contract"
	_description = "Contracts"
	_inherit = ['mail.thread']

	name = fields.Char(string="Contract ID", tracking=True)
	contract_code = fields.Char(string="Contract Name")
	partner_id = fields.Many2one('res.partner', string="Customer", ondelete='restrict', tracking=True)
	contact_id = fields.Many2one('res.partner', string="Contact Person", ondelete='restrict', domain="[('parent_id','=',partner_id)]", tracking=True)
	currency_id = fields.Many2one('res.currency', string="Currency", ondelete='restrict', tracking=True)
	client_order_ref = fields.Char(string="Client Ref/PO", tracking=True)
	email = fields.Char(string="Email", tracking=True)
	date_from = fields.Date(string="Start Date", tracking=True)
	date_to = fields.Date(string="End Date", tracking=True)
	contract_period = fields.Integer(string="Contract Period (Months)", tracking=True)
	sale_order_ids=fields.Many2many('sale.order', string="Sale Orders")
	sam_id = fields.Many2one('res.users', string="SAM")
	contract_line_ids = fields.One2many('od.asp.contract.line', 'order_id', string="Service Lines")
	contract_line_active_ids = fields.One2many('od.asp.contract.line.active', 'order_id', string="Service Lines")
	note = fields.Text(string="Note")
	company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
	state=fields.Selection([('0_draft','Draft'),('active','In Progress'),('inactive','Expired'),('terminate','Terminated')], string="Active", default='0_draft')
	invoice_ids = fields.Many2many("account.move", string='Invoices', compute="_get_invoiced", readonly=True, copy=False)
	payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
	od_exchange_rate = fields.Float(digits=0, default=1.0,string="Exchange Rate")
	color = fields.Integer('Color Index', compute="change_colore_on_kanban")
	renewed = fields.Boolean(string="Renewed", default=False)
	analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True, copy=False, help="The analytic account related to a sales order.")
	fluctuation = fields.Boolean(string="Fluctuating Contract", default=False,tracking=True)
	new_business = fields.Boolean(string="New Business", default=True)
	contracts_to_renew = fields.Boolean(string="Contracts to renew", default=False)

	@api.depends('state')
	def change_colore_on_kanban(self):
		for record in self:
			color = 0
			if record.state == '0_draft':
				color = 1
			elif record.state == 'active':
				color = 10
			elif record.state == 'inactive':
				color = 3
			else:
				color=0
			record.color = color

	def unlink(self):
		for line in self:
			if line.invoice_ids:
				raise UserError(_("You cannot delete a service which has been invoiced already!!!"))
			return super(OrchidASPContract, self).unlink()
	

	
	@api.depends('contract_line_ids.invoice_line_ids')
	def _get_invoiced(self):
		for order in self:
			invoices = order.contract_line_ids.invoice_line_ids.move_id.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund'))
			order.invoice_ids = invoices

	def button_confirm(self):
		# confirming the contract and draft contract lines which have effective date for fresh contract
		# for line in self.contract_line_ids.filtered(lambda r: r.effective_date !=False and r.state=='draft'):
		if self.analytic_account_id and self.contract_code:
			self.analytic_account_id.name=self.contract_code
			
		for line in self.contract_line_ids.filtered(lambda r: r.state=='0_draft'):
			line.action_activate()
		self.state='active'

	def button_terminate(self):
		# terminating the contract and draft and active contract lines
		for line in self.contract_line_ids.filtered(lambda r: r.state in('0_draft','active')):
			line.state='terminate'
			line.termination_reason="Contract Terminated"
			line.termination_date=fields.date.today()
		self.state='terminate'

	def button_expire(self):
		#the contract is expired if all its cntract lines are either terminated or expired
		# need to check
		records = self.search([
			('state', 'in', ['0_draft','active']),
		])
		to_date = fields.Date.context_today(self) + datetime.timedelta(days=100)
		for record in records: 
			if not record.contract_line_ids.filtered(lambda r: r.state in('0_draft','active')):
				record.state='inactive'
				record.contracts_to_renew = False
			elif record.state=='active' and record.date_to>=fields.Date.context_today(self) and record.date_to <= to_date and not record.renewed:
				record.contracts_to_renew = True
			else:
				record.contracts_to_renew = False


	def button_renew(self, new_quotation):
		for record in self:
			if record.renewed:
				raise UserError(_("This contract is renewed already!!"))
			if new_quotation:
				pricelist_id = 1
				if record.currency_id.id == 2:
					pricelist_id = 4
				old_quotation_id = self.sale_order_ids.search([],limit=1, order="id desc")

				sale_vals={
				'partner_id':record.partner_id.id,
				'od_contact_id':record.contact_id.id,
				'currency_id':record.currency_id.id,
				'payment_term_id':record.payment_term_id.id,
				'od_exchange_rate':record.od_exchange_rate,
				'pricelist_id':pricelist_id,
				}
				if old_quotation_id:
					sale_vals['campaign_id'] = old_quotation_id.campaign_id and old_quotation_id.campaign_id.id or 16
					sale_vals['medium_id'] = old_quotation_id.medium_id and old_quotation_id.medium_id.id or 14
					sale_vals['source_id'] = old_quotation_id.source_id.id

				renewed_quotation_id = self.env['sale.order'].create(sale_vals)
				line_ls = []
				for line in record.contract_line_ids.filtered(lambda r: r.state !='terminate'):
					tax_ls=[]
					for t in line.tax_id:
						tax_ls.append(t.id)
					line_vals={
					'display_type':False,
					'order_id':renewed_quotation_id.id,
					'product_id':line.product_id.id,
					'name':line.name,
					'price_unit':line.price_unit,
					'price_subtotal':line.price_subtotal,
					'price_total':line.price_total,
					'tax_id':[(6,0,tax_ls)],
					'price_tax':line.price_tax,
					'discount':line.discount,
					'product_uom_qty':line.product_uom_qty,
					'product_uom':line.product_uom.id,
					# 'od_frequency':line.frequency,
					'od_frequency':0,
					}
					w_line = (0,0,line_vals)
					line_ls.append(w_line)
				renewed_quotation_id.order_line = line_ls
				record.renewed=True
				record.contracts_to_renew = False
				action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
				form_view = [(self.env.ref('sale.view_order_form').id, 'form')]
				if 'views' in action:
					action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
				else:
					action['views'] = form_view
				action['res_id'] = renewed_quotation_id.id
				return action
			else:
				sale_ls=[]
				for sid in self.sale_order_ids:
					sale_ls.append(sid.id)
				contract_vals = {
				'partner_id':record.partner_id.id,
				'contact_id':record.contact_id.id,
				'currency_id':record.currency_id.id,
				'client_order_ref':record.client_order_ref,
				'email':record.email,
				'sale_order_ids':[(6,0,sale_ls)],
				'sam_id':record.sam_id.id,
				'company_id':record.company_id.id,
				'payment_term_id':record.payment_term_id.id,
				'od_exchange_rate':record.od_exchange_rate,
				'state':'0_draft',
				'new_business':False,
				'analytic_account_id':record.analytic_account_id and record.analytic_account_id.id,
				}
				renewed_contract_id = self.env['od.asp.contract'].create(contract_vals)
				line_ls = []
				for line in record.contract_line_ids.filtered(lambda r: r.state !='terminate'):
					tax_ls=[]
					for t in line.tax_id:
						tax_ls.append(t.id)
					line_vals={
					'state':'0_draft',
					'order_id':renewed_contract_id.id,
					'billing_cycle':line.billing_cycle,
					'acculde':line.acculde,
					'product_id':line.product_id.id,
					'name':line.name,
					'price_unit':line.price_unit,
					'price_subtotal':line.price_subtotal,
					'price_total':line.price_total,
					'tax_id':[(6,0,tax_ls)],
					'price_tax':line.price_tax,
					'discount':line.discount,
					'product_uom_qty':line.product_uom_qty,
					'product_uom':line.product_uom.id,
					'order_line_id':line.order_line_id.id,
					'frequency':line.frequency,
					}
					w_line = (0,0,line_vals)
					line_ls.append(w_line)
				renewed_contract_id.contract_line_ids = line_ls
				record.renewed=True
				record.contracts_to_renew = False
				for sale_id in renewed_contract_id.sale_order_ids:
					sale_id.od_contract_id=renewed_contract_id.id
				action = self.env["ir.actions.actions"]._for_xml_id("orchid_asp_gulf.action_od_asp_contract_view")
				form_view = [(self.env.ref('orchid_asp_gulf.od_asp_contract_form_view').id, 'form')]
				if 'views' in action:
					action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
				else:
					action['views'] = form_view
				action['res_id'] = renewed_contract_id.id
				return action

	@api.onchange('date_from','date_to')
	def onchange_contract_period(self):
		
		if self.date_from and self.date_to:
			start_date = self.date_from
			end_date = self.date_to
			months = pd.date_range(start_date, end_date, freq='M')
			# months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
			# months=abs(months)+1
			# months=abs(rdelta.months)+1
			self.contract_period=len(months)

			for line in self.contract_line_ids:
				if not line.effective_date:
					line.effective_date = self.date_from
				# if not line.billing_from:
				line.billing_from = self.date_from
				# if not line.billing_to:
				line.billing_to = self.date_to
				line.onchange_payment_date()

	@api.onchange('partner_id')
	def onchange_partner_id(self):
		if self.partner_id:
			# if not self.currency_id:
				# self.currency_id = self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.currency_id.id
				# self.currency_id = self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.currency_id.id
			if not self.email:
				self.email=self.partner_id.email
			self.sam_id = self.partner_id.user_id and self.partner_id.user_id.id

	@api.model_create_multi
	def create(self, vals_list):

		for vals in vals_list:

			sale_order_ids = []

			if vals.get('sale_order_ids'):
				for command in vals['sale_order_ids']:
					if command[0] == 6:
						sale_order_ids = command[2]
					elif command[0] == 4:
						sale_order_ids.append(command[1])

			if not sale_order_ids:
				raise UserError(_('Contract can be created from Sale Order only'))

			vals['name'] = self.env['ir.sequence'].next_by_code('od.asp.contract')

		records = super().create(vals_list)

		active_id = self.env.context.get('active_id')
		active_model = self.env.context.get('active_model')

		if active_id and active_model == 'sale.order':
			sale_order = self.env['sale.order'].browse(active_id)
			# if multiple records, assign first one (or adjust logic if needed)
			sale_order.od_contract_id = records[0].id

		return records

	def action_view_invoice(self):
		invoices = self.mapped('invoice_ids')
		action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
		if len(invoices) > 1:
			action['domain'] = [('id', 'in', invoices.ids)]
		elif len(invoices) == 1:
			form_view = [(self.env.ref('account.view_move_form').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
			action['res_id'] = invoices.id
		else:
			action = {'type': 'ir.actions.act_window_close'}

		context = {
			'default_move_type': 'out_invoice',
		}
		# if len(self) == 1:
		#     context.update({
		#         'default_partner_id': self.partner_id.id,
		#         'default_partner_shipping_id': self.partner_shipping_id.id,
		#         'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
		#         'default_invoice_origin': self.mapped('name'),
		#         'default_user_id': self.user_id.id,
		#     })
		action['context'] = context
		return action

	def find_number_of_months(self,start_date,end_date):
		start_months=pd.date_range(start_date, end_date, freq='MS')
		end_months=pd.date_range(start_date, end_date, freq='M')
		months_all =[]
		for date in start_months:
			yr_month=str(date.month)+"-"+str(date.year)
			months_all.append(yr_month)
		for date in end_months:
			yr_month=str(date.month)+"-"+str(date.year)
			months_all.append(yr_month)
		months_all = list(set(months_all))
		return len(months_all)

class OrchidASPContractLines(models.Model):
	_name = "od.asp.contract.line"
	_description = "Service Lines"
	_order = "state asc, id desc"

	order_id = fields.Many2one('od.asp.contract', string="Contract", ondelete='cascade')
	effective_date = fields.Date(string="Effective Date")
	billing_from = fields.Date(string="Billing From")
	billing_to = fields.Date(string="Billing To")
	billing_cycle = fields.Selection([('monthly','Monthly'), ('quarterly','Quarterly'), ('half','Half yearly'), ('yearly','Yearly'), ('one_time','One Time'), ('annually','Annually')], string="Billing Cycle")
	next_invoice_date = fields.Date(string="Next Payment Date")
	state=fields.Selection([('0_draft','Draft'),('active','Active'),('inactive','Expired'),('terminate','Terminated')], string="Active", default='0_draft')
	
	name = fields.Text(string='Description', required=True)
	sequence = fields.Integer(string='Sequence', default=10)
	price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
	price_subtotal = fields.Monetary( string='Subtotal', readonly=True, store=True)
	price_tax = fields.Float(string='Total Tax', readonly=True, store=True)
	price_total = fields.Monetary(string='Total', readonly=True, store=True)
	tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
	discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
	product_id = fields.Many2one(
		'product.product', string='Product', domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
		change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
	product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
	product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
	currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
	company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
	invoice_line_ids = fields.Many2many('account.move.line', string="Invoices")
	order_line_id = fields.Many2one('sale.order.line', string="Sale Line")
	payment_id = fields.Many2one('od.contract.payment', string="Payment")
	frequency = fields.Integer(string="Frequency")

	# termination
	termination_date = fields.Date(string="Termination Date")
	termination_reason = fields.Char(string="Termination Reason")

	acculde = fields.Boolean(string="Accrued", default=True)
	line_regular = fields.Boolean(string="Regular", default=False)
	fluctuating_contract=fields.Boolean(string="Fluctuating Service", help="returns true if this prepayment is associated with a fluctuating contractline", default=False, copy=False, readonly=True)
	flctng_parent_contract_line_id=fields.Many2one('od.asp.contract.line', string="Parent contract line", help="contract line from which this fluctuating line has been created")

	company_currency_id = fields.Many2one('res.currency',string='Company Currency', readonly=True, related='company_id.currency_id')
	total_direct_cost = fields.Monetary(string='Total Cost', currency_field='company_currency_id', help="Total cost to be booked for the whole contract period")


	def action_activate(self):
		for line in self:
			if line.effective_date:
				if (line.state=='active' and not line.invoice_line_ids) or line.state=='0_draft':
					line.payment_id.unlink()
					# if not (line.product_id.categ_id.id==40 or line.frequency>1):
					# if line.frequency!=1:generate paylines for all including onetime
					
					if not line.billing_cycle:
						raise UserError(_("Please assign a billing cycle for the service '%s' !!")%(line.product_id.name))
					no_of_months=1
					if line.billing_from and line.billing_to:
						start_date = line.billing_from
						end_date = line.billing_to
						months = pd.date_range(start_date, end_date, freq='M')
						no_of_months=len(months)
					if no_of_months<1:
						no_of_months=1
						
					vals={
					'name':line.name,
					'contract_line_id':line.id,
					'contract_id':line.order_id.id,
					'start_date':line.billing_from,
					'end_date':line.billing_to,
					'billing_cycle':line.billing_cycle,
					# 'total_amount':line.price_total,changed here for vat case
					'total_amount':line.price_subtotal,
					'partner_id':line.order_id.partner_id.id,
					# 'per_month':line.price_unit*line.product_uom_qty,
					'per_month':line.price_subtotal/no_of_months,
					'fluctuating_contract':line.fluctuating_contract,
					}
					payment_id=self.env['od.contract.payment'].create(vals)
					self.payment_id=payment_id.id
					payment_id.generate()
					self.state='active'
				else:
					raise UserError(_("Invoices have been generated already!!"))

	@api.onchange('effective_date')
	def onchange_payment_date(self):
		for line in self:
			# if line.billing_from:
			# 	if not(line.order_id.date_from<=line.billing_from<=line.order_id.date_to):
			# 		raise UserError(_("The Billing Date should be between Contract Period!!"))
			# if line.billing_to:
			# 	if not(line.order_id.date_from<=line.billing_to<=line.order_id.date_to):
			# 		raise UserError(_("The Billing To Date should be between Contract Period!!"))
			# 	if line.billing_from and not(line.billing_from<=line.billing_to):
			# 		raise UserError(_("The Billing To Date should not be less than Billing From Date!!"))
			if line.effective_date:
				# if not(line.order_id.date_from<=line.effective_date<=line.order_id.date_to):
				# 	raise UserError(_("The Effective Date should be between Contract Period!!"))
				line.next_invoice_date=line.effective_date
				line.billing_from=line.effective_date
				line.onchange_line_regular()

	@api.onchange('billing_from','billing_to')
	def onchange_line_regular(self):
		for line in self:
			# this is included to calculate the payment lines correctly. bcoz the calculation for line ending in between month and ending in the month end are different
			# so the line is divided as regular and irregular based on the billing to date
			# regular---line with billing to= a proper month end.ie 30,31 and 28,29 for feb
			# irregular---line with billing to= in between month.ie not(30,31) and not in (28,29 with month !=feb)
			
			if line.billing_from and line.billing_to:
				
				if line.billing_to.day in (28,29) and line.billing_to.month==2:
					line.line_regular=True
				elif line.billing_to.day in (30,31):
					line.line_regular=True
				else:
					line.line_regular=False
				
	def button_expire(self):
		#the contract is expired if billing_to is less than today date and all payment Lines are invoiced
		# need to check if all invoices are paid
		records = self.search([
			('state', 'in', ['0_draft','active']),
			('billing_to', '<', fields.Date.today(self)),
		])
		for record in records:
			if record.payment_id:
				payment_lines = record.payment_id.payment_line
				if all(payment_line.invoiced for payment_line in payment_lines):
					record.state='inactive'
			else:
				record.state='inactive'

	def unlink(self):
		for line in self:
			if line.invoice_line_ids:
				raise UserError(_("You cannot delete a service which has been invoiced already!!!"))
			return super(OrchidASPContractLines, self).unlink()


class OrchidASPContractLinesActive(models.Model):
	_name = "od.asp.contract.line.active"
	_description = "Service Lines"
	_order = "state asc, id desc"

	order_id = fields.Many2one('od.asp.contract', string="Contract", ondelete='cascade')
	effective_date = fields.Date(string="Effective Date")
	billing_from = fields.Date(string="Billing From")
	billing_to = fields.Date(string="Billing To")
	billing_cycle = fields.Selection([('monthly','Monthly'), ('quarterly','Quarterly'), ('half','Half yearly'), ('yearly','Yearly'), ('one_time','One Time'), ('annually','Annually')], string="Billing Cycle")
	next_invoice_date = fields.Date(string="Next Payment Date")
	state=fields.Selection([('0_draft','Draft'),('active','Active'),('inactive','Expired'),('terminate','Terminated')], string="Active", default='0_draft')
	
	name = fields.Text(string='Description', required=True)
	sequence = fields.Integer(string='Sequence', default=10)
	price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
	price_subtotal = fields.Monetary( string='Subtotal', readonly=True, store=True)
	price_tax = fields.Float(string='Total Tax', readonly=True, store=True)
	price_total = fields.Monetary(string='Total', readonly=True, store=True)
	tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
	discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
	product_id = fields.Many2one(
		'product.product', string='Product', domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
		change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
	product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
	product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
	currency_id = fields.Many2one(related='order_id.currency_id', depends=['order_id.currency_id'], store=True, string='Currency', readonly=True)
	company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True, index=True)
	invoice_line_ids = fields.Many2many('account.move.line', string="Invoices")
	order_line_id = fields.Many2one('sale.order.line', string="Sale Line")
	payment_id = fields.Many2one('od.contract.payment', string="Payment")
	frequency = fields.Integer(string="Frequency")

	# termination
	termination_date = fields.Date(string="Termination Date")
	termination_reason = fields.Char(string="Termination Reason")

	acculde = fields.Boolean(string="Accrued", default=True)
	line_regular = fields.Boolean(string="Regular", default=False)
	fluctuating_contract=fields.Boolean(string="Fluctuating Service", help="returns true if this prepayment is associated with a fluctuating contractline", default=False, copy=False, readonly=True)
	flctng_parent_contract_line_id=fields.Many2one('od.asp.contract.line', string="Parent contract line", help="contract line from which this fluctuating line has been created")

	company_currency_id = fields.Many2one('res.currency',string='Company Currency', readonly=True, related='company_id.currency_id')
	total_direct_cost = fields.Monetary(string='Total Cost', currency_field='company_currency_id', help="Total cost to be booked for the whole contract period")

	def action_activate(self):
		for line in self:
			if line.effective_date:
				if (line.state=='active' and not line.invoice_line_ids) or line.state=='0_draft':
					line.payment_id.unlink()
					# if not (line.product_id.categ_id.id==40 or line.frequency>1):
					# if line.frequency!=1:generate paylines for all including onetime
					
					if not line.billing_cycle:
						raise UserError(_("Please assign a billing cycle for the service '%s' !!")%(line.product_id.name))
					no_of_months=1
					if line.billing_from and line.billing_to:
						start_date = line.billing_from
						end_date = line.billing_to
						months = pd.date_range(start_date, end_date, freq='M')
						no_of_months=len(months)
					if no_of_months<1:
						no_of_months=1
						
					vals={
					'name':line.name,
					'contract_line_id':line.id,
					'contract_id':line.order_id.id,
					'start_date':line.billing_from,
					'end_date':line.billing_to,
					'billing_cycle':line.billing_cycle,
					# 'total_amount':line.price_total,changed here for vat case
					'total_amount':line.price_subtotal,
					'partner_id':line.order_id.partner_id.id,
					'per_month':line.price_subtotal/no_of_months,
					'fluctuating_contract':line.fluctuating_contract,
					}
					payment_id=self.env['od.contract.payment'].create(vals)
					self.payment_id=payment_id.id
					payment_id.generate()
					self.state='active'
				else:
					raise UserError(_("Invoices have been generated already!!"))

	@api.onchange('effective_date')
	def onchange_payment_date(self):
		for line in self:
			if line.effective_date:
				line.next_invoice_date=line.effective_date
				line.billing_from=line.effective_date
				line.onchange_line_regular()

	@api.onchange('billing_from','billing_to')
	def onchange_line_regular(self):
		for line in self:
			# this is included to calculate the payment lines correctly. bcoz the calculation for line ending in between month and ending in the month end are different
			# so the line is divided as regular and irregular based on the billing to date
			# regular---line with billing to= a proper month end.ie 30,31 and 28,29 for feb
			# irregular---line with billing to= in between month.ie not(30,31) and not in (28,29 with month !=feb)
			
			if line.billing_from and line.billing_to:
				
				if line.billing_to.day in (28,29) and line.billing_to.month==2:
					line.line_regular=True
				elif line.billing_to.day in (30,31):
					line.line_regular=True
				else:
					line.line_regular=False
				
	def button_expire(self):
		#the contract is expired if billing_to is less than today date and all payment Lines are invoiced
		# need to check 
		records = self.search([
			('state', 'in', ['0_draft','active']),
			('billing_to', '<', fields.Date.today(self)),
		])
		for record in records:
			if record.payment_id:
				payment_lines = record.payment_id.payment_line
				if all(payment_line.invoiced for payment_line in payment_lines):
					record.state='inactive'
			else:
				record.state='inactive'

	def unlink(self):
		for line in self:
			if line.invoice_line_ids:
				raise UserError(_("You cannot delete a service which has been invoiced already!!!"))
			return super(OrchidASPContractLines, self).unlink()
