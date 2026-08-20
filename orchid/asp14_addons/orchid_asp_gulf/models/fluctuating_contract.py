# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pandas as pd

class OrchidFluctuatingContract(models.Model):
	_name = "od.fluctuating.contract"
	_description = "Fluctuating Services"
	_inherit = ['mail.thread']

	remarks = fields.Text('Remarks')
	name = fields.Many2one('od.asp.contract', 'Contract', required=True, copy=False,  domain="[('state','=','active'),('fluctuation','=',True)]", tracking=True)
	fluctuating_line_ids = fields.One2many('od.fluctuating.contract.line','form_id',string="Contract Lines", copy=False)
	company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
	contract_name = fields.Char('Contract Name', related="name.contract_code", store=True)
	state=fields.Selection([('draft','Draft'),('validate','Validated'),('approve','Approved')], string="State", default='draft', copy=False, tracking=True)


# class OrchidFluctuatingContractLine(models.Model):
# 	_name = "od.fluctuating.contract.line"
# 	_description = "Fluctuating Service Lines"

	# form_id = fields.Many2one('od.fluctuating.contract', string="Contract", ondelete='cascade')
	# company_id = fields.Many2one('res.company', string="Company", related='name.company_id', store=True)
	# contract_line_id = fields.Many2one('od.asp.contract.line', string="Contract Line", required=True,  domain="[('order_id','=',name),('state','=','active'),('flctng_parent_contract_line_id','=',False),('billing_cycle','=','monthly')]", tracking=True)
	# product_id = fields.Many2one('product.product',related="contract_line_id.product_id", string='Product', change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
	# old_desc = fields.Text(related="contract_line_id.name", string='Description', change_default=True,  check_company=True)  # Unrequired company
	# new_desc = fields.Text(string='New Description', change_default=True,  check_company=True)  # Unrequired company
	# inv_desc = fields.Text(string='Invoice Description', change_default=True, help="Description to be passed to invoice line for grouped lines")  # Unrequired company
	# start_date = fields.Date('Start Date', required=True, tracking=True)
	# current_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', compute="_compute_current_qty", store=True)
	# new_qty = fields.Float(string="New Qty", digits='Product Unit of Measure', required=True, tracking=True)
	# revised_qty = fields.Float(string="Revised Qty", digits='Product Unit of Measure', compute="_compute_revised_qty", store=True)
	
	# # price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
	# frequency = fields.Integer(string="Frequency")
	# # price_subtotal = fields.Monetary( string='Subtotal', readonly=True, store=True)
	# # tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
	# # price_tax = fields.Float(string='Total Tax', readonly=True, store=True)
	# # price_total = fields.Monetary(string='Total', readonly=True, store=True)
	# # discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
	# # currency_id = fields.Many2one(related='contract_line_id.currency_id', depends=['contract_line_id.currency_id'], store=True, string='Currency', readonly=True)

	# termination_date = fields.Date(string="Termination Date")
	# termination_reason = fields.Char(string="Termination Reason")
	# new_contract_line_id=fields.Many2one('od.asp.contract.line', string="Contract Line", copy=False, readonly=True)
	
	# def button_terminate(self, cl):
	# 	if self.termination_date and self.termination_reason:
	# 		cl.sudo().write({'termination_date':self.termination_date,'termination_reason':self.termination_reason,'state':'terminate'})
	# 		start_date = cl.billing_from
	# 		end_date = self.termination_date
	# 		months = pd.date_range(start_date, end_date, freq='M')
	# 		frequency=len(months)
	# 		cl.order_line_id.od_frequency=frequency
	# 		# cl.order_line_id.product_uom_qty=0


	# def create_new_quote_line(self):
	# 	quotation_line_vals={
	# 		'order_id':self.contract_line_id.order_line_id.order_id.id,
	# 		'product_id':self.product_id.id,
	# 		'name':self.new_desc,
	# 		# 'product_uom_qty':self.revised_qty,
	# 		'price_unit':self.contract_line_id.price_unit,
	# 		'od_frequency':self.frequency,
	# 		'tax_id':[(6,0,[tax.id for tax in self.contract_line_id.tax_id])],
	# 		}
	# 	if self.revised_qty>0:
	# 		quotation_line_vals['product_uom_qty']=self.revised_qty
	# 	if self.revised_qty<0:
	# 		quotation_line_vals['product_uom_qty']=self.new_qty
	# 	sale_order_line=self.env['sale.order.line'].create(quotation_line_vals)
	# 	return sale_order_line

	# def create_new_contract_line(self,sale_order_line):
	# 	contract_line_vals={
	# 			'sequence':sale_order_line.sequence,
	# 			'effective_date':self.start_date,
	# 			'billing_from':self.start_date,
	# 			'acculde':self.contract_line_id.acculde,
	# 			'billing_to':self.contract_line_id.billing_to,
	# 			'next_invoice_date':self.start_date,
	# 			'billing_cycle':'monthly',
	# 			'product_id':sale_order_line.product_id.id,
	# 			'name':sale_order_line.name,
	# 			'price_unit':sale_order_line.price_unit,
	# 			'price_subtotal':sale_order_line.price_subtotal,
	# 			'price_total':sale_order_line.price_total,
	# 			'price_tax':sale_order_line.price_tax,
	# 			'tax_id':[(6,0,[tax.id for tax in sale_order_line.tax_id])],
	# 			'discount':sale_order_line.discount,
	# 			'product_uom_qty':sale_order_line.product_uom_qty,
	# 			'product_uom':sale_order_line.product_uom.id,
	# 			'order_line_id':sale_order_line.id,
	# 			'frequency':sale_order_line.od_frequency,
	# 			'order_id':self.name.id,
	# 			# 'fluctuating_contract':True,
	# 			# 'flctng_parent_contract_line_id':self.contract_line_id.id,

	# 			}
	# 	if self.revised_qty>0:
	# 		contract_line_vals['fluctuating_contract']=True
	# 		contract_line_vals['flctng_parent_contract_line_id']=self.contract_line_id.id,
	# 	new_contract_line=self.env['od.asp.contract.line'].create(contract_line_vals)
	# 	new_contract_line.onchange_line_regular()
	# 	new_contract_line.action_activate()
	# 	self.new_contract_line_id=new_contract_line.id

	def button_validate(self):
		self.state='validate'

	def button_reset(self):
		self.state='draft'

	# def button_approve(self):
	# 	if self.contract_line_id.state!='active':# to ensure the contract line/contract is active at the time of approval
	# 		raise UserError(_("The contract line is not in progress state !!"))
	# 	'''if the revised qty is positive=extra qty added'''
	# 	if self.revised_qty<0:
	# 		child_line_ids = self.env['od.asp.contract.line'].search([('flctng_parent_contract_line_id','=',self.contract_line_id.id),('state','=','active')])
	# 		for cl in child_line_ids:
	# 			self.button_terminate(cl)
	# 		self.button_terminate(self.contract_line_id)
	# 		sale_order_line=self.create_new_quote_line()
	# 		self.create_new_contract_line(sale_order_line)
	# 	if self.revised_qty>0:

	# 		# 1.new quotaton line
	# 		# quotation_line_vals={
	# 		# 'order_id':self.contract_line_id.order_line_id.order_id.id,
	# 		# 'product_id':self.product_id.id,
	# 		# 'name':self.contract_line_id.name,
	# 		# 'product_uom_qty':self.revised_qty,
	# 		# 'price_unit':self.contract_line_id.price_unit,
	# 		# 'od_frequency':self.frequency,
	# 		# 'tax_id':[(6,0,[tax.id for tax in self.contract_line_id.tax_id])],
	# 		# }
	# 		# sale_order_line=self.env['sale.order.line'].create(quotation_line_vals)
	# 		sale_order_line=self.create_new_quote_line()
	# 		self.create_new_contract_line(sale_order_line)

	# 		# 2.new contractline--active
	# 		# contract_line_vals={
	# 		# 	'sequence':sale_order_line.sequence,
	# 		# 	'effective_date':self.start_date,
	# 		# 	'billing_from':self.start_date,
	# 		# 	'acculde':self.contract_line_id.acculde,
	# 		# 	'billing_to':self.contract_line_id.billing_to,
	# 		# 	'next_invoice_date':self.contract_line_id.next_invoice_date,
	# 		# 	'billing_cycle':'monthly',
	# 		# 	'product_id':sale_order_line.product_id.id,
	# 		# 	'name':sale_order_line.name,
	# 		# 	'price_unit':sale_order_line.price_unit,
	# 		# 	'price_subtotal':sale_order_line.price_subtotal,
	# 		# 	'price_total':sale_order_line.price_total,
	# 		# 	'price_tax':sale_order_line.price_tax,
	# 		# 	'tax_id':[(6,0,[tax.id for tax in sale_order_line.tax_id])],
	# 		# 	'discount':sale_order_line.discount,
	# 		# 	'product_uom_qty':sale_order_line.product_uom_qty,
	# 		# 	'product_uom':sale_order_line.product_uom.id,
	# 		# 	'order_line_id':sale_order_line.id,
	# 		# 	'frequency':sale_order_line.od_frequency,
	# 		# 	'order_id':self.name.id,
	# 		# 	'fluctuating_contract':True,
	# 		# 	'flctng_parent_contract_line_id':self.contract_line_id.id,

	# 		# 	}
	# 		# new_contract_line=self.env['od.asp.contract.line'].create(contract_line_vals)
	# 		# new_contract_line.action_activate()

	# 		# 3.prepaymentlines
	# 		# 4.invoice generation

	# 	self.state='approve'


	def button_approve(self):
		for fl_line in self.fluctuating_line_ids:
			if fl_line.contract_line_id.state!='active':# to ensure the contract line/contract is active at the time of approval
				raise UserError(_("The contract line is not in progress state !!"))
			'''if the revised qty is positive=extra qty added'''
			if fl_line.revised_qty<0:
				child_line_ids = self.env['od.asp.contract.line'].search([('flctng_parent_contract_line_id','=',fl_line.contract_line_id.id),('state','=','active')])
				for cl in child_line_ids:
					fl_line.button_terminate(cl)
				fl_line.button_terminate(fl_line.contract_line_id)
				sale_order_line=fl_line.create_new_quote_line()
				fl_line.create_new_contract_line(sale_order_line)
			if fl_line.revised_qty>0:

				# 1.new quotaton line
				# quotation_line_vals={
				# 'order_id':self.contract_line_id.order_line_id.order_id.id,
				# 'product_id':self.product_id.id,
				# 'name':self.contract_line_id.name,
				# 'product_uom_qty':self.revised_qty,
				# 'price_unit':self.contract_line_id.price_unit,
				# 'od_frequency':self.frequency,
				# 'tax_id':[(6,0,[tax.id for tax in self.contract_line_id.tax_id])],
				# }
				# sale_order_line=self.env['sale.order.line'].create(quotation_line_vals)
				sale_order_line=fl_line.create_new_quote_line()
				fl_line.create_new_contract_line(sale_order_line)

			# 2.new contractline--active
			# contract_line_vals={
			# 	'sequence':sale_order_line.sequence,
			# 	'effective_date':self.start_date,
			# 	'billing_from':self.start_date,
			# 	'acculde':self.contract_line_id.acculde,
			# 	'billing_to':self.contract_line_id.billing_to,
			# 	'next_invoice_date':self.contract_line_id.next_invoice_date,
			# 	'billing_cycle':'monthly',
			# 	'product_id':sale_order_line.product_id.id,
			# 	'name':sale_order_line.name,
			# 	'price_unit':sale_order_line.price_unit,
			# 	'price_subtotal':sale_order_line.price_subtotal,
			# 	'price_total':sale_order_line.price_total,
			# 	'price_tax':sale_order_line.price_tax,
			# 	'tax_id':[(6,0,[tax.id for tax in sale_order_line.tax_id])],
			# 	'discount':sale_order_line.discount,
			# 	'product_uom_qty':sale_order_line.product_uom_qty,
			# 	'product_uom':sale_order_line.product_uom.id,
			# 	'order_line_id':sale_order_line.id,
			# 	'frequency':sale_order_line.od_frequency,
			# 	'order_id':self.name.id,
			# 	'fluctuating_contract':True,
			# 	'flctng_parent_contract_line_id':self.contract_line_id.id,

			# 	}
			# new_contract_line=self.env['od.asp.contract.line'].create(contract_line_vals)
			# new_contract_line.action_activate()

			# 3.prepaymentlines
			# 4.invoice generation

		self.state='approve'

	def unlink(self):
		if self.state=='approve':
			raise UserError(_("Cannot delete an approved record !!!"))
		return super(OrchidFluctuatingContract,self).unlink()
		
	@api.onchange('name')
	def onchange_contract(self):
		for contract in self:
			# contract.contract_line_id=False
			if contract.fluctuating_line_ids:
				contract.fluctuating_line_ids.unlink()

	# @api.onchange('start_date')
	# def onchange_start_date(self):
	# 	for contract in self:
	# 		if self.start_date:
	# 			start_date = self.start_date
	# 			end_date = self.contract_line_id.billing_to
	# 			months = pd.date_range(start_date, end_date, freq='M')
	# 			frequency=len(months)
	# 			contract.frequency=frequency		
			
	# @api.depends('contract_line_id')
	# def _compute_current_qty(self):
	# 	for contract in self:
	# 		if contract.contract_line_id:
	# 			# print("koooooooooooooooooooooooooooooooooooooo")
	# 			current_qty=contract.contract_line_id.product_uom_qty
	# 			for fl in self.env['od.asp.contract.line'].search([('flctng_parent_contract_line_id','=',self.contract_line_id.id),('state','=','active'),('billing_cycle','=','monthly')]):
	# 				# print("hereecdcdfssssssss")
	# 				current_qty=current_qty+fl.product_uom_qty
	# 			self.current_qty=current_qty
	# 		else:
	# 			# print("elseeeeeeeeeeeeeeeeeeee")
	# 			self.current_qty=0

	# @api.depends('current_qty','new_qty')
	# def _compute_revised_qty(self):
	# 	for contract in self:
	# 		contract.revised_qty=contract.new_qty-contract.current_qty

	# @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
	# def _compute_amount(self):
	# 	"""
	# 	Compute the amounts of the line.
	# 	"""
	# 	for line in self:
	# 		price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
	# 		taxes = line.tax_id.compute_all(price, line.currency_id, line.product_uom_qty, product=line.product_id, partner=line.form_id.name.partner_id)
	# 		line.update({
	# 			'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
	# 			'price_total': taxes['total_included'],
	# 			'price_subtotal': taxes['total_excluded'],
	# 		})
	# 		if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
	# 			line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])


