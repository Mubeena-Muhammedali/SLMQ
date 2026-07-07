# -*- coding: utf-8 -*-

from odoo import models, fields, api,_

class OdInterCompanyTransfer(models.Model):
	_name = 'od.intercompany.transfer'
	_inherit = ['mail.thread']
	_description = "Inter Company Transfers"

	name = fields.Char(string='Name', copy=False, tracking=True)
	company_id = fields.Many2one('res.company', string="To Company", default=lambda self:self.env.company, tracking=True)
	from_company_id = fields.Many2one('res.company', string="From", tracking=True)
	state = fields.Selection([('Draft','Draft'),('Submitted','Submitted'),('Validated','Validated'),('Cancelled','Cancelled')], string="State", default='Draft', tracking=True)
	transfer_picking_ids = fields.Many2many('stock.picking', string="Transfer", compute="compute_transfer_ids", tracking=True)
	user_id = fields.Many2one('res.users', string="User", tracking=True)
	date = fields.Date(string="Date", default=fields.Date.today, tracking=True)
	remarks = fields.Text(string="Remarks")
	line_ids = fields.One2many('od.intercompany.transfer.line','transfer_id', string="Inter Company Lines")
	po_id = fields.Many2one('purchase.order', string="Purchase Order")

	def load_po_lines(self):
		if self.po_id:
			self.line_ids.unlink()
			lines = []
			for line in self.po_id.order_line.filtered(lambda x:x.product_id and x.qty_received):
				vals={
				'purchase_order_line_id':line.id,
				'product_id':line.product_id.id,
				'qty':line.product_uom_qty,
				'price_unit':line.price_unit,
				}
				lines.append((0,0,vals))
			self.line_ids = lines

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			vals['name'] = self.env['ir.sequence'].next_by_code('od.intercompany.transfer')
		return super(OdInterCompanyTransfer, self).create(vals_list)

	@api.depends('line_ids', 'line_ids.transfer_picking_id', 'line_ids.receive_picking_id')
	def compute_transfer_ids(self):
		for record in self:
			transfer_ids = record.line_ids.mapped('transfer_picking_id').ids
			receive_ids = record.line_ids.mapped('receive_picking_id').ids

			all_ids = list(set(transfer_ids + receive_ids))   # remove duplicates
			
			record.transfer_picking_ids = [(6, 0, all_ids)]

	def action_get_transfers(self):
		self.ensure_one()
		action_ref = self.env.ref('stock.action_picking_tree_incoming')
		if not action_ref:
			return False
		action_data = action_ref.read()[0]
		action_data['domain'] = [('id', 'in', self.transfer_picking_ids.ids)]
		action_data['context'] = {'create':0,'edit':0}
		return action_data
		

	def button_submit(self):
		self.line_ids.state='Submitted'
		self.state='Submitted'

	def button_draft(self):
		self.line_ids.state='Draft'
		self.state='Draft'

	def button_cancel(self):
		self.line_ids.state='Cancelled'
		self.state='Cancelled'

	def button_validate(self):
		self.line_ids.action_intercompany_transfer()
		if all(l.state=='Validated' for l in self.line_ids):
			self.state = 'Validated'


