# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class OrchidProductCorrection(models.Model):
	_name = 'od.product.correction'
	_description = "Product Correction Utility"
	_inherit = ['mail.thread']

	sale_id = fields.Many2one('sale.order',string="Sales Order", tracking=True)
	name=fields.Char(string="Name")
	contract_id = fields.Many2one('od.asp.contract',string="Contract", tracking=True)
	product_line_ds = fields.One2many('od.product.correction.line','utility_id', string="Products")
	contract_line_ids = fields.One2many('od.contract.correction.line','utility_id', string="Contracts")
	remarks = fields.Text(string="Remarks")
	description = fields.Char(string="Description")
	state = fields.Selection([('draft','Draft'),('confirm','Confirmed')], string="State", default='draft', tracking=True)
	company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id, tracking=True)
	record_type = fields.Selection([('sale','Sale Order'),('contract','Contract'),('contract_name','Contract Name')], string="Type", default='sale', tracking=True)
	old_contract_name = fields.Char(string="Old Contract Name")
	new_contract_name = fields.Char(string="New Contract Name")

	@api.onchange('record_type')
	def onchange_record_type(self):
		for rec in self:
			rec.product_line_ds.unlink()
			rec.contract_line_ids.unlink()
			rec.sale_id = False
			rec.contract_id = False
			rec.old_contract_name = False
			rec.new_contract_name = False

	@api.onchange('sale_id')
	def onchange_sale(self):
		for rec in self:
			rec.product_line_ds.unlink()
			if rec.sale_id:
				rec.contract_line_ids.unlink()
				rec.name=rec.sale_id.name

	@api.onchange('contract_id')
	def onchange_contract(self):
		for rec in self:
			rec.contract_line_ids.unlink()
			if rec.contract_id:
				rec.product_line_ds.unlink()
				rec.name=rec.contract_id.name
				if rec.record_type=='contract_name' and rec.contract_id:
					rec.old_contract_name = rec.contract_id.contract_code

	def button_confirm(self):
		if self.record_type=='contract_name':
			self.contract_id.write({'contract_code':self.new_contract_name})
			self.contract_id.mapped('invoice_ids').write({'od_contract_name':self.new_contract_name})


		elif self.record_type=='sale':
			for line in self.product_line_ds:
				line.update_products()
			# deletion method
			#1.get the total amount to be updated:
			inv_line_id_qry = '''SELECT lne.price_adjustment_line as line FROM od_product_correction_line lne WHERE lne.utility_id=%s AND lne.price_adjustment_line is not null GROUP BY lne.price_adjustment_line'''%(self.id)
			self._cr.execute(inv_line_id_qry)
			result = self._cr.dictfetchall()

			for data in result:
				total_price=0
				price_adjustment_line = self.env['sale.order.line'].browse(data['line'])
				for dl in self.product_line_ds.filtered(lambda x:x.price_adjustment_line.id==data['line']):
					if dl.sale_line_id.price_subtotal:
						total_price+=(dl.sale_line_id.price_unit*dl.sale_line_id.product_uom_qty)
				data['new_price'] = (total_price+price_adjustment_line.price_unit)
				for dl in self.product_line_ds.filtered(lambda x:x.price_adjustment_line.id==data['line']):
					contract_line_ids = self.env['od.asp.contract.line'].search([('order_line_id','=',dl.sale_line_id.id)])
					for contract_line_id in contract_line_ids:
						#1. invoice line unlink()
						if contract_line_id.invoice_line_ids:
							for invoice_line_id in contract_line_id.invoice_line_ids:
								invoice_line_id.move_id.button_draft()
								move_id = invoice_line_id.move_id
								invoice_line_id.write({'price_unit':0.00})
								invoice_line_id.unlink()
								move_id._compute_amount()
						#2.contractline terminate
						contract_line_id.write({'state':'terminate','termination_reason':"terminated via Utility",'termination_date':fields.date.today()})
					# 3.unlink saleline.
					sale_id=dl.sale_line_id.order_id
					dl.sale_line_id.write({'price_unit':0.00})
					delete_qry="""DELETE FROM account_analytic_line where so_line=%s"""%(dl.sale_line_id.id)
					self._cr.execute(delete_qry)
					delete_line_qry="""DELETE FROM sale_order_line where id=%s"""%(dl.sale_line_id.id)
					self._cr.execute(delete_line_qry)
					sale_id._amount_all()

				# update the new unit price
				#1.update sale
				new_price =  data['new_price']
				price_adjustment_line.write({'price_unit':new_price})
				price_adjustment_line._compute_amount()
				price_adjustment_line.order_id._amount_all()
				
				
				# 2. contract line
				adjust_contract_line_ids = self.env['od.asp.contract.line'].search([('order_line_id','=',price_adjustment_line.id)])
				for adjust_contract_line_id in adjust_contract_line_ids:
					adjust_contract_line_id.write({'price_unit':new_price})
					# 3.invoice line
					if adjust_contract_line_id.invoice_line_ids:
						for invoice_line_id in adjust_contract_line_id.invoice_line_ids:
							invoice_line_id.move_id.button_draft()
							invoice_line_id.write({'price_unit':data['new_price']})
							invoice_line_id._onchange_price_subtotal()
							invoice_line_id.move_id._compute_amount()
							invoice_line_id.move_id.action_post()
							
		elif self.record_type=='contract':
			for line in self.contract_line_ids:
				line.update_products()
			# deletion method
			#1.get the total amount to be updated:
			inv_line_id_qry = '''SELECT lne.price_adjustment_line as line FROM od_contract_correction_line lne WHERE lne.utility_id=%s AND lne.price_adjustment_line is not null GROUP BY lne.price_adjustment_line'''%(self.id)
			self._cr.execute(inv_line_id_qry)
			result = self._cr.dictfetchall()

			for data in result:
				total_price=0
				price_adjustment_line = self.env['od.asp.contract.line'].browse(data['line'])
				for dl in self.contract_line_ids.filtered(lambda x:x.price_adjustment_line.id==data['line']):
					if dl.contract_line_id.price_subtotal:
						total_price+=(dl.contract_line_id.price_unit*dl.contract_line_id.product_uom_qty)
				data['new_price'] = (total_price+price_adjustment_line.price_unit)
				for dl in self.contract_line_ids.filtered(lambda x:x.price_adjustment_line.id==data['line']):
					contract_line_ids = dl.contract_line_id
					for contract_line_id in contract_line_ids:
						#1. invoice line unlink()
						if contract_line_id.invoice_line_ids:
							for invoice_line_id in contract_line_id.invoice_line_ids:
								invoice_line_id.move_id.button_draft()
								move_id = invoice_line_id.move_id
								invoice_line_id.write({'price_unit':0.00})
								invoice_line_id.unlink()
								move_id._compute_amount()
						#2.contractline terminate
						contract_line_id.write({'state':'terminate','termination_reason':"terminated via Utility",'termination_date':fields.date.today()})
			
				
				# 2. contract line
				new_price =  data['new_price']
				adjust_contract_line_ids = price_adjustment_line
				for adjust_contract_line_id in adjust_contract_line_ids:
					adjust_contract_line_id.write({'price_unit':new_price})
					# 3.invoice line
					if adjust_contract_line_id.invoice_line_ids:
						for invoice_line_id in adjust_contract_line_id.invoice_line_ids:
							invoice_line_id.move_id.button_draft()
							invoice_line_id.write({'price_unit':data['new_price']})
							invoice_line_id._onchange_price_subtotal()
							invoice_line_id.move_id._compute_amount()
							invoice_line_id.move_id.action_post()
							
		self.state = 'confirm'


