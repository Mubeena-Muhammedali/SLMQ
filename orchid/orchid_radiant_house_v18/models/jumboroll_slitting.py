# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidJumboRollSplitting(models.Model):
	_name = 'orchid.jumboroll.slitting'
	_inherit = ['mail.thread']
	description = 'Jumbo Roll Slitting'

	name = fields.Char('Name',required="1",default='/',readonly=True, tracking=True)
	output_line = fields.One2many('orchid.jumboroll.output.line', 'output_slitting_id', string='Output Lines')
	input_line = fields.One2many('orchid.jumboroll.input.line', 'input_slitting_id', string='Input Lines')
	output_qty_total = fields.Float(string='Total Output Quantity', store=True, readonly=True, compute='_qty_output_total', tracking=True)
	input_qty_total = fields.Float(string='Total Input Quantity', store=True, readonly=True, compute='_qty_input_total', tracking=True)
	location_id = fields.Many2one('stock.location',required=True,domain=[('usage','=','internal')],string="Location", tracking=True)
	state = fields.Selection([
				('draft','Draft'),
				('partial', 'Partially Completed'),
				('done','Done'),
			],string='Status',default='draft', tracking=True)
	move_ids = fields.One2many('stock.move', 'od_slitting_id', string='Created Moves')
	date = fields.Date("Date", tracking=True)
	company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, tracking=True)

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			vals['name'] = self.env['ir.sequence'].next_by_code('orchid.jumboroll.slitting')
		return super(OrchidJumboRollSplitting, self).create(vals_list)

	@api.depends('output_line.quantity')
	def _qty_output_total(self):
		for record in self:
			total = 0.0
			for output in record.output_line:
				total += output.quantity
			record.update({
				'output_qty_total':total,
				})

	@api.depends('input_line.quantity')
	def _qty_input_total(self):
		for record in self:
			total1 = 0.0
			for line2 in record.input_line:
				total1 += line2.quantity
			record.update({
				'input_qty_total':total1,
				})


	def action_get_slitting_stock_moves(self):
		self.ensure_one()
		action_ref = self.env.ref('orchid_radiant_house_v18.od_action_jumboroll_moves')
		if not action_ref:
			return False
		action_data = action_ref.read()[0]
		action_data['domain'] = [('move_id', 'in', self.move_ids.ids)]
		return action_data
	
	def compute_cost_for_items(self):
		sub_total = 0
		for obj in self:
			for ilines in obj.input_line:
				if ilines.quantity <=0:
					raise UserError(_('quantity should not less than or equal to zero'))
				cost =  ilines.price
			for olines in obj.output_line:
				if olines.quantity <=0:
					raise UserError(_('quantity should not less than or equal to zero'))
				olines.write({'price':cost})
		return True

	def transfer_errcheck(self):
		for obj in self:
		#checking the totals of two lines
			total_output_line = 0
			total_input_line = 0
			if not obj.output_line:
				raise UserError(_('Settings Warning!,Out lines are not found'))

			if not obj.input_line:
				raise UserError(_('Settings Warning!,Input lines are not found'))
				
			for oline in obj.output_line:
				if oline.quantity <= 0:
					raise UserError(_('Settings Warning!,Qty should not be zero'))
				total_output_line = total_output_line + oline.quantity

			for iline in obj.input_line:
				if iline.available_qty <=0 or iline.available_qty < iline.quantity:
					raise UserError(_('The available quantity of the product is %s'%iline.available_qty))
				if iline.quantity <= 0:
					raise UserError(_('Settings Warning!'),_('Qty should not be zero'))
				total_input_line = total_input_line + iline.quantity
			
			if str(total_output_line) != str(total_input_line):
				raise UserError(_('Settings Warning!,total input quantities and output quantities are not matching'))

			date_expected = fields.Datetime.now()
			# parameter_obj = self.env['ir.config_parameter']
			# parameter_id = parameter_obj.search([('key', '=', 'def_slitting_loc')])
			# print("kjhvvvvvvvvvvvvvvv",parameter_id)
			# if (not parameter_id) or (not int(parameter_id.value)):
			# 	raise UserError(_('Settings Warning!,No Slitting location\nPlz config it in System Parameters with def_slitting_loc!'))
			# slitting_loc_id = int(parameter_id.value)
			slitting_loc_id = self.company_id.def_slitting_loc_id and self.company_id.def_slitting_loc_id.id
			if not (slitting_loc_id):
				raise UserError(_("Please set Slitting Location!!"))
		
			source_loc_id =obj.location_id and obj.location_id.id

			return slitting_loc_id,source_loc_id,date_expected

	def output_transfer(self):
		for obj in self:
			slitting_loc_id,source_loc_id,date_expected = obj.transfer_errcheck()

			for oline in obj.output_line:			
				product_uom_id = (self.env['product.product'].browse(oline.product_id.id)).uom_id.id
				vals = {
					'name':oline.product_id.name,
					'product_id':oline.product_id.id,
					'product_uom':product_uom_id,
					'product_uom_qty':oline.quantity,
					'quantity':oline.quantity,
					'origin':obj.name,
					'location_id':slitting_loc_id,
					'location_dest_id':source_loc_id,
					'state':'confirmed',
					'date_deadline':date_expected,
					'price_unit':oline.price,
					# 'lot_ids':[(6,0,oline.lot_id.ids)],
					'od_slitting_id':self.id,
					'company_id': self.company_id.id,
					'is_inventory': True,
					'picked': True,
					'move_line_ids': [(0, 0, {
						'product_id': oline.product_id.id,
						'product_uom_id': product_uom_id,
						'quantity': oline.quantity,
						'location_id': slitting_loc_id,
						'location_dest_id': source_loc_id,
						'lot_id': oline.lot_id.id or False,
						})]
							
				}
				print("vvvvv",vals)
				stock_move_id = self.env['stock.move'].create(vals)
				stock_move_id._action_done()
		self.write({'state':'done'})              
		return True

	def input_transfer(self):
		for obj in self:
			slitting_loc_id,source_loc_id,date_expected = obj.transfer_errcheck()
			for iline in obj.input_line:
				if iline.lot_id:
					quant_ids = self.env['stock.quant'].search([('product_id', '=', iline.product_id.id),('lot_id','=',iline.lot_id.id)])
					if not quant_ids:
						raise UserError(_('Warning!,no quant value found'))
				product_uom_id = (self.env['product.product'].browse(iline.product_id.id)).uom_id.id
				vals1 = {
							'name':iline.product_id.name,
							'product_id':iline.product_id.id,
							'product_uom':product_uom_id,
							'product_uom_qty':iline.quantity,
							'quantity':iline.quantity,
							'origin':obj.name,
							'location_id':source_loc_id,
							'location_dest_id':slitting_loc_id,
							'state':'confirmed',
							'price_unit':iline.price,
							'is_inventory': True,
							'picked': True,
							'date_deadline':date_expected,
							# 'lot_ids':[(6,0,iline.lot_id.ids)],
							'od_jumboroll_input_line_id':iline.id,
							'od_slitting_id':self.id,
							'company_id': self.company_id.id,
							'move_line_ids': [(0, 0, {
								'product_id': iline.product_id.id,
								'product_uom_id': product_uom_id,
								'quantity': iline.quantity,
								'location_id': source_loc_id,
								'location_dest_id': slitting_loc_id,
								'lot_id': iline.lot_id.id or False,
								})]
							}
				stock_id = self.env['stock.move'].create(vals1)
				stock_id._action_done()
				# od_jumboroll_input_line_id = iline.id  
				# if od_jumboroll_input_line_id:
				# 	move1 = self.env['stock.move'].search([('od_jumboroll_input_line_id', '=', od_jumboroll_input_line_id)])
				# 	for move in move1:
				# 		iline.price = move.price_unit
		self.write({'state':'partial'})  
		self.compute_cost_for_items()   
		return True

