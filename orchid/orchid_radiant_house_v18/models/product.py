# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
	_inherit = "product.template"

	@api.model_create_multi
	def create(self, vals_list):
		for vals in vals_list:
			if vals.get('od_product_type') == 'finished_product':
				if not vals.get('od_proof_request_id'):
					raise UserError(_("Finished Products should be created from proof request!!"))
		return super(ProductTemplate, self).create(vals_list)

	@api.onchange('od_die_id')
	def onchange_die_id(self):
		for product in self:
			length = product.od_die_id and product.od_die_id.od_length_of_label or 0.0
			width = product.od_die_id and product.od_die_id.od_width_of_label or 0.0
			product.od_length = length
			product.od_width = width

	@api.onchange('od_mat_id')
	def onchange_mat_id(self):
		for product in self:
			mat_id = product.od_mat_id
			if mat_id:
				liner = mat_id.od_raw_liner3 and mat_id.od_raw_liner3.id or False
				product.od_liner3 = liner
				micron = mat_id.od_raw_thickness
				product.od_micron = micron
				face_stock_type = mat_id.od_face_stock_type2 and mat_id.od_face_stock_type2.id
				product.od_face2 = face_stock_type
				micron2 =mat_id.od_raw_liner_thickness
				product.od_micron2 = micron2

	# def od_action_open_proof_request(self):
	# 	tmpl_id = self.id
	# 	products = self.env['product.product'].search([('product_tmpl_id','=',tmpl_id)])
	# 	product_ids =[prod.id for prod in products]
	# 	domain = []
	# 	context = self._context
	# 	ctx = {}
	# 	if product_ids:
	# 		proof_req = self.env['od.proof.request'].search([('product_id','in',product_ids)])
	# 		proof_req_ids = [pr.id for pr in proof_req]
	# 		domain.append(('id','in',proof_req_ids))
	# 		ctx.update({'default_product_id':product_ids[0]})
	# 		return {
	# 			'domain': domain,
	# 			'view_type': 'form',
	# 			'view_mode': 'tree,form',
	# 			'res_model': 'od.proof.request',
	# 			'type': 'ir.actions.act_window',
	# 			'context':ctx
	# 		}

	# def compute_proof_request_count(self):
	# 	res ={}

	# 	for obj in self:
	# 		tmpl_id = obj.id
	# 		products = self.env['product.product'].search([('product_tmpl_id','=',tmpl_id)])
	# 		product_ids =[prod.id for prod in products]
	# 		# print "product_ids",product_ids
	# 		if product_ids:
	# 			proof_req = self.env['od.proof.request'].search([('product_id','in',product_ids)])
	# 			# print "proofffffffffffffffffffffffff req",proof_req
	# 			self.od_proof_req_count = len(proof_req)
	# 		else:
	# 			self.od_proof_req_count = 0

	# @api.model_create_multi
	# def create(self, vals_list):
	# 	partner_pool = self.env['res.partner']
	# 	for vals in vals_list:
	# 		if vals.get('od_product_type') == 'finished_product':
	# 			partner_id = vals.get('od_customer_id')
	# 			partner_obj=partner_pool.browse(partner_id)
	# 			product_seq = partner_obj.od_product_seq_no or 0
	# 			if product_seq == 0:
	# 				product_seq += 1
	# 			customer_code =partner_obj.od_customer_code or ''
	# 			code = customer_code + '/'+ str(product_seq).zfill(5)
	# 			vals['default_code'] = code
	# 			partner_obj.write({'od_product_seq_no':product_seq+1})
	# 		elif vals.get('od_product_type') == 'raw_material':
	# 			partner_id = vals.get('od_supplier_id')
	# 			partner_obj=partner_pool.browse(partner_id)
	# 			product_seq = partner_obj.od_product_seq_no or 0
	# 			if product_seq == 0:
	# 				product_seq += 1
	# 			customer_code =partner_obj.od_customer_code or ''
	# 			code = customer_code + '/'+ str(product_seq).zfill(5)
	# 			vals['default_code'] = code
	# 			partner_obj.write({'od_product_seq_no':product_seq+1})
	# 		elif vals.get('od_product_type') == 'diecut':
	# 			vals['default_code'] = self.env['ir.sequence'].get('od.die.cut') or '/'
	# 		elif vals.get('od_product_type') == 'plate':
	# 			vals['default_code'] = self.env['ir.sequence'].get('od.plate') or '/'
		# return super(ProductTemplate, self).create( vals_list)

	od_proof_req_count = fields.Integer(string="Proof Requests", compute="compute_proof_request_count")
	od_product_type = fields.Selection([('finished_product', 'Finished Product'),('raw_material', 'Raw Material'),('diecut', 'Diecut'),('plate','Plate'),('consumable','Consumable')], string='Internal Type', required=True, tracking=True)
	od_customer_id = fields.Many2one('res.partner', string='Customer', domain=[('customer_rank','>',0)], tracking=True)
	od_supplier_id = fields.Many2one('res.partner', string='Supplier', domain=[('supplier_rank','>',0)], tracking=True)
	od_application = fields.Selection([('machine', 'Machine'),('manual', 'Manual'),], string='Application', tracking=True)
	od_wdg_direction = fields.Char('WDG Direction Front', tracking=True)
	od_wdg_direction_back = fields.Char('WDG Direction Back', tracking=True)
	od_continouse_print = fields.Boolean(string='Continuous print', tracking=True)
	od_application_temp = fields.Float(string='Application Temp', tracking=True)
	od_adhesive = fields.Selection(
				[('permenant', 'Permenant'),('removable', 'Removable'),('freezing', 'Freezing'),('hot_melt', 'Hot Melt'),('acrylic', 'Acrylic'),('na','NA')],
				string='Adhesive', tracking=True)
	od_print_finishing = fields.Selection(
				[('uv-varnish-glossy', 'UV Varnish Glossy'),('uv_varnish-matt', 'UV Varnish Matt'),
				# ('laminated', 'Laminated'),
				('spot_varnish', 'Spot+Matt Varnish'),('others','Others')],
				string='Print Finishing', tracking=True)
	# od_sec_printing = fields.Selection(
	# 			[('ttr', 'TTR'),('dt', 'DT'),('dot_matrix', 'Dot Matrix'),('inkjet','Inkjet'),('na','NA')],
	# 			string='Sec Printing', tracking=True)

	od_sec_printing = fields.Text(string='Sec Printing', tracking=True)
	
	od_color_matching_ref = fields.Selection(
				[('printed_sample', 'Printed Sample'),('digital_proof', 'Digital Proof'),('previous_printed', 'Previous Printed'),('panton_no','Panton No'),('repeat','Repeat')],
				string='Color Matching Ref', tracking=True)
	od_printing_sude = fields.Selection([
		('front', 'Front'),
		('back', 'Back'),
		('both', 'Front & Back'),
		('Front Double Layer', 'Front Double Layer'),
		('Back Double Layer', 'Back Double Layer'),
		('Top Label', 'Top Label')
	], string='Printing Side', tracking=True)
	od_pms_no = fields.Char(string='PMS No', tracking=True)
	od_speacial_req = fields.Selection(
				[('perforation', 'Perforation'),('under_scoring', 'Under Scoring'),('previous_printed', 'Pin Feed Holes'),('spot_varnish','Spot Varnish'),('Kiss Cut', 'Kiss Cut'),
				('Glue Side Printing', 'Glue Side Printing'),
				('LFW', 'LFW'),
				('Fan-Folding', 'Fan-Folding'),('na','NA')],
				string='Special Req', tracking=True)
	color_dom = [('0','0'),('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),('8', '8'),('9', '9'),('10', '10')]

	od_no_of_colors = fields.Integer(string="No of Colors", tracking=True)
	od_no_of_colors_1 = fields.Selection(color_dom, string="No.Of Colors", tracking=True)

	od_type_of_printing = fields.Selection(
				[('surface', 'Surface'),('reverse', 'Reverse'),],
				string='Type Of Printing', tracking=True)

	od_type_of_primer = fields.Selection(
				[('full', 'Full'),('spot', 'Spot'),],
				string='Type Of Primer', tracking=True)
	od_art_ref_no = fields.Char(string='Artwork Ref No', tracking=True)
	od_art_work_code = fields.Char(string='Artwork Code', tracking=True)

	od_conv_format = fields.Selection(
				[('roll', 'Roll'),('pieces', 'Pieces'),],
				string='Conv Format', tracking=True)
	od_core = fields.Selection(
				[('25', '25'),('40', '40'),('50', '50'),('76', '76'),('120', '120'),('152', '152'),],
				'Core')
	od_die_id = fields.Many2one('product.product', string='Die', domain=[('od_product_type','=','diecut')], tracking=True)
	od_raw_material_id = fields.Many2one('product.product', string="Raw Material", domain=[('od_product_type','=','raw_material')], tracking=True)
	od_storage_temp = fields.Float(string='Storage Temp', tracking=True)
	od_prod_to_be_filled = fields.Char(string='Prod To Be Filled', tracking=True)
	od_container_type = fields.Char('Container Type', tracking=True)
	od_width = fields.Float(string='Width(mm)', tracking=True)
	od_length = fields.Float(string='Length/Height(mm)', tracking=True)
	od_printing_process = fields.Selection([('flexo','Flexo'),
											('digital', 'Digital'),
											('ribbon', 'Ribbon'),
											('stretch', 'Stretch'),
											('ribbon', 'Ribbon'),
											('tape', 'Tape'),
											], tracking=True)
	od_digital_ink = fields.Selection([('ink1','INK1'),('ink2','INK2')], tracking=True)
	od_screen = fields.Boolean(string='Screen', tracking=True)
	od_hot_foil = fields.Boolean(string='Hot Foil', tracking=True)
	od_cold_foil = fields.Boolean(string='Gold Foil', tracking=True)
	od_pcs_roll =fields.Integer(string='PCS/Roll or Pack', tracking=True)
	od_pack_roll =fields.Integer(string='Packs/Roll', tracking=True)
	od_of_roll = fields.Char(string='OD of Roll', tracking=True)
	od_cartons = fields.Char(string='Cartons/Pallet', tracking=True)
	od_pallet_spec = fields.Char(string='Pallet Spec', tracking=True)
	od_note_spec = fields.Text(string='Note', tracking=True)
#     die specification
	od_die_type = fields.Selection([('flexible','Flexible'),('flat_bed_die','Flat Bed Die')], string='Die Type', tracking=True)
	od_material = fields.Selection([('adhesive', 'Self-Adhesive Labels')], string="Material", tracking=True)
	od_material2  = fields.Many2one('od.die.material', string="Material Type", tracking=True)
	od_mat_id = fields.Many2one('product.product', string="Material", tracking=True)
	od_face = fields.Selection([('pp','PP'),('pe','PE'),('coated_paper','Coated Paper'),('tml','TML/TTR'),('others','Others')], string="Face", tracking=True)
	od_face2 = fields.Many2one('od.raw.face.stock.type', string="Face", tracking=True)
	od_gsm = fields.Integer(string='GSM', tracking=True)
	od_micron = fields.Char(string='Micron', tracking=True)
	od_micron2 = fields.Char(string='Micron', tracking=True)
	od_liner = fields.Selection([('glassine','Glassine')], string="Liner", tracking=True)
	od_liner3 = fields.Many2one('od.liner', string="Liner", tracking=True)
	od_gsm2 = fields.Integer(string='GSM', tracking=True)
	od_width_of_label = fields.Float(string='Width Of The Label(mm)', tracking=True)
	od_length_of_label = fields.Float(string='Length Of The Label(mm)', tracking=True)
	od_cylinder_teeth = fields.Float(string='Cylinder Teeth', tracking=True)
	od_cylinder_teeth_1 = fields.Many2one('od.cylinder.teeth', string="Cylinder Teeth", tracking=True)
	od_machine = fields.Char(string='Machine', tracking=True)
	od_machine2 = fields.Many2one('od.die.machine', string="Machine", tracking=True)
	od_repeat_in_mm = fields.Float(string='Repeat in MM', tracking=True)
	od_radius_corner = fields.Char(string='Radius Corner', tracking=True)
	od_material_width = fields.Float(string='Material Width', tracking=True)
	od_ups_across = fields.Float(string='Ups Across', tracking=True)
	od_ups_around = fields.Float(string='Ups Around', tracking=True)
	od_gap_across = fields.Float(string='Gap Across', tracking=True)
	od_gap_around = fields.Float(string='Gap Around', tracking=True)
	od_shape = fields.Selection([('special','Special'),('rect','Rectangular'),('square','Square'),('oval','Oval'),('round','Round')],string='Shape', tracking=True)
	od_shape_id = fields.Many2one('od.product.shape',string='Shape', tracking=True)
	od_cutting = fields.Selection([('cut','Kiss-Cut'),('tcut','Cut Through')],string="Cutting", tracking=True)
#Raw material Specification
	od_face_stock = fields.Selection([('white','White'),('transparent','Transparent'),('silver','Silver'),('mat','Matt-Trans')], string="Face Stock", tracking=True)
	od_face_stock2 = fields.Many2one('od.raw.face.stock','Face Stock', tracking=True)
	od_face_stock_type = fields.Selection([('pp','PP'),('pvc','PVC'),('paper','Paper'),('pe','PE')], string="Face Stock Type", tracking=True)
	od_face_stock_type2 = fields.Many2one('od.raw.face.stock.type', string='Face Stock Type', tracking=True)
	od_adhesive_raw = fields.Selection([('permanant','Permanant'),('removable','Removable')], string='Adhesive', tracking=True)
	od_adhesive_raw2 = fields.Many2one('od.raw.adhesive', string='Adhesive', tracking=True)
	od_adhesive_thick =fields.Float(string='Thickness', tracking=True)
	od_raw_thickness = fields.Float(string='Thickness', tracking=True)
	od_raw_liner = fields.Selection([('white','Gassline White'),('yellow',' Gassline Yellow'),('pet','PET')], string='Liner', tracking=True)
	od_raw_liner3 = fields.Many2one('od.liner', string='Liner', tracking=True)
	od_raw_liner_thickness = fields.Float('Thickness', tracking=True)
	od_raw_width = fields.Float(string='Width', tracking=True)
	#python expression to eval
	od_auto = fields.Boolean(string='Auto', tracking=True)
	od_eval_code = fields.Text(string="Expression", tracking=True)
	od_timebase = fields.Boolean(string="Time Based", tracking=True)
	od_default = fields.Boolean(string="Default", tracking=True)
	od_only_in_firstproduction = fields.Boolean(string="Only in First Production", tracking=True)    
	od_machine_pp = fields.Boolean(string="Is a Machine", tracking=True)
	od_avg_conversion_rate = fields.Float(string="Average Conversion rate", default=1, tracking=True)
	od_overhead_pdts = fields.One2many('od.over.head.product','machine_id', string="Overhead Components", tracking=True)

	# others
	orchid_brand_id =  fields.Many2one('orchid.product.brand', string='Brand', tracking=True)
	orchid_type_id =  fields.Many2one('orchid.product.type', string='Type', tracking=True)
	orchid_sub_type_id =  fields.Many2one('orchid.product.sub.type', string='Sub Type', tracking=True)
	orchid_group_id =  fields.Many2one('orchid.product.group', string='Group', tracking=True)
	orchid_sub_group_id =  fields.Many2one('orchid.product.sub.group', string='Sub Group', tracking=True)
	orchid_class_id =  fields.Many2one('orchid.product.classification', string='Classification', tracking=True)
	od_production_uom_id =fields.Many2one('uom.uom', string="Production Uom", tracking=True)

	od_cold_foil_light = fields.Boolean(string="Gold Foil Light", tracking=True)
	od_holographic_foil = fields.Boolean(string="Holographic Foil", tracking=True)
	od_silver_foil = fields.Boolean(string="Silver Foil", tracking=True)
	od_glossy_lamination = fields.Boolean(string="Glossy Lamination", tracking=True)
	od_matt_lamination = fields.Boolean(string="Matt Lamination", tracking=True)
	od_embossing = fields.Selection([('On Time', 'Online'), ('Off Time', 'Offline')], string="Embossing", tracking=True)

	od_delivery_date = fields.Date(string="Delivery Date", tracking=True)
	od_job_no = fields.Date(string="Job Card No", tracking=True)
	od_user_id = fields.Many2one('res.users', string="Salesman", tracking=True)
	od_plain = fields.Char(string="Plain", tracking=True)
	od_printed = fields.Char(string="Printed", tracking=True)
	od_micron = fields.Char(string="Micron", tracking=True)
	od_yards = fields.Char(string="Yards", tracking=True)
	od_rolls = fields.Char(string="Rolls", tracking=True)
	od_inch = fields.Char(string="Inch", tracking=True)
	od_box = fields.Char(string="Box", tracking=True)
	od_plastic = fields.Char(string="Plastic", tracking=True)
	od_inkout = fields.Char(string="Ink Out", tracking=True)
	od_inkin = fields.Char(string="Ink In", tracking=True)
	od_lbw = fields.Float(string='LBW', tracking=True)
	od_speacial_req_id = fields.Many2many('od.special.request', string="Special Req")
	od_product_segment = fields.Selection([
        ('self_adhesive', 'Self Adhesive'),
        ('wrap_around', 'Wrap Around'),
        ('shrink_sleeve', 'Shrink Sleeve'),
        ('alu_lids', 'Alu Lids'),
        ('plain', 'Plain'),
        ('printed', 'Printed'),
        ('tape', 'Tape'),
        ('stretched_film', 'Stretched Film'),
        ('ribbon', 'Ribbon'),
        ('others', 'Others'),
        ('trading', 'Trading'),
    ], string='Product Segment', tracking=True)
	od_proof_request_id = fields.Many2one('od.proof.request', string="Prroof Request", help="Product created from")



	def od_update_proof_request(self, vals={}):
		update_vals = [
			'od_wdg_direction','od_wdg_direction_back','od_application','od_continouse_print','od_application_temp','od_adhesive',
			'od_print_finishing','od_sec_printing','od_color_matching_ref',
			'od_printing_sude','od_pms_no','od_speacial_req','od_no_of_colors','od_type_of_printing',
			'od_type_of_primer','od_art_ref_no','od_art_work_code','od_conv_format','od_core','od_die_id',
			'od_raw_material_id','od_storage_temp','od_prod_to_be_filled','od_container_type','od_width',
			'od_length','od_printing_process','od_digital_ink','od_screen','od_hot_foil','od_cold_foil',
			'od_cold_foil_light','od_silver_foil','od_glossy_lamination','od_matt_lamination',  
			'od_pcs_roll','od_pack_roll','od_of_roll','od_cartons','od_pallet_spec','od_note_spec','od_holographic_foil','od_embossing'
			]

		
		tmpl_id = self.id
		products = self.env['product.product'].search([('product_tmpl_id','=',tmpl_id)])
		product_ids =[prod.id for prod in products]
		if product_ids:
			proof_req_ids = self.env['od.proof.request'].search([('product_id','in',product_ids)])
		for up in update_vals:
			for proof_req_id in proof_req_ids:
				proof_req_id.write({up:self.read()[0][up]})