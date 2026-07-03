 # -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime,timedelta
from odoo.exceptions import AccessError, UserError, ValidationError
from itertools import groupby
from odoo.tools import float_compare, date_utils, email_split, email_re

class OdPurchaseEnquiry(models.Model):
	_name = "od.purchase.enquiry"
	_inherit = ['mail.thread']
	_description="Purchase Enquiry"

	name=fields.Char(string="Name")
	date=fields.Date(string="Date", default=fields.Date.today, tracking=True)
	user_id=fields.Many2one('res.users', string="User", default=lambda self:self.env.user, tracking=True)
	partner_id=fields.Many2one('res.partner', string="Supplier", tracking=True)
	line_ids = fields.One2many('od.purchase.enquiry.line', 'enquiry_id', string="Lines")
	company_id = fields.Many2one('res.company', string="Company", default=lambda self:self.env.company)
	remaining_qty = fields.Float(string="Remaining Qty", compute="compute_remaining_qty", store=True, tracking=True)
	state = fields.Selection([('draft','Draft'),('order','Purchase Order')], string="state", default="draft")
	order_ids = fields.Many2many(comodel_name='purchase.order',string="Purchase Orders",compute='get_po_ids',copy=False)
	purchase_reference = fields.Char(string="Purchase Reference")
	
	@api.model
	def create(self, vals):
		vals['name'] = self.env['ir.sequence'].next_by_code('od.purchase.enquiry')
		return super(OdPurchaseEnquiry, self).create(vals)
		
	def action_create_po(self):
		print("hiiiiiiiiiiiiiiii", self._context)
		''' Open the od.create.po.wiz wizard tocreate po for selected enquiries.
		'''
		for record in self:
			if not record.remaining_qty:
				raise UserError(_("No qty to create PO for the enquiry '%s' ")%(record.name))
			if record.state !='order':
				raise UserError(_("The enqiry '%s' is not confirmed!!")%(record.name))
		return {
			'name': _('Create Purchase'),
			'res_model': 'od.create.po.wiz',
			'view_mode': 'form',
			'context': {
				'active_model': 'od.purchase.enquiry',
				'active_ids': self.ids,
			},
			'target': 'new',
			'type': 'ir.actions.act_window',
		}
	

	@api.depends('line_ids.remaining_qty')
	def compute_remaining_qty(self):
		for record in self:
			remaining_qty = 0
			remaining_qty = sum(record.line_ids.mapped('remaining_qty'))
			record.remaining_qty = remaining_qty

	@api.depends('line_ids.order_line_ids')
	def get_po_ids(self):
		for record in self:
			orders = record.line_ids.order_line_ids.order_id
			record.order_ids = orders

	def button_confirm(self):
		self.state="order"

	def button_reset(self):
		if self.order_ids:
			raise UserError(_("Orders have been already made from this enquiry!!!"))
		self.state="draft"


class OdPurchaseEnquiryLine(models.Model):
	_name = "od.purchase.enquiry.line"
	_inherit = "analytic.mixin"
	_description="Purchase Enquiry Lines"

	enquiry_id = fields.Many2one('od.purchase.enquiry', string="Enquiry", ondelete="cascade", copy=False)
	name =  fields.Char(string="Name")
	company_id = fields.Many2one('res.company', string="Company", related="enquiry_id.company_id")
	product_id  = fields.Many2one('product.product', string="Product", tracking=True)
	quantity  = fields.Float(string="Quantity", tracking=True)
	price_unit  = fields.Float(string="Unit Price", tracking=True)
	ordered_qty = fields.Float(string="Ordered Qty", tracking=True, compute="compute_remaining_qty", store=True)
	remaining_qty = fields.Float(string="Remaining Qty", compute="compute_remaining_qty", store=True, tracking=True)
	order_line_ids =fields.Many2many(comodel_name='purchase.order.line', relation='od_purchase_enquiry_line_po_line_rel', column1='enquiry_line_id', column2='po_line_id', string="PO Lines", copy=False)
	hs_code_id = fields.Many2one('orchid.product.hscode', related="product_id.orchid_hscode_id", string='HS Code')

	@api.depends('order_line_ids.product_qty','quantity')
	def compute_remaining_qty(self):
		for line in self:
			ordered_qty = 0
			remaining_qty = 0
			for po_line in line.order_line_ids:
				ordered_qty+=po_line.product_qty
			remaining_qty = line.quantity - ordered_qty
			line.ordered_qty =  ordered_qty
			line.remaining_qty =  remaining_qty

	@api.onchange('product_id')
	def get_cost(self):
		for line in self:
			cost = 0
			name = ""
			if line.product_id:
				cost = line.product_id.od_cost_price
				name = line.product_id.name
			line.price_unit =cost
			line.name =name


class PurchaseOrder(models.Model):
	_inherit = "purchase.order"

	enquiry_ids = fields.Many2many('od.purchase.enquiry',string="Purchase Enquiry",compute='od_get_enq_ids',copy=False)

	@api.depends('order_line.od_enquiry_line_ids')
	def od_get_enq_ids(self):
		for record in self:
			orders = record.order_line.od_enquiry_line_ids.enquiry_id
			record.enquiry_ids = orders

class PurchaseOrderLine(models.Model):
	_inherit = "purchase.order.line"

	od_enquiry_line_ids =fields.Many2many('od.purchase.enquiry.line','od_purchase_enquiry_line_po_line_rel','po_line_id','enquiry_line_id', string="Enquiry Lines", copy=False)

	def write(self, vals):
		res = super(PurchaseOrderLine, self).write(vals)
		if 'product_qty' in vals:
			if self.od_enquiry_line_ids:
				for line in self.od_enquiry_line_ids:
					line.ordered_qty = self.product_qty
					line.compute_remaining_qty()
		return res