class OdInterCompanyTransferLine(models.Model):
	_name = "od.intercompany.transfer.line"
	_description = "Inter Company Transfer Line"

	transfer_id = fields.Many2one('od.intercompany.transfer', "Transfer", ondelete="cascade", copy=False)
	product_id = fields.Many2one('product.product', string="Product")
	qty = fields.Float(string="Qty", default=1)
	company_id = fields.Many2one('res.company', string="To Company", related="transfer_id.company_id", store=True)
	from_company_id = fields.Many2one('res.company', string="From", related="transfer_id.from_company_id", store=True)
	state = fields.Selection([('Draft','Draft'),('Submitted','Submitted'),('Validated','Validated'),('Cancelled','Cancelled')], string="State", default='Draft')
	transfer_picking_id = fields.Many2one('stock.picking', string="Outgoing Transfer")
	receive_picking_id = fields.Many2one('stock.picking', string="Incoming Transfer")
	purchase_order_line_id = fields.Many2one('purchase.order.line', string="Purchase Order Line")
	price_unit = fields.Float(string="Unit Price")

	@api.onchange('product_id','from_company_id')
	def onchange_pdt(self):
		for line in self:
			if line.product_id and line.sudo().from_company_id:
				product = line.product_id.with_context(
					company_id=line.sudo().from_company_id.id,
					allowed_company_ids=[line.sudo().from_company_id.id],
				)
				line.price_unit = product.standard_price


	def action_intercompany_transfer(self):
		"""Creates and validates intercompany stock transfers between companies"""
		StockPicking = self.env['stock.picking'].sudo()
		StockMove = self.env['stock.move'].sudo()

		for rec in self:
			if not rec.from_company_id or not rec.company_id:
				raise UserError(_("Please specify both source and destination companies."))

			if rec.from_company_id == rec.company_id:
				raise UserError(_("Source and destination companies must be different."))

			# --- Get warehouses ---
			from_wh = self.env['stock.warehouse'].sudo().search([('company_id', '=', rec.from_company_id.id)], limit=1)
			to_wh = self.env['stock.warehouse'].sudo().search([('company_id', '=', rec.company_id.id)], limit=1)

			if not from_wh or not to_wh:
				raise UserError(_("Please configure warehouses for both companies."))

			# --- Get operation types ---
			outgoing_type = self.env['stock.picking.type'].sudo().search([
				('warehouse_id', '=', from_wh.id),
				('code', '=', 'outgoing')
			], limit=1)

			incoming_type = self.env['stock.picking.type'].sudo().search([
				('warehouse_id', '=', to_wh.id),
				('code', '=', 'incoming')
			], limit=1)

			if not outgoing_type or not incoming_type:
				raise UserError(_("Please configure Incoming/Outgoing operation types."))

			# --- Create outgoing picking ---
			out_picking_vals = {
				'partner_id': rec.company_id.partner_id.id,
				'company_id': rec.from_company_id.id,
				'picking_type_id': outgoing_type.id,
				'location_id': outgoing_type.default_location_src_id.id,
				'location_dest_id': outgoing_type.default_location_dest_id.id or rec.company_id.partner_id.property_stock_customer.id,
				'origin': f"Intercompany Transfer to {rec.company_id.name}",
			}
			out_picking = StockPicking.create(out_picking_vals)

			StockMove.create({
				'name': rec.product_id.display_name,
				'picking_id': out_picking.id,
				'product_id': rec.product_id.id,
				'product_uom': rec.product_id.uom_id.id,
				'product_uom_qty': rec.qty,
				'quantity': rec.qty,
				'location_id': out_picking.location_id.id,
				'location_dest_id': out_picking.location_dest_id.id,
				'company_id': rec.from_company_id.id,
				'price_unit':rec.price_unit,
			})

			out_picking.action_confirm()
			out_picking.action_assign()

			# --- Force validate outgoing picking ---
			for move_line in out_picking.move_line_ids:
				move_line.quantity = rec.qty
			# If no move lines yet (possible in Odoo), fill from moves
			if not out_picking.move_line_ids:
				for move in out_picking.move_ids:
					move.quantity_done = move.product_uom_qty
			out_picking.button_validate()

			# --- Create incoming picking in receiving company ---
			in_picking_vals = {
				'partner_id': rec.from_company_id.partner_id.id,
				'company_id': rec.company_id.id,
				'picking_type_id': incoming_type.id,
				'location_id': incoming_type.default_location_src_id.id,
				'location_dest_id': incoming_type.default_location_dest_id.id,
				'origin': f"Intercompany Transfer from {rec.from_company_id.name}",
			}
			in_picking = StockPicking.create(in_picking_vals)

			StockMove.create({
				'name': rec.product_id.display_name,
				'picking_id': in_picking.id,
				'product_id': rec.product_id.id,
				'product_uom': rec.product_id.uom_id.id,
				'product_uom_qty': rec.qty,
				'quantity': rec.qty,
				'location_id': in_picking.location_id.id,
				'location_dest_id': in_picking.location_dest_id.id,
				'company_id': rec.company_id.id,
				'price_unit':rec.price_unit,
			})

			in_picking.action_confirm()
			in_picking.action_assign()

			# --- Force validate incoming picking ---
			for move_line in in_picking.move_line_ids:
				move_line.quantity = rec.qty
			if not in_picking.move_line_ids:
				for move in in_picking.move_ids:
					move.quantity_done = move.product_uom_qty
			in_picking.button_validate()

			# --- Link both pickings ---
			rec.transfer_picking_id = out_picking.id
			rec.receive_picking_id = in_picking.id
			rec.state = 'Validated'
	