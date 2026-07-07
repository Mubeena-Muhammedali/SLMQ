# -*- coding: utf-8 -*-
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, AccessError
import datetime

class N2Nbundle(models.Model):
	_name = 'n2n.bundle'
	_description = "Bundle"
	_inherit = ['mail.thread']

	@api.depends('bundle_pack_line.sub_total')
	def _amount_pack_total(self):
		for line in self:
			total = 0.0
			for pack in line.bundle_pack_line:
				total += pack.sub_total
			line.update({
				'pack_total':total,
				})

	@api.depends('bundle_unpack_line.sub_total')
	def _amount_unpack_total(self):
		for line1 in self:
			total1 = 0.0
			for unpack in line1.bundle_unpack_line:
				total1 += unpack.sub_total
			line1.update({
				'unpack_total':total1,
				})


	name = fields.Char('Name',required=True,default='/',readonly="1")
	bundle_pack_line = fields.One2many('n2n.bundle.pack.line', 'bundle_pack_id', string='Bundle Pack Lines',tracking=True)
	bundle_unpack_line = fields.One2many('n2n.bundle.unpack.line', 'bundle_unpack_id', string='Bundle Unpack Lines',tracking=True)
	amount_total = fields.Float('Total',readonly="1",tracking=True)
	pack_total = fields.Monetary(string='Packed Product Total', store=True, readonly=True, compute='_amount_pack_total', tracking=True)
	unpack_total = fields.Monetary(string='Unpacked Product Total', store=True, readonly=True, compute='_amount_unpack_total', tracking=True)
	location_id = fields.Many2one('stock.location',required=True,domain=[('usage','=','internal')],string="Location",tracking=True)
	journal_id = fields.Many2one('account.journal', required=True, domain=[('type','=','general')], string="Journal",tracking=True)
	bundle_type = fields.Selection([
			('unpacking','UnPacking'),
			('packing','Packing'),
		], string='Operation',required=True,tracking=True)
	state = fields.Selection([
			('draft','Draft'),
			('partial', 'Partially Completed'),
			('done','Done'),
		],string='Status',default='draft',tracking=True)
	currency_id = fields.Many2one('res.currency', string='Account Currency',tracking=True)
	move_ids = fields.One2many('stock.move', 'nn_bundle_id', string='Created Moves',tracking=True)
	bundle_date = fields.Date("Bundle Date",tracking=True)
	force_date = fields.Date("Force Date",tracking=True)
	document_date = fields.Date(string="Document Date",default=fields.Date.context_today)
	bundle_loc_id = fields.Many2one('stock.location', string="Bundle Location")

	
	@api.model
	def create(self, vals):
		if vals.get('name','/')=='/':
			vals['name'] = self.env['ir.sequence'].next_by_code('n2n.bundle') or '/'
		return super(N2Nbundle, self).create(vals)

	def action_force_date(self):
		if self.force_date:
			reff= self.name
			f_date = self.force_date
			for stock_ref in self.env['stock.move'].search([('origin', '=', reff)]):
				stock_ref.write({'date': f_date})
				move_lines = self.env['account.move'].search([('stock_move_id','=', stock_ref.id)])
				move_lines.write({'date': f_date})

	def input_transfer(self):
		for obj in self:

			#checking the totals of two lines
			total_pack_line = 0
			total_unpack_line = 0
			pack_line_unit_cost = 0
			if not obj.bundle_pack_line:
				raise UserError(_('Settings Warning!,In lines are not found'))

			if not obj.bundle_unpack_line:
				raise UserError(_('Settings Warning!,Out lines are not found'))
				
			for total_pack in obj.bundle_pack_line:
				if total_pack.quantity <= 0:
					raise UserError(_('Settings Warning!,Qty should not be zero'))
					
				
				total_pack_line = total_pack_line + total_pack.sub_total
				pack_line_unit_cost+=total_pack.price

			for total_unpack in obj.bundle_unpack_line:
				if total_unpack.available_qty <=0 or total_unpack.available_qty < total_unpack.quantity:
					raise UserError(_('The available quantity of the product is %s'%total_unpack.available_qty))
				if total_unpack.quantity <= 0:
					raise UserError(_('Settings Warning!,Qty should not be zero'))
				total_unpack_line = total_unpack_line + total_unpack.sub_total
			
			if self.bundle_type=='packing':
				if str(pack_line_unit_cost) != str(total_unpack_line):
					raise UserError(_('Settings Warning!,Costs are not matching'))
			else:
				if str(total_pack_line) != str(total_unpack_line):
					raise UserError(_('Settings Warning!,total amounts are not matching'))
				

			#finding source and destination location           
			date_expected = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

			# parameter_obj = self.env['ir.config_parameter']
			# parameter_id = parameter_obj.search([('key', '=', 'def_bundle_loc')])
			# if not parameter_id:
			# 	raise UserError(_('Settings Warning!,No bundle loc\nPlz config it in System Parameters with def_bundle_loc!'))
			# parameter_data = parameter_obj.browse(parameter_ids)
			bundle_loc_id = self.bundle_loc_id.id
			source_loc_id =obj.location_id and obj.location_id.id



			for bundle_un in obj.bundle_unpack_line:
				if bundle_un.product_id.tracking=='serial':
					quant_ids = self.env['stock.quant'].search([('product_id', '=', bundle_un.product_id.id),('lot_id','=',bundle_un.lot_id.id)])
					if not quant_ids:
						raise UserError(_('Warning!,no quant value found'))
						
					
						
			
				product_uom_id = (self.env['product.product'].browse(bundle_un.product_id.id)).uom_id.id
				# vals1 = {
				# 			'product_id':bundle_un.product_id.id,
				# 			'product_uom_qty':bundle_un.quantity,
				# 			'product_uom':product_uom_id,
				# 			'origin':obj.name,
				# 			'location_id':source_loc_id,
				# 			'location_dest_id':bundle_loc_id,
				# 			'state':'draft',
				# 			'price_unit':bundle_un.price,
				# 			'date_expected':date_expected,
				# 			'name':bundle_un.product_id.name,
				# 			'restrict_lot_id':bundle_un.lot_id.id or False,
				# 			'od_journal_id':self.journal_id.id,
				# 			'nn_unbundle_line_id':bundle_un.id,
				# 			'nn_bundle_id':self.id,
				# }
				vals1 = {
					'name': bundle_un.product_id.name,
					'product_id': bundle_un.product_id.id,
					'product_uom': product_uom_id,
					'product_uom_qty': bundle_un.quantity,
					'quantity':bundle_un.quantity,
					# 'company_id': self.company_id.id or self.env.company.id,
					'state': 'confirmed',
					'location_id': source_loc_id,
					'location_dest_id': bundle_loc_id,
					# 'restrict_partner_id':  self.owner_id.id,
					'is_inventory': True,
					'picked': True,
					'od_journal_id':self.journal_id.id,
					'nn_unbundle_line_id':bundle_un.id,
					'nn_bundle_id':self.id,
					'price_unit':bundle_un.price,
					'move_line_ids': [(0, 0, {
						'product_id': bundle_un.product_id.id,
						'product_uom_id': product_uom_id,
						'quantity': bundle_un.quantity,
						'location_id': source_loc_id,
						'location_dest_id': bundle_loc_id,
						# 'company_id': self.company_id.id or self.env.company.id,
						'lot_id': bundle_un.lot_id.id or False,
						# 'package_id': package_id.id if package_id else False,
						# 'result_package_id': package_dest_id.id if package_dest_id else False,
						# 'owner_id': self.owner_id.id,
					})]
				}
				# stock_id = self.env['stock.move'].with_context(inventory_mode=False).create(vals1)
				print("vallll",vals1)
				# print(s)
				stock_id = self.env['stock.move'].create(vals1)
				stock_id._action_done()
				# stock_id = self.env['stock.move'].create(vals1)
				# stock_id.action_done()

				n_unbundle_line_id = bundle_un.id  
				# if n_unbundle_line_id:
				# 	move1 = self.env['stock.move'].search([('nn_unbundle_line_id', '=', n_unbundle_line_id)])
				# 	for move in move1:
				# 		bundle_un.price = move.price_unit
 
		self.write({'state':'partial'})              
		return True

	def output_transfer(self):
		for obj in self:
			total_pack_line = 0
			total_unpack_line = 0
			if not obj.bundle_pack_line:
				raise UserError(_('Settings Warning!,In lines are not found'))

			if not obj.bundle_unpack_line:
				raise UserError(_('Settings Warning!,Out lines are not found'))
				
			for total_pack in obj.bundle_pack_line:
				if total_pack.quantity <= 0:
					raise UserError(_('Settings Warning!,Qty should not be zero'))
					
				
				total_pack_line = total_pack_line + total_pack.sub_total

			for total_unpack in obj.bundle_unpack_line:

				if total_unpack.quantity <= 0:
					raise UserError(_('Settings Warning!,Qty should not be zero'))
