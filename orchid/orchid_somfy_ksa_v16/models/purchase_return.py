 # -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OdPurchaseReturn(models.Model):
	_name = "od.purchase.return"
	_inherit = ['mail.thread']
	_description="Purchase Return"

	name=fields.Char(string="Name")
	date=fields.Date(string="Date", default=fields.Date.today, tracking=True)
	user_id=fields.Many2one('res.users', string="User", default=lambda self:self.env.user, tracking=True)
	picking_id=fields.Many2one('stock.picking', string="Purchase Return", tracking=True, copy=False)
	invoice_id=fields.Many2one('account.move', string="Debit Note", tracking=True, copy=False)
	line_ids = fields.One2many('od.purchase.return.line', 'return_id', string="Lines")
	company_id = fields.Many2one('res.company', string="Company", default=lambda self:self.env.company)
	state = fields.Selection([('draft','Draft'),('return','Returned'),('debit_note','Debit Note Created'),('complete','Completed')], string="state", default="draft")
	partner_id = fields.Many2one('res.partner', string="Partner")

	def button_transfer(self):
		move_vals = []
		od_po_return_picking_type_param = self.env.ref('orchid_somfy_ksa_v16.od_po_return_picking_type') or False
		if (not od_po_return_picking_type_param) or od_po_return_picking_type_param==None:
			raise UserError(_("Please set od_po_return_picking_type"))
		od_po_return_picking_type = int(od_po_return_picking_type_param.value)

		picking_type_id = self.env['stock.picking.type'].browse(od_po_return_picking_type)
		if not picking_type_id:
			raise UserError(_("Picking type with database id %s is not found")%(od_po_return_picking_type))
		location_id = picking_type_id.default_location_src_id.id #TJDWH/Stock
		location_dest_id = self.env.ref('stock.stock_location_suppliers').id #Partners/Vendors
		for line in self.line_ids:
			picking_line_vals = {
					'product_id':line.product_id.id,
					'name':line.product_id.name,
					'product_uom_qty':line.quantity,
					'quantity_done':line.quantity,
					'product_uom':line.product_id.uom_po_id.id,
					'location_id':location_id,
					'location_dest_id':location_dest_id,
					'od_po_return_line_id':line.id,
					}
			move_vals.append((0,0,picking_line_vals))
		if move_vals:
			picking_vals = {
				'partner_id':self.partner_id.id,
				'picking_type_id':picking_type_id.id,
				'location_id':location_id ,#wh/stock
				'location_dest_id':location_dest_id, #wh/wip chnge later
				'origin':self.name,
				'move_ids_without_package':move_vals,
			}
			picking_id = self.env['stock.picking'].create(picking_vals)
			picking_id.action_confirm()
			picking_id.button_validate()
			self.picking_id = picking_id.id
		for line in self.line_ids:
			stock_move_id = picking_id.move_ids.filtered(lambda x:x.od_po_return_line_id.id==line.id).mapped('id')
			if stock_move_id:
				line.stock_move_id = stock_move_id[0]
				price_unit=0
				for sl in line.stock_move_id.stock_valuation_layer_ids:
					price_unit+=sl.unit_cost
				line.stock_move_price_unit = price_unit

		self.state='return'

	def button_debit_note(self):
		invoice_line_ids = []
		for line in self.line_ids:
			invoice_line_vals={
				'product_id':line.product_id.id,
				'quantity':line.quantity,
				'product_uom_id':line.product_id.uom_po_id.id,
				'account_id':line.product_id.categ_id.property_stock_account_input_categ_id.id,
				'price_unit':line.price_unit,
				'od_po_return_line_id':line.id,
			}
			invoice_line_ids.append((0,0,invoice_line_vals))
		if invoice_line_ids:
			invoice_vals = {
				'move_type':'in_refund',
				'partner_id':self.partner_id.id,
				'invoice_origin':self.name,
				'invoice_line_ids':invoice_line_ids,
			}
			invoice_id = self.env['account.move'].create(invoice_vals)
			invoice_id.action_post()
			self.invoice_id = invoice_id.id

			for line in self.line_ids:
				invoice_line_id = invoice_id.invoice_line_ids.filtered(lambda x:x.od_po_return_line_id.id==line.id).mapped('id')
				if invoice_line_id:
					line.invoice_line_id = invoice_line_id[0]

		self.state='debit_note'

	def button_complete(self):
		self.state='complete'

	@api.model
	def create(self, vals):
		vals['name'] = self.env['ir.sequence'].next_by_code('od.purchase.return')
		return super(OdPurchaseReturn, self).create(vals)

class OdPurchaseReturnLine(models.Model):
	_name = "od.purchase.return.line"
	_inherit = "analytic.mixin"
	_description="Purchase Return Lines"

	return_id = fields.Many2one('od.purchase.return', string="Enquiry", ondelete="cascade", copy=False)
	company_id = fields.Many2one('res.company', string="Company", related="return_id.company_id")
	product_id  = fields.Many2one('product.product', string="Product", tracking=True)
	quantity  = fields.Float(string="Quantity", tracking=True)
	price_unit  = fields.Float(string="Unit Price(Euro)", tracking=True)
	stock_move_id = fields.Many2one('stock.move', string='Stock Move', copy=False)
	invoice_line_id = fields.Many2one('account.move.line', string='Bill Line', copy=False)
	stock_move_price_unit = fields.Float(string="Unit Price(SAR)", tracking=True, copy=False)


	@api.onchange('product_id')
	def get_cost(self):
		for line in self:
			cost = 0
			if line.product_id:
				cost = line.product_id.od_cost_price
			line.price_unit =cost

class StockMove(models.Model):
	_inherit = "stock.move"

	od_po_return_line_id = fields.Many2one('od.purchase.return.line', string="Purchase Return Line")