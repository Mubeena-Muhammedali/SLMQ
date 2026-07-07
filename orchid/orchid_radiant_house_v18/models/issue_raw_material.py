from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidIssueRawMaterials(models.Model):
	_name = 'orchid.issue.raw.materials'
	_description = "Issue Raw Materials"

	name = fields.Char(string="Name", readonly=True, copy=False)
	mo_id = fields.Many2one('mrp.production', string="MO",readonly=True, copy=False)
	product_id = fields.Many2one('product.product', string="Product", readonly=True)
	raw_material_line = fields.One2many('orchid.issue.raw.material.lines','issue_raw_material_id', string="Raw Material Lines", copy=False)
	state = fields.Selection([('draft','Draft'),('confirm','Materials Issued'),('receive','Materials Received')], default='draft', string="State", readonly=True)

	def unlink(self):
		if self.state != 'draft':
			raise UserError("You Can Only Delete Draft Raw Material Request")
		return super(OrchidIssueRawMaterials,self).unlink()

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			vals['name'] = self.env['ir.sequence'].next_by_code('orchid.issue.raw.materials')
		return super(OrchidIssueRawMaterials, self).create(vals_list)

	def confirm_issue_qty(self):
		for line in self.raw_material_line:
			line.mo_raw_material_line_id.od_issued = line.issued
			line.mo_raw_material_line_id.od_compute_consumed_sqm()
		self.mo_id.od_material_issued = True
		self.write({'state':'confirm'})

	def receive_materials(self):
		self.write({'state':'receive'})

class OrchidIssueRawMaterialLines(models.Model):
	_name = "orchid.issue.raw.material.lines"
	_description = "Issue Raw Material Lines"

	issue_raw_material_id = fields.Many2one('orchid.issue.raw.materials', string="MO",readonly=True, copy=False)
	mo_raw_material_line_id = fields.Many2one('stock.move', string="MO Raw Material Line",readonly=True, copy=False)
	product_id = fields.Many2one('product.product',string="Product",required=True,readonly=True)
	product_uom = fields.Many2one('uom.uom',string="Uom(Base)",related="product_id.uom_id",readonly=True,store=True,required=False)
	product_uom2 = fields.Many2one('uom.uom',string="Uom",required=True,readonly=True)
	planned = fields.Float(string="Planned",readonly=True)
	issued = fields.Float(string="Issued")
	returned = fields.Float(string="Returned", readonly=True)

class MrpProduction(models.Model):
	_inherit = "mrp.production"

	od_issue_material_id = fields.Many2one('orchid.issue.raw.materials', string="Issue Materials",readonly=True, copy=False)
	od_material_issued = fields.Boolean(string="Raw Materials Issued", copy=False)
	
	def action_confirm(self):
		for production in self:
			production.od_check_qty()
			if any(line.od_issued==0 for line in production.move_raw_ids):
				raise UserError(_("Raw material issued is zero!!!!!"))
			# for raw in production.move_raw_ids:
				# if not raw.product_id.categ_id.id in (3,5):
			if not production.od_material_issued:
				raise UserError("Issue Raw Materials to confirm the production.")
			res = super(MrpProduction,production).action_confirm()
			return res

	def button_mark_done(self):
		"""Override mark done to handle cost calculations"""
		for production in self:
			# Validate issued quantity
			if any(line.od_issued==0 for line in production.move_raw_ids):
				raise UserError(_("Raw material issued is zero!!!!!"))
			# Call super method
			res = super(MrpProduction, production).button_mark_done()
		return res

	def od_check_qty(self):
		if not self.move_raw_ids:
			raise UserError("Raw Materials are not set!!!")
		for line in self.move_raw_ids:
			if not (line.product_id.with_context(location_id=line.location_id.id).qty_available>0):
				raise UserError(_("No enough stock for Raw Material '%s' !!!")%(line.product_id.display_name))
			base_qty = line.product_uom._compute_quantity(line.should_consume_qty, line.product_id.uom_id, rounding_method='HALF-UP')
			# print("baaa",base_qty,line.product_id.qty_available,line.product_id.with_context(location_id=line.location_id.id).qty_available)
			if base_qty > line.product_id.with_context(location_id=line.location_id.id).qty_available:
				raise UserError(_("No enough stock for Raw Material'%s' !!!")%(line.product_id.display_name))

	def od_issue_materials(self):
		self.od_check_qty()
		if self.od_issue_material_id:
			raise UserError("A Request to issue raw materials has already been made.")
		issue_material_vals ={
		'mo_id':self.id,
		'product_id':self.product_id.id,
		}
		issue_id = self.env['orchid.issue.raw.materials'].create(issue_material_vals)
		self.od_issue_material_id = issue_id.id
		for line in self.move_raw_ids:
			line_vals = {
			'issue_raw_material_id':issue_id.id,
			'mo_raw_material_line_id':line.id,
			'product_id':line.product_id.id,
			'product_uom2':line.product_uom.id,
			'product_uom':line.od_product_uom and line.od_product_uom.id or False,
			'planned':line.product_uom_qty,
			}
			issue_line_id = self.env['orchid.issue.raw.material.lines'].create(line_vals)
			line.od_issue_raw_material_line_id = issue_line_id.id
		

class StockMove(models.Model):
	_inherit = "stock.move"

	od_issued = fields.Float(string="Issued", copy=False)
	od_issue_raw_material_line_id = fields.Many2one('orchid.issue.raw.material.lines', string="Issue Material Line",readonly=True, copy=False)
	od_returned = fields.Float(string="Returned", compute="od_compute_consumed_sqm")

	@api.depends('quantity', 'product_uom', 'od_product_uom')
	def od_compute_consumed_sqm(self):
		for raw in self:
			print("rrrr",raw)
			res = super(StockMove, self).od_compute_consumed_sqm()
			raw.od_returned = raw.od_issued - raw.quantity
			if raw.od_issue_raw_material_line_id:
				raw.od_issue_raw_material_line_id.returned = raw.od_returned
		return res