#                total_unpack_line += round(total_unpack.sub_total,2)
				total_unpack_line = total_unpack_line + total_unpack.sub_total	

			if str(total_pack_line) != str(total_unpack_line):
				raise UserError(_('Settings Warning!,total amounts are not matching'))
				

			#finding source and destination location           
			date_expected = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

			# parameter_obj = self.env['ir.config_parameter']
			# parameter_id = parameter_obj.search([('key', '=', 'def_bundle_loc')])
			# if not parameter_id:
			# 	raise UserError(_('Settings Warning!,No bundle loc\nPlz config it in System Parameters with def_bundle_loc!'))
			# bundle_loc_id = parameter_id.nn_model_id and parameter_id.nn_model_id.id
			bundle_loc_id = self.bundle_loc_id.id

			source_loc_id =obj.location_id and obj.location_id.id


			for bundle_in in obj.bundle_pack_line:			
				product_uom_id = (self.env['product.product'].browse(bundle_in.product_id.id)).uom_id.id
				# vals = {
				# 		'product_id':bundle_in.product_id.id,
				# 		'product_uom_qty':bundle_in.quantity,
				# 		'product_uom':product_uom_id,
				# 		'origin':obj.name,
				# 		'location_id':bundle_loc_id,
				# 		'location_dest_id':source_loc_id,
				# 		'state':'draft',
				# 		'date_expected':date_expected,
				# 		'price_unit':bundle_in.price,
				# 		'name':bundle_in.product_id.name,
				# 		'restrict_lot_id':bundle_in.lot_id.id or False,
				# 		'od_journal_id':self.journal_id.id,
				# 		'nn_bundle_id':self.id,
				# }
				# stock_move_id = self.env['stock.move'].create(vals)
				# stock_move_id.action_done()

				vals = {
					'name': bundle_in.product_id.name,
					'product_id': bundle_in.product_id.id,
					'product_uom': product_uom_id,
					'product_uom_qty': bundle_in.quantity,
					# 'company_id': self.company_id.id or self.env.company.id,
					'state': 'confirmed',
					'location_dest_id': source_loc_id,
					'location_id': bundle_loc_id,
					# 'restrict_partner_id':  self.owner_id.id,
					'is_inventory': True,
					'picked': True,
					'od_journal_id':self.journal_id.id,
					# 'nn_unbundle_line_id':bundle_in.id,
					'nn_bundle_id':self.id,
					'price_unit':bundle_in.price,
					'move_line_ids': [(0, 0, {
						'product_id': bundle_in.product_id.id,
						'product_uom_id': product_uom_id,
						'quantity': bundle_in.quantity,
						'location_dest_id': source_loc_id,
						'location_id': bundle_loc_id,
						# 'company_id': self.company_id.id or self.env.company.id,
						'lot_id': bundle_in.lot_id.id or False,
						# 'package_id': package_id.id if package_id else False,
						# 'result_package_id': package_dest_id.id if package_dest_id else False,
						# 'owner_id': self.owner_id.id,
					})]
				}
				print(vals)
				# stock_id = self.env['stock.move'].with_context(inventory_mode=False).create(vals1)
				stock_move_id = self.env['stock.move'].create(vals)
				stock_move_id._action_done()

		self.write({'state':'done'})              
		return True


 
	def compute_cost_for_items(self):
		sub_total = 0
		for obj in self:

			for lines in obj.bundle_unpack_line:
				if lines.quantity <=0:
					raise UserError(_('quantity should not less than or equal to zero'))
				sub_total =  sub_total + lines.sub_total


			for pack in obj.bundle_pack_line:
				if pack.quantity <=0:
					raise UserError(_('quantity should not less than or equal to zero'))
				sub = sub_total / pack.quantity

				pack.write({'price':sub})
				
		return True

	def distribute(self):
		subtotal =0.0
		qty=0.0
		amount =0.0
		for line in self.bundle_unpack_line:
			if line.quantity <=0:
				raise UserError(_('quantity should not less than or equal to zero'))
			subtotal =  subtotal + line.sub_total
		for pack_qty in self.bundle_pack_line:
			qty = qty + pack_qty.quantity
		if subtotal:
			amount = subtotal/qty
		for pack in self.bundle_pack_line:
			pack.price = amount   

	@api.constrains('bundle_type','bundle_pack_line','bundle_unpack_line')
	def _check_constriant(self):
		unpack_ids = []
		pack_ids = []
		bundle_type = self.bundle_type
		if bundle_type == 'unpacking':
			for obj in self.bundle_unpack_line:
				unpack_ids.append(obj.id)
			if len(unpack_ids) != 1:
				raise UserError(_("unpacking can done one bundle product at a time or incorrect entering of bundle product details"))


		if bundle_type == 'packing':
			for objc in self.bundle_pack_line:
				pack_ids.append(objc.id)
			if len(pack_ids) != 1:
				raise UserError(_("packing can done one bundle Product at a time or incorrect entering of bundle product details"))              
		
		return True

	def action_get_bundle_stock_moves(self):
		self.ensure_one()
		action_ref = self.env.ref('stock.stock_move_action')
		if not action_ref:
			return False
		action_data = action_ref.read()[0]
		action_data['domain'] = [('id', 'in', self.move_ids.ids)]
		return action_data

	@api.onchange('location_id')
	def onchange_location(self):
		for record in self:
			if record.bundle_unpack_line:
				record.bundle_unpack_line.onchange_pdt()

	@api.onchange('unpack_total','bundle_pack_line')
	def onchange_price(self):
		for record in self:
			if record.bundle_pack_line and record.bundle_type=='packing':
				record.bundle_pack_line.write({'price':record.unpack_total})