class OrchidProductCorrectionLine(models.Model):
	_name = 'od.product.correction.line'
	_description = "Product Correction Utility Line"

	utility_id = fields.Many2one('od.product.correction', string="Utility", copy=False, ondelete="cascade")
	sale_line_id = fields.Many2one('sale.order.line', string="Sale Order Line")
	sale_line_display_name = fields.Char(string="Sale Order Line")
	old_product_id = fields.Many2one('product.product', string="Old Product", store=True)
	new_product_id = fields.Many2one('product.product', string="New Product")
	old_description = fields.Char(string="Old Description")
	new_description = fields.Char(string="New Description")
	company_id = fields.Many2one('res.company', string="Company", related='utility_id.company_id', store=True)
	method = fields.Selection([('Update','Update'),('Deletion','Deletion')], string="Method")
	price_adjustment_line = fields.Many2one('sale.order.line', string="Adjustment Line")
	price_subtotal = fields.Float(string="Subtotal")


	@api.onchange('sale_line_id')
	def onchange_sale_line(self):
		for line in self:
			if line.sale_line_id:
				line.old_product_id = line.sale_line_id.product_id and line.sale_line_id.product_id.id
				line.new_product_id = line.sale_line_id.product_id and line.sale_line_id.product_id.id
				line.old_description = line.sale_line_id.name
				line.new_description = line.sale_line_id.name
				line.sale_line_display_name = line.sale_line_id.display_name
				line.price_subtotal = line.sale_line_id.price_subtotal

	def update_products(self):

		if self.method=='Update':
			# 1.update saleline
			self.sale_line_id.write({'product_id':self.new_product_id.id,'name':self.new_description})
			contract_line_ids = self.env['od.asp.contract.line'].search([('order_line_id','=',self.sale_line_id.id)])
			for contract_line_id in contract_line_ids:
				#2.contractline
				contract_line_id.write({'product_id':self.new_product_id.id,'name':self.new_description})
				if contract_line_id.payment_id:
					# 3.update cost line
					for cost_line_id in contract_line_id.payment_id.costing_line_ids:
						cost_line_id.write({'product_id':self.new_product_id.id})
				# 4.update invoice lines
				if contract_line_id.invoice_line_ids:
					for invoice_line_id in contract_line_id.invoice_line_ids:
						invoice_line_id.write({'product_id':self.new_product_id.id,'name':self.new_description})