class OrchidFluctuatingContractLine(models.Model):
	_name = "od.fluctuating.contract.line"
	_description = "Fluctuating Service Lines"

	form_id = fields.Many2one('od.fluctuating.contract', string="Contract", ondelete='cascade')
	contract_id = fields.Many2one('od.asp.contract', 'Contract', related="form_id.name", store=True)
	company_id = fields.Many2one('res.company', string="Company", related='form_id.company_id', store=True)
	contract_line_id = fields.Many2one('od.asp.contract.line', string="Contract Line", required=True,  domain="[('order_id','=',contract_id),('state','=','active'),('flctng_parent_contract_line_id','=',False),('billing_cycle','=','monthly')]", tracking=True)
	product_id = fields.Many2one('product.product',related="contract_line_id.product_id", string='Product', change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
	old_desc = fields.Text(related="contract_line_id.name", string='Description', change_default=True,  check_company=True)  # Unrequired company
	new_desc = fields.Text(string='New Description', change_default=True,  check_company=True)  # Unrequired company
	# inv_desc = fields.Text(string='Invoice Description', change_default=True, help="Description to be passed to invoice line for grouped lines")  # Unrequired company
	start_date = fields.Date('Start Date', required=True, tracking=True)
	current_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', compute="_compute_current_qty", store=True)
	new_qty = fields.Float(string="New Qty", digits='Product Unit of Measure', required=True, tracking=True)
	revised_qty = fields.Float(string="Revised Qty", digits='Product Unit of Measure', compute="_compute_revised_qty", store=True)
	
	# price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
	frequency = fields.Integer(string="Frequency")
	# price_subtotal = fields.Monetary( string='Subtotal', readonly=True, store=True)
	# tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
	# price_tax = fields.Float(string='Total Tax', readonly=True, store=True)
	# price_total = fields.Monetary(string='Total', readonly=True, store=True)
	# discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
	# currency_id = fields.Many2one(related='contract_line_id.currency_id', depends=['contract_line_id.currency_id'], store=True, string='Currency', readonly=True)
	state=fields.Selection([('draft','Draft'),('validate','Validated'),('approve','Approved')], string="State", default='draft', copy=False, tracking=True)

	termination_date = fields.Date(string="Termination Date")
	termination_reason = fields.Char(string="Termination Reason")
	new_contract_line_id=fields.Many2one('od.asp.contract.line', string="Contract Line", copy=False, readonly=True)


	@api.onchange('start_date')
	def onchange_start_date(self):
		for contract in self:
			if self.start_date:
				start_date = self.start_date
				end_date = self.contract_line_id.billing_to
				months = pd.date_range(start_date, end_date, freq='M')
				frequency=len(months)
				contract.frequency=frequency		
			
	@api.depends('contract_line_id')
	def _compute_current_qty(self):
		for contract in self:
			if contract.contract_line_id:
				# print("koooooooooooooooooooooooooooooooooooooo")
				current_qty=contract.contract_line_id.product_uom_qty
				for fl in self.env['od.asp.contract.line'].search([('flctng_parent_contract_line_id','=',contract.contract_line_id.id),('state','=','active'),('billing_cycle','=','monthly')]):
					# print("hereecdcdfssssssss",fl.product_uom_qty,current_qty)
					current_qty=current_qty+fl.product_uom_qty
				contract.current_qty=current_qty
			else:
				# print("elseeeeeeeeeeeeeeeeeeee")
				contract.current_qty=0

	@api.depends('current_qty','new_qty')
	def _compute_revised_qty(self):
		for contract in self:
			contract.revised_qty=contract.new_qty-contract.current_qty

	def button_terminate(self, cl):
		if self.termination_date and self.termination_reason:
			cl.sudo().write({'termination_date':self.termination_date,'termination_reason':self.termination_reason,'state':'terminate'})
			start_date = cl.billing_from
			end_date = self.termination_date
			months = pd.date_range(start_date, end_date, freq='M')
			frequency=len(months)
			cl.order_line_id.od_frequency=frequency
			# cl.order_line_id.product_uom_qty=0


	def create_new_quote_line(self):
		quotation_line_vals={
			'order_id':self.contract_line_id.order_line_id.order_id.id,
			'product_id':self.product_id.id,
			'name':self.new_desc,
			# 'product_uom_qty':self.revised_qty,
			'price_unit':self.contract_line_id.price_unit,
			'od_frequency':self.frequency,
			'tax_id':[(6,0,[tax.id for tax in self.contract_line_id.tax_id])],
			}
		if self.revised_qty>0:
			quotation_line_vals['product_uom_qty']=self.revised_qty
		if self.revised_qty<0:
			quotation_line_vals['product_uom_qty']=self.new_qty
		sale_order_line=self.env['sale.order.line'].create(quotation_line_vals)
		return sale_order_line

	def create_new_contract_line(self,sale_order_line):
		contract_line_vals={
				'sequence':sale_order_line.sequence,
				'effective_date':self.start_date,
				'billing_from':self.start_date,
				'acculde':self.contract_line_id.acculde,
				'billing_to':self.contract_line_id.billing_to,
				'next_invoice_date':self.start_date,
				'billing_cycle':'monthly',
				'product_id':sale_order_line.product_id.id,
				'name':sale_order_line.name,
				'price_unit':sale_order_line.price_unit,
				'price_subtotal':sale_order_line.price_subtotal,
				'price_total':sale_order_line.price_total,
				'price_tax':sale_order_line.price_tax,
				'tax_id':[(6,0,[tax.id for tax in sale_order_line.tax_id])],
				'discount':sale_order_line.discount,
				'product_uom_qty':sale_order_line.product_uom_qty,
				'product_uom':sale_order_line.product_uom.id,
				'order_line_id':sale_order_line.id,
				'frequency':sale_order_line.od_frequency,
				'order_id':self.contract_id.id,
				# 'fluctuating_contract':True,
				# 'flctng_parent_contract_line_id':self.contract_line_id.id,

				}
		if self.revised_qty>0:
			contract_line_vals['fluctuating_contract']=True
			contract_line_vals['flctng_parent_contract_line_id']=self.contract_line_id.id,
		new_contract_line=self.env['od.asp.contract.line'].create(contract_line_vals)
		new_contract_line.onchange_line_regular()
		new_contract_line.action_activate()
		self.new_contract_line_id=new_contract_line.id


