# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.stock_landed_costs.models.stock_landed_cost import SPLIT_METHOD


class OrchidGrnNo(models.Model):
	_name = "orchid.grn.no"
	_inherit = ['mail.thread']

	name = fields.Char(string="GRN No.", tracking=True)
	import_invoice_no = fields.Char(string="Import Invoice No.", tracking=True)
	warehouse_recipt_no = fields.Char(string="Warehouse Receipt No.", tracking=True)
	grn_date = fields.Date(string="GRN Date", tracking=True)
	supplier_id = fields.Many2one('res.partner', string="Supplier", tracking=True)
	grn_lines = fields.One2many('orchid.grn.line','grn_id', string="GRN Lines")
	state = fields.Selection([
	  ('draft',"Draft"),('lock',"Locked"),
	  ], default='draft', tracking=True)
	shipment_size = fields.Selection([
	  ('40ft',"40FT CONTAINER"),('20ft',"20FT CONTAINER"),('lcl',"LCL"),('air',"AIR"),('express',"EXPRESS"),
	  ], string="Size of Shipment", tracking=True)

	def button_lock(self):
		self.write({'state':'lock'})

	def button_unlock(self):
		self.write({'state':'draft'})

	def button_search(self):
		if self.grn_lines:
			self.grn_lines.unlink()
		# self.searched = False
		values={}
		line_qry = '''SELECT 
						sp.origin,
						-- tmpl.name as product_id,
						prd.id as product_id,
						sp.partner_id as supplier,
						sum(sml.qty_done) as quantity,
						pol.price_unit as price_unit,
						pol.price_unit*sum(sml.qty_done) as total
						FROM stock_picking sp
						LEFT JOIN stock_move_line sml ON sml.picking_id = sp.id
						LEFT JOIN stock_move sm ON sm.id = sml.move_id
						LEFT JOIN purchase_order_line pol ON pol.id = sm.purchase_line_id
						LEFT JOIN product_product prd ON sml.product_id = prd.id
						-- LEFT JOIN product_template tmpl ON prd.product_tmpl_id = tmpl.id
						LEFT JOIN orchid_grn_no og ON og.id = sp.od_grn_no
						WHERE sp.state='done' 
						AND sml.qty_done>0
						 AND og.id = %s
						GROUP BY 
						sp.origin,sp.partner_id,
						prd.id,pol.price_unit
						ORDER BY  sp.origin
					'''%(self.id)


		self.env.cr.execute(line_qry)
		result = self.env.cr.dictfetchall()
		wiz_line = self.env['orchid.grn.line']
		for res in result:
			# total = 0
			# qty = res[]
			wiz_line_id = wiz_line.create({
				'origin'    : res['origin'] or ' ',
				'product_id': res['product_id'] or False,
				'quantity'  : res['quantity'],
				'price_unit': res['price_unit'],
				'total'     : res['total'],
				'grn_id'    : self.id,
			})
		
			self.supplier_id = res['supplier']
		# if self.grn_lines:
		# 	self.searched = True

		# return {
		# 	'view_type': 'form',
		# 	"view_mode": 'form',
		# 	'res_model': 'orchid.grn.wiz',
		# 	'res_id': self.id,
		# 	'type':'ir.actions.act_window',
		# 	'target': 'new'
		# 	}

class OrchidGrnWizLine(models.Model):
	_name = 'orchid.grn.line'
	_description = 'GRN Report'

	grn_id = fields.Many2one('orchid.grn.no', string="GRN No.")
	origin = fields.Char(string="Purchase Order")
	product_id = fields.Many2one('product.product', string="Product")
	quantity = fields.Float(string="Quantity")
	price_unit = fields.Float(string="Unit Price", digits='Product Price')
	total = fields.Float(string="Total", digits='Product Price')


