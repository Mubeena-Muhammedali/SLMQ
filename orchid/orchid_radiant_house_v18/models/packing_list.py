from odoo import models, fields, api, _
from datetime import datetime
from collections import defaultdict
from odoo.exceptions import UserError

class stock_picking(models.Model):
	_inherit = "stock.picking"
	
	od_packing_list_ids = fields.One2many('od.stock.packing.list','picking_id',string="Packing List")

	# def filter_products(self, product_list):
	# 	checked_id = []
	# 	filtered_list = []
	# 	temp_pro_list = product_list
	# 	for product in temp_pro_list:
	# 		name = product.product_id.name
	# 		if product.check:
	# 			for check_p in temp_pro_list:
	# 				if check_p.product_id.name == name and check_p.check and check_p.id not in checked_id:
	# 					filtered_list.append(check_p)
	# 					checked_id.append(check_p.id)
	# 	return filtered_list
		
	def od_copy(self):
		if self.state=='draft':
			picking_id = self.id
			lines = self.od_packing_list_ids
			for line in lines:
				if line.od_duplicate:
					product_id = line.product_id and line.product_id.id
					pallet_no = line.pallet_no
					carton_number = line.carton_number
					no_of_cartons = line.no_of_cartons
					labels_per_reel = line.labels_per_reel
					reels_per_carton = line.reels_per_carton
					gross_weight = line.gross_weight
					net_weight = line.net_weight
					check =line.check
					vals = {'od_duplicate': False,'picking_id':picking_id,'product_id':product_id, 'pallet_no':pallet_no,
							'carton_number':carton_number, 'no_of_cartons':no_of_cartons,
							'labels_per_reel':labels_per_reel, 'reels_per_carton':reels_per_carton,
							'gross_weight':gross_weight,'net_weight':net_weight, 'check':check}
					self.env['od.stock.packing.list'].create(vals)

	def od_get_grouped_packing_lines(self):
		grouped = defaultdict(list)

		for line in self.od_packing_list_ids:
			if line.product_id:
				grouped[line.product_id].append(line)

		result = []
		for product, lines in grouped.items():
			total = sum(line.total for line in lines)
			result.append({
				'product': product,
				'lines': lines,
				'total': total,
			})
		# print("resultttt",result)

		return result

	def button_validate(self):
		if self.picking_type_code=='outgoing':
			for line in self.move_ids:
				if line.product_id and line.quantity:
					# print("llll",line.picking_id)
					avail_qty = line.product_id.with_context({'location': self.location_id.id,'company_id':self.company_id.id}).qty_available or 0
					print("jjjj",avail_qty)
					if avail_qty < line.quantity:
						message = f"You cannot validate the picking, Not enough quantity for product {line.product_id.display_name}"
						raise UserError(_(message))
		return super(stock_picking, self).button_validate()

class od_stock_packing_list(models.Model):
	_name = "od.stock.packing.list"
	description = "Packing List"

	@api.depends('no_of_cartons','labels_per_reel','reels_per_carton')
	def _compute_vals(self):
		for record in self:
			no_of_cartons = record.no_of_cartons
			labels_per_reel = record.labels_per_reel
			reels_per_carton = record.reels_per_carton
			labels_per_carton = labels_per_reel * reels_per_carton
			total = labels_per_carton * no_of_cartons
			record.labels_per_carton = labels_per_carton
			record.total = total
	   

	product_id = fields.Many2one('product.product',string='Product',required=True)
	picking_id = fields.Many2one('stock.picking',string="Picking")
	check = fields.Boolean(string="Check", default=True)
	pallet_no = fields.Char(string="Pallet Number")
	carton_number = fields.Char(string="Carton Number")
	no_of_cartons = fields.Float("Number of Cartons")
	labels_per_reel = fields.Float(string="Labels Per Reel",)
	reels_per_carton = fields.Float(string="Reels Per Carton")
	labels_per_carton = fields.Float(string="Labels Per Carton",compute="_compute_vals")
	total = fields.Float(string="Total",compute="_compute_vals")
	gross_weight=  fields.Float(string="Gross Weight")
	net_weight = fields.Float(string="Net Weight")
	od_duplicate = fields.Boolean(string="Duplicate", help="Check to duplicate the line")