class N2NbundlePackLine(models.Model):
	_name = 'n2n.bundle.pack.line'

	@api.depends('quantity', 'price')
	def _compute_total(self): 
		for obj in self:
			obj.sub_total = obj.price * obj.quantity

	def onchange_lot_id(self,lot_id):
		result = {}
		if lot_id:
			result = {'value': {
			
		}}
		
		return result

	@api.model
	def create(self,vals):
		if self.env['n2n.bundle'].browse(vals['bundle_pack_id']).state in ('partial','done'):
			raise UserError(_("The Bundle is not in draft state!!"))              
		return super(N2NbundlePackLine, self).create(vals)


	bundle_pack_id = fields.Many2one('n2n.bundle', string='Bundle',ondelete='cascade', copy=False)
	product_id = fields.Many2one('product.product', string='Product',required=True)
	lot_id = fields.Many2one('stock.lot', 'Lot No')
	quantity = fields.Float('Quantity')
	price = fields.Float('Cost')
	sub_total = fields.Float(string='Total',store=True, readonly=True, compute='_compute_total')
	# state=fields.Char(string="State", related="bundle_pack_id.state")
	state = fields.Selection([
			('draft','Draft'),
			('partial', 'Partially Completed'),
			('done','Done'),
		],string='Status',default='draft',related="bundle_pack_id.state")