class StockPicking(models.Model):
	_inherit = "stock.picking"

	od_grn_no = fields.Many2one('orchid.grn.no', string="GRN No.")
	od_import_invoice_no = fields.Char(string="Import Invoice No.")
	shipment_size = fields.Selection([
	  ('40ft',"40FT CONTAINER"),('20ft',"20FT CONTAINER"),('lcl',"LCL"),('air',"AIR"),('express',"EXPRESS"),
	  ], string="Size of Shipment")
	od_gbw_ref_no = fields.Char(string="Warehouse order no.")
	od_local_transportation_id = fields.Many2one('od.local.transport.charge.master',related="sale_id.od_local_transportation_id", string="Delivery Location", tracking=True, store=True)
	od_package_type = fields.Char(string="Package Type")
	od_dimensions = fields.Char(string="Dimensions")
	od_landed_cost_line_ids = fields.One2many('od.landed.cost.line','picking_id', string="Landed Cost Line")
	
	def od_action_open_landed_cost(self):
		landed_ids = self.env['stock.landed.cost'].search([('picking_ids','in',self.ids)])
		action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
		if self.state == 'done':
			if not landed_ids:
				context = {
				'default_picking_ids':[(4,self.id)],
				'create':0,
				}
				action['context'] = context
				action['view_mode'] = 'form'
				action['views'] = [(False, 'form')]
				return action
			if landed_ids:
				return {
				'type':'ir.actions.act_window',
				'name':'Landed Costs',
				'view_mode':'list,form',
				'res_model':'stock.landed.cost',
				'domain':[('id','in',landed_ids.ids)],
				'context':{'create':0},
				}
				


	def button_validate(self):
		result = super(StockPicking, self).button_validate()
		for picking in self:
			if picking.state=='done' and picking.od_grn_no:
				if picking.move_ids and picking.move_ids[0].purchase_line_id:
					po_id = picking.move_ids[0].purchase_line_id.order_id
					if po_id and (not po_id.od_non_inventroy) and (not po_id.od_non_trade_inventory):
						# create landed cost
						if not picking.od_landed_cost_line_ids:
							raise UserError(_("Set Landed Cost Lines to proceed !!"))
						line_ls = []
						for line in picking.od_landed_cost_line_ids:
							vals = {
							'name':line.name,
							'product_id':line.product_id.id,
							'account_id':line.account_id.id,
							'price_unit':line.price_unit,
							'split_method':line.split_method,
							}
							line_ls.append((0,0,vals))
						landed_cost_vals = {
						'picking_ids':[(6,0,picking.ids)],
						'cost_lines':line_ls,
						}
						cost_id = self.env['stock.landed.cost'].create(landed_cost_vals)
						cost_id.button_validate()
		return result



	@api.onchange('od_grn_no')
	def onchange_gn(self):
		if self.od_grn_no:
			self.od_import_invoice_no = self.od_grn_no.import_invoice_no

class OrchidLandedCostLine(models.Model):
	_name = "od.landed.cost.line"

	picking_id = fields.Many2one('stock.picking', string="Picking", copy=False, ondelete="cascade")
	name = fields.Char('Description')
	product_id = fields.Many2one('product.product', 'Product')
	price_unit = fields.Float('Cost')
	split_method = fields.Selection(
		SPLIT_METHOD,
		string='Split Method',
		required=True,
		help="Equal : Cost will be equally divided.\n"
			 "By Quantity : Cost will be divided according to product's quantity.\n"
			 "By Current cost : Cost will be divided according to product's current cost.\n"
			 "By Weight : Cost will be divided depending on its weight.\n"
			 "By Volume : Cost will be divided depending on its volume.")
	account_id = fields.Many2one('account.account', 'Account', domain=[('deprecated', '=', False)])

	@api.onchange('product_id')
	def onchange_product_id(self):
		for line in self:
			line.name = line.product_id.name or ''
			line.split_method = line.product_id.product_tmpl_id.split_method_landed_cost or line.split_method or 'equal'
			line.price_unit = line.product_id.standard_price or 0.0
			accounts_data = line.product_id.product_tmpl_id.get_product_accounts()
			line.account_id = accounts_data['stock_input']


	
