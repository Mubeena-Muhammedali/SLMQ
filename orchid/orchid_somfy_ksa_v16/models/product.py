from odoo import api, fields, models, _
from odoo.exceptions import UserError



# class OrchidProductGroup(models.Model):
# 	_inherit = 'orchid.product.group'
# 	arab_name = fields.Char(string='Arabic Name',required=True)

class OrchidProductCategory(models.Model):
	_inherit = 'product.category'
	_order = "od_sale_qty desc"
   
	od_code = fields.Char(string='Code',required=True) 
	od_sale_qty = fields.Integer(string="Sold Qty")

	def od_get_sale_qty(self):
		od_sale_qty = 0
		qry = """SELECT 
					COALESCE((SUM(sl.product_uom_qty)+SUM(sl.od_free_qty)+SUM(sl.od_adjustment_qty)),0)
					FROM sale_order_line sl
					LEFT JOIN product_product pp ON pp.id=sl.product_id
					LEFT JOIN product_template tmpl ON tmpl.id=pp.product_tmpl_id
					LEFT JOIN sale_order so ON so.id=sl.order_id 
					WHERE tmpl.categ_id=%s AND so.state in ('sale','done')"""%(self.id)
		# print(qry)
		self._cr.execute(qry)
		qty=self._cr.fetchall()
		qty=[q[0] for q in qty]
		if qty:
			od_sale_qty = qty[0]
		self.od_sale_qty = od_sale_qty


# Modification in Inventory Product
class ProducTemplate(models.Model):
	_inherit = 'product.template' 

	od_com_code = fields.Char(string='Commodity Code')
	od_mult_qty = fields.Float(string='Multiple Quantity')
	od_pcs_box = fields.Float(string='Pcs/Box')
	od_depth = fields.Float(string='Depth(mm)')
	od_width = fields.Float(string='Width(mm)')
	od_height = fields.Float(string='Height(mm)')
	od_weight = fields.Float(string='Weight(kg)')
	od_pkg_weight = fields.Float(string='Packaging Weight')
	od_ttl_weight = fields.Float(string='Total Weight')
	od_pcs_pallet = fields.Float(string='Pcs/Pallet')
	od_box_layer = fields.Float(string='Nb box/Layer')
	od_layer = fields.Float(string='Nb of Layers')
	od_box_pallet = fields.Float(string='Nb Boxes/ pallet')
	od_max_pallet_ht = fields.Float(string='Pallet Max Height(mm)')
	od_cbm_vol = fields.Float(string='CBM',digits=(12, 12))
	od_factory_cost = fields.Float(string="Factory Cost")

	orchid_brand_id =  fields.Many2one('orchid.product.brand', string='Brand')
	orchid_type_id =  fields.Many2one('orchid.product.type', string='Type')
	orchid_sub_type_id =  fields.Many2one('orchid.product.sub.type', string='Sub Type')
	orchid_group_id =  fields.Many2one('orchid.product.group', string='Group')
	orchid_sub_group_id =  fields.Many2one('orchid.product.sub.group', string='Sub Group')
	orchid_class_id =  fields.Many2one('orchid.product.classification', string='Classification')
	orchid_country_id = fields.Many2one('res.country', string='Country Of Origin')
	orchid_hscode_id = fields.Many2one('orchid.product.hscode', string='HS Code')
	orchid_arabic = fields.Char(string='Arabic Name')
	od_sale_price =fields.Float(string="Sales Price")
	od_cost_price =fields.Float(string="Cost Price Euro")
	od_readonly = fields.Boolean(string="Readonly", default=False)
	od_product_segment_id = fields.Many2many('od.product.segment', string="Product Segment", tracking=True)
	

	def od_get_euro_cost(self):
		for pdt in self:
			cost_euro = 0
			domain = ['&', ('state', 'in', ['purchase', 'done']), ('product_id', 'in', pdt.product_variant_ids.ids)]
			po_line_id = self.env['purchase.order.line'].search(domain, order='id desc',limit=1)
			if po_line_id:
				cost_euro = po_line_id.price_unit
			pdt.od_cost_price = cost_euro
			
	@api.onchange('od_sale_price')
	def od_onchange_sale_price(self):
		for pt in self:
			# print("herrrrrrrrrrrproducttttttttttttttttt************************")
			pt.list_price = pt.od_sale_price

	@api.onchange('orchid_group_id')
	def od_onchange_group(self):
		for pt in self:
			print("herrrrrrrrrrrproducttttttttttttttttt************************")
			if pt.orchid_group_id:
				pt.property_account_income_id = pt.orchid_group_id.pdt_grp_account_income_id and pt.orchid_group_id.pdt_grp_account_income_id.id or False
				pt.property_account_expense_id = pt.orchid_group_id.pdt_grp_account_expense_id and pt.orchid_group_id.pdt_grp_account_expense_id.id or False
			else:
				pt.property_account_income_id = False
				pt.property_account_expense_id = False
	# @api.model_create_multi
	# def create(self, vals_list):
	# 	for vals in vals_list:
	# 		# print("valsss",vals)
	# 		if not vals['property_account_income_id']:
	# 			raise UserError(_("Please set the Income Account to continue!!"))
	# 		if not vals['property_account_expense_id']:
	# 			raise UserError(_("Please set the Expense Account to continue!!"))
	# 	return super(ProducTemplate, self).create(vals_list)
	
	
class ProductProduct(models.Model):
	_inherit = "product.product"

	#to pass costcenter to movelines from vendorbill
	@api.model
	def _convert_prepared_anglosaxon_line(self, line, partner):
		res = super(ProductProduct,self)._convert_prepared_anglosaxon_line(line, partner)
		if 'orchid_cc_id' in line:
			res['orchid_cc_id'] = line['orchid_cc_id']
		return res