class N2NbundleUnpackLine(models.Model):
	_name = 'n2n.bundle.unpack.line'

	@api.model
	def create(self,vals):
		if self.env['n2n.bundle'].browse(vals['bundle_unpack_id']).state in ('partial','done'):
			raise UserError(_("The Bundle is not in draft state!!"))              
		return super(N2NbundleUnpackLine, self).create(vals)

	@api.depends('quantity', 'price')
	def _compute_total(self): 
		for obj in self:
			obj.sub_total = obj.price * obj.quantity

	@api.onchange('product_id')
	def onchange_pdt(self):
		for line in self:
			if line.product_id:
				product_id = line.product_id.id
				location_id = line.bundle_unpack_id.location_id.id
				# domain = [('product_id', '=', product_id),('location_id', '=', location_id)]
				# lot_id = line.lot_id.id or False
				# if lot_id:
				# 	domain.append(('lot_id', '=', lot_id))
				# quant_obj = line.env['stock.quant'].search(domain)
				qty = line.product_id.with_context(location_id=location_id,lot_id=self.lot_id.id).qty_available
				# cost = 0.0
				# qty = sum([prod.quantity for prod in quant_obj])
				# inventory_value = sum([prod.inventory_value for prod in quant_obj])
				# if inventory_value:
				#     cost = inventory_value /qty
				# self.price = cost
				line.available_qty = qty
				line.price = line.product_id.standard_price	

	def onchange_lot_id(self,lot_id):
		result = {}
		if lot_id:
			result = {'value': {
		   
		}}
		
		return result

	bundle_unpack_id = fields.Many2one('n2n.bundle', string='Bundle',ondelete='cascade', copy=False)
	product_id = fields.Many2one('product.product', string='Product',required=True)
	lot_id = fields.Many2one('stock.lot', 'Lot No')
	available_qty = fields.Float('Available')
	quantity = fields.Float('Quantity')
	price = fields.Float('Cost')
	sub_total = fields.Float(string='Total',store=True, readonly=True, compute='_compute_total')
	# state=fields.Char(string="State", related="bundle_unpack_id.state")
	state = fields.Selection([
			('draft','Draft'),
			('partial', 'Partially Completed'),
			('done','Done'),
		],string='Status',default='draft',related="bundle_unpack_id.state")


class StockMove(models.Model):
	_inherit = "stock.move"

	od_journal_id = fields.Many2one('account.journal', string="Journal")
	nn_unbundle_line_id = fields.Many2one('n2n.bundle.unpack.line', 'Unpack')
	nn_bundle_id = fields.Many2one('n2n.bundle', 'Bundle')

	# def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id):
	# 	res = super(StockMove,self)._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id)
	# 	for _,_,line in res:
	# 		if self.od_journal_id:
	# 			line['journal_id'] = self.od_journal_id.id
	# 	return res

	def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
		res = super(StockMove,self)._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
		if res.get('journal_id'):
			if self.od_journal_id:
				res['journal_id'] = self.od_journal_id and self.od_journal_id.id
		return res
