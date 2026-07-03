from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError

class OdcreatePOWiz(models.TransientModel):
	_name = 'od.create.po.wiz'
	_description = 'Create Purchase from Enquiry'

	enquiry_ids = fields.Many2many('od.purchase.enquiry', string="Enquiry")
	purchase_id = fields.Many2one('purchase.order', string="Purchase Order")
	order_line = fields.Many2one('purchase.order.line', string="Purchase Order Line")
	operation_type = fields.Selection([('create','Create new PO'),('edit','Edit PO')], default="create", string="Operation Type")
	line_ids = fields.One2many('od.create.po.wiz.line', 'wiz_id', string="Lines")

	@api.model
	def default_get(self, fields):
		res = super(OdcreatePOWiz, self).default_get(fields)
		res['enquiry_ids']= [Command.set(self._context.get('active_ids'))]
		return res

	def load_enquiry_lines(self):
		for record in self:
			line_ls = []
			record.line_ids.unlink()
			line_ids = record.enquiry_ids.mapped('line_ids').filtered(lambda x:x.remaining_qty)
			for line in line_ids:
				print("lineeeee",line)
				line_vals={
				'wiz_id':record.id,
				'enquiry_line_id':line.id,
				'enquiry_id':line.enquiry_id.id,
				'product_id':line.product_id.id,
				'name':line.name,
				'remaining_qty':line.remaining_qty,
				'price_unit':line.price_unit,
				'quantity':line.remaining_qty,
				}
				line_ls.append((0,0,line_vals))
			print("llll",line_ls)
			record.line_ids = line_ls

			
			return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.create.po.wiz',
			  'res_id': record.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }

	# def load_po_lines(self):
	# 	for record in self:
	# 		line_ls = []
	# 		record.line_ids.unlink()
	# 		for line_id in po.order_line:
	# 			line_vals={
	# 			'enquiry_line_id':line.od_enquiry_line_ids[0].id if line.od_enquiry_line_ids[0] else False,
	# 			'po_line_id':line.id,
	# 			'product_id':line.product_id.id,
	# 			'name':line.name,
	# 			# 'remaining_qty':line.remaining_qty,
	# 			'price_unit':line.price_unit,
	# 			'quantity':line.product_qty,
	# 			}
	# 			line_ls.append((0,0,line_vals))
	# 		record.line_ids = line_ls


	def create_po(self):
		for record in self:
			po_vals = {
			'partner_id':record.enquiry_ids[0].partner_id.id,
			'date_order':fields.Date.today(),
			# 'origin':record.name,
			# 'od_enquiry_ids':[Command.set(record.enquiry_ids.ids)],
			'od_non_inventroy':False,
			'od_non_trade_inventory':False,
			}
			print("pooo",po_vals)
			line_ls = []
			for line in record.line_ids:
				print("jjj",line.enquiry_line_id)
				line_vals={
				'od_enquiry_line_ids':[Command.link(line.enquiry_line_id.id)],
				'product_id':line.product_id.id,
				'name':line.name or line.product_id.name,
				'price_unit':line.price_unit,
				'product_qty':line.quantity,
				}
				line_ls.append((0,0,line_vals))
			po_vals['order_line'] = line_ls
			po_id = record.env['purchase.order'].create(po_vals)
			return {
			'res_model':'purchase.order',
			'view_mode':'form',
			'res_id':po_id.id,
			}

	@api.onchange('operation_type')
	def onchange_operation_type(self):
		for record in self:
			if record.operation_type == 'create':
				record.line_ids.unlink()
			if record.operation_type == 'edit':
				record.line_ids.unlink()



class OdcreatePOWizLine(models.TransientModel):
	_name = "od.create.po.wiz.line"

	wiz_id = fields.Many2one('od.create.po.wiz', string="wizard", ondelete="cascade", copy=False)
	enquiry_line_id = fields.Many2one('od.purchase.enquiry.line', string="Enquiry Line")
	enquiry_id = fields.Many2one('od.purchase.enquiry', string="Enquiry")
	name =  fields.Char(string="Name")
	company_id = fields.Many2one('res.company', string="Company", related="enquiry_id.company_id")
	product_id  = fields.Many2one('product.product', string="Product")
	quantity  = fields.Float(string="Quantity")
	price_unit  = fields.Float(string="Unit Price")
	remaining_qty = fields.Float(string="Remaining Qty")
	# po_line_id = fields.Many2one('purchase.order.line', string="Po Line")