class OrchidJumborollOutputLine(models.Model):
	_name = 'orchid.jumboroll.output.line'
	description = 'Jumbo Roll Slitting Output Line'
	
	@api.depends('quantity', 'price')
	def _compute_total(self): 
		for line in self:
			line.sub_total = round(line.price,2) * line.quantity

	output_slitting_id = fields.Many2one('orchid.jumboroll.slitting', string='Jumboroll Slitting',ondelete='cascade')
	product_id = fields.Many2one('product.product', string='Product',required="1")
	lot_id = fields.Many2one('stock.lot', 'Lot No', domain="[('product_id','=',product_id)]")
	quantity = fields.Float('Quantity')
	price = fields.Float('Cost')
	sub_total = fields.Float(string='Total',store=True, readonly=True, compute='_compute_total')
	company_id = fields.Many2one('res.company', string="Company", related='output_slitting_id.company_id')


class OrchidJumborollInputLine(models.Model):
	_name = 'orchid.jumboroll.input.line'
	description = 'Jumbo Roll Slitting input Line'

	@api.depends('quantity', 'price')
	def _compute_total(self): 
		for line in self:
			line.sub_total = round(line.price,2)* line.quantity

	@api.onchange('product_id','lot_id')
	def onchange_pdt(self):
		for line in self:
			if not line.input_slitting_id.location_id.id:
				raise UserError(_('Please Set a Location'))
			if line.product_id:
				product_id = line.product_id.id
				location_id = line.input_slitting_id.location_id.id
				domain = [('product_id', '=', product_id),('location_id', '=', location_id)]
				lot_id = line.lot_id.id or False
				if lot_id:
					domain.append(('lot_id', '=', lot_id))
				quant_obj = line.env['stock.quant'].search(domain)
				qty = sum([prod.available_quantity for prod in quant_obj])
				line.available_qty = qty
				line.price = line.product_id.standard_price

	input_slitting_id = fields.Many2one('orchid.jumboroll.slitting', string='Jumboroll Slitting',ondelete='cascade')
	product_id = fields.Many2one('product.product', string='Product',required="1")
	lot_id = fields.Many2one('stock.lot', 'Lot No', domain="[('product_id','=',product_id)]")
	available_qty = fields.Float('Available')
	quantity = fields.Float('Quantity')
	price = fields.Float('Cost')
	sub_total = fields.Float(string='Total',store=True, readonly=True, compute='_compute_total')
	company_id = fields.Many2one('res.company', string="Company", related='input_slitting_id.company_id')

class StockMove(models.Model):
	_inherit = "stock.move"

	od_jumboroll_input_line_id = fields.Many2one('orchid.jumboroll.input.line', 'Input')
	od_slitting_id = fields.Many2one('orchid.jumboroll.slitting', 'Jumboroll Slitting')