class OrchidContractCorrectionLine(models.Model):
	_name = 'od.contract.correction.line'
	_description = "Contract Correction Utility Line"

	utility_id = fields.Many2one('od.product.correction', string="Utility", copy=False, ondelete="cascade")
	contract_line_id = fields.Many2one('od.asp.contract.line', string="Contract Line")
	contract_line_display_name = fields.Char(string="Contract Line")
	old_product_id = fields.Many2one('product.product', string="Old Product", store=True)
	new_product_id = fields.Many2one('product.product', string="New Product")
	old_description = fields.Char(string="Old Description")
	new_description = fields.Char(string="New Description")
	company_id = fields.Many2one('res.company', string="Company", related='utility_id.company_id', store=True)
	method = fields.Selection([('Update','Update'),('Deletion','Deletion')], string="Method")
	price_adjustment_line = fields.Many2one('od.asp.contract.line', string="Adjustment Line")
	price_subtotal = fields.Float(string="Subtotal")

	@api.onchange('contract_line_id')
	def onchange_sale_line(self):
		for line in self:
			if line.contract_line_id:
				line.old_product_id = line.contract_line_id.product_id and line.contract_line_id.product_id.id
				line.new_product_id = line.contract_line_id.product_id and line.contract_line_id.product_id.id
				line.old_description = line.contract_line_id.name
				line.new_description = line.contract_line_id.name
				line.contract_line_display_name = line.contract_line_id.display_name
				line.price_subtotal = (line.contract_line_id.price_unit*line.contract_line_id.product_uom_qty*line.contract_line_id.frequency)


	def update_products(self):

		if self.method=='Update':
			# 1.update saleline
			self.contract_line_id.write({'product_id':self.new_product_id.id,'name':self.new_description})
			contract_line_ids = self.contract_line_id
			for contract_line_id in contract_line_ids:
				#2.contractline
				contract_line_id.write({'product_id':self.new_product_id.id,'name':self.new_description})
				if contract_line_id.payment_id:
					# 3.update cost line
					for cost_line_id in contract_line_id.payment_id.costing_line_ids:
						cost_line_id.write({'product_id':self.new_product_id.id})
				# 4.update invoice lines
				if contract_line_id.invoice_line_ids:
					for invoice_line_id in contract_line_id.invoice_line_ids:
						invoice_line_id.write({'product_id':self.new_product_id.id,'name':self.new_description})


			






			




