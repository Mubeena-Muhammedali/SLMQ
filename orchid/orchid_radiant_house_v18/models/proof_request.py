# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError


class ODProofRequest(models.Model):
    _name = 'od.proof.request'
    _description = 'Proof Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =======================
    # BASIC FIELDS
    # =======================
    name = fields.Char(string='Name', required=True, default='/', tracking=True, copy=False)
    date = fields.Date(string='Date', default=fields.Date.today, required=True, readonly=True, tracking=True)
    submission_date = fields.Date(string='Submission Date', default=fields.Date.today, tracking=True)
    partner_id = fields.Many2one('res.partner', string="Client", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', tracking=True)

    customer = fields.Boolean(string="Client")
    product_id = fields.Many2one('product.product', string="Product", readonly=True, copy=False, tracking=True)
    product_name = fields.Char('Product Name', copy=False, tracking=True)
    product_segment = fields.Selection([
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
    ], string='Product Segment', default='self_adhesive', tracking=True)

    raw_mat_id = fields.Many2one('product.product', string="Raw Material", copy=False, tracking=True)
    die_type_id = fields.Many2one('od.die.type.master', string="Die Type", tracking=True)

    od_bom_count = fields.Integer(string="BoM Count", compute="_compute_count")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting'),
        ('approved', 'Approved'),
    ], string='Status', default='draft', tracking=True)

    # =======================
    # SPECIFICATION FIELDS
    # =======================
    od_application = fields.Selection([('machine', 'Machine'), ('manual', 'Manual')], string='Application', tracking=True)
    od_wdg_direction = fields.Char('WDG Direction Front', tracking=True)
    od_wdg_direction_back = fields.Char('WDG Direction Back', tracking=True)
    od_continouse_print = fields.Boolean(string='Continuous Print', tracking=True)
    od_application_temp = fields.Float(string='Front Qty', tracking=True)
    od_adhesive = fields.Selection([
        ('permenant', 'Permanent'),
        ('removable', 'Removable'),
        ('freezing', 'Freezing'),
        ('hot_melt', 'Hot Melt'),
        ('acrylic', 'Acrylic'),
        ('na', 'NA'),
    ], string='Adhesive', tracking=True)


    od_print_finishing = fields.Selection([
        ('uv-varnish-glossy', 'UV Varnish Glossy'),
        ('uv_varnish-matt', 'UV Varnish Matt'),
        # ('laminated', 'Laminated'),
        ('spot_varnish', 'Spot+Matt Varnish'),
        ('others', 'Others')
    ], string='Print Finishing', tracking=True)

    # od_sec_printing = fields.Selection([
    #     ('ttr', 'TTR'),
    #     ('dt', 'DT'),
    #     ('dot_matrix', 'Dot Matrix'),
    #     ('inkjet', 'Inkjet'),
    #     ('na', 'NA')
    # ], string='Sec Printing', tracking=True)

    od_sec_printing = fields.Text(string='Sec Printing', tracking=True)

    od_color_matching_ref = fields.Selection([
        ('printed_sample', 'Printed Sample'),
        ('digital_proof', 'Digital Proof'),
        ('previous_printed', 'Previous Printed'),
        ('panton_no', 'Pantone No'),('repeat','Repeat')
    ], string='Color Matching Ref', tracking=True)

    od_printing_sude = fields.Selection([
        ('front', 'Front'),
        ('back', 'Back'),
        ('both', 'Front & Back'),
        ('Front Double Layer', 'Front Double Layer'),
        ('Back Double Layer', 'Back Double Layer'),
        ('Top Label', 'Top Label')
    ], string='Printing Side', tracking=True)

    od_pms_no = fields.Char(string='PMS No', tracking=True)
    od_speacial_req = fields.Selection([
        ('perforation', 'Perforation'),
        ('under_scoring', 'Under Scoring'),
        ('previous_printed', 'Pin Feed Holes'),
        ('spot_varnish', 'Spot Varnish'),
        ('Kiss Cut', 'Kiss Cut'),
        ('Glue Side Printing', 'Glue Side Printing'),
        ('LFW', 'LFW'),
        ('Fan-Folding', 'Fan-Folding'),
        ('na', 'NA')
    ], string='Special Req', tracking=True)

    od_speacial_req_id = fields.Many2many('od.special.request', string="Special Req")

    od_no_of_colors = fields.Integer(string='No. of Colors', tracking=True)
    od_type_of_printing = fields.Selection([('surface', 'Surface'), ('reverse', 'Reverse')], string='Type of Printing', tracking=True)
    od_type_of_primer = fields.Selection([('full', 'Full'), ('spot', 'Spot')], string='Type of Primer', tracking=True)
    od_art_ref_no = fields.Char(string='Artwork Ref No', tracking=True)
    od_art_work_code = fields.Char(string='Artwork Code', tracking=True)
    od_conv_format = fields.Selection([('roll', 'Roll'), ('pieces', 'Pieces')], string='Conv Format', tracking=True)
    od_core = fields.Selection([
        ('25', '25'), ('40', '40'), ('50', '50'), ('76', '76'), ('120', '120'), ('152', '152')
    ], string='Core', tracking=True)

    od_die_id = fields.Many2one('product.product', string='Die', tracking=True)
    od_raw_material_id = fields.Many2one('product.product', string='Raw Material', tracking=True)
    od_note_spec = fields.Text(string='Notes', tracking=True)
    od_storage_temp = fields.Float(string='Back Qty', tracking=True)
    od_lbw = fields.Float(string='LBW', tracking=True)
    od_prod_to_be_filled = fields.Char(string='Prod To Be Filled', tracking=True)
    od_container_type = fields.Char(string='Container Type', tracking=True)
    od_width = fields.Float(string='Width (mm)', tracking=True)
    od_length = fields.Float(string='Length/Height (mm)', tracking=True)
    od_printing_process = fields.Selection([('flexo', 'Flexo'),
                                            ('digital', 'Digital'),
                                            ('ribbon', 'Ribbon'),
                                            ('stretch', 'Stretch'),
                                            ('ribbon', 'Ribbon'),
                                            ('tape', 'Tape'),
                                            ], string="Printing Process", tracking=True)
    od_digital_ink = fields.Selection([('ink1', 'INK1'), ('ink2', 'INK2')], string="Digital Ink", tracking=True)
    od_embossing = fields.Selection([('On Time', 'Online'), ('Off Time', 'Offline')], string="Embossing", tracking=True)
    od_screen = fields.Boolean(string='Screen', tracking=True)
    od_hot_foil = fields.Boolean(string='Hot Foil', tracking=True)
    od_cold_foil = fields.Boolean(string='Gold Foil', tracking=True)
    od_pcs_roll = fields.Integer(string='PCS/Roll or Pack', tracking=True)
    od_pack_roll = fields.Integer(string='Packs/Roll', tracking=True)
    od_of_roll = fields.Char(string='OD of Roll', tracking=True)
    od_cartons = fields.Char(string='Cartons/Pallet', tracking=True)
    od_pallet_spec = fields.Char(string='Pallet Spec', tracking=True)

    od_cold_foil_light = fields.Boolean("Gold Foil Light", tracking=True)
    od_silver_foil = fields.Boolean("Silver Foil", tracking=True)
    od_holographic_foil = fields.Boolean(string="Holographic Foil", tracking=True)
    od_glossy_lamination = fields.Boolean("Glossy Lamination", tracking=True)
    od_matt_lamination = fields.Boolean("Matt Lamination", tracking=True)

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
    od_sale_line_id = fields.Many2one('sale.order.line', string="Sale Order Line")

    od_die_ups_across = fields.Float(string='Ups Across', tracking=True)
    od_die_ups_around = fields.Float(string='Ups Around', tracking=True)
    od_die_gap_across = fields.Float(string='Gap Across', tracking=True)
    od_die_gap_around = fields.Float(string='Gap Around', tracking=True)
    od_cylinder_teeth_1 = fields.Many2one('od.cylinder.teeth', string="Cylinder Teeth", tracking=True)
    uom_id = fields.Many2one('uom.uom', string="Product Uom", tracking=True)

    @api.onchange('od_die_id')
    def od_onchange_die(self):
        for p in self:
            if p.od_die_id:
                p.od_die_ups_across = p.od_die_id.od_ups_across
                p.od_die_ups_around = p.od_die_id.od_ups_around
                p.od_die_gap_across = p.od_die_id.od_gap_across
                p.od_die_gap_around = p.od_die_id.od_gap_around
                p.od_cylinder_teeth_1 = p.od_die_id.od_cylinder_teeth_1.id
            else:
                p.od_die_ups_across = 0
                p.od_die_ups_around = 0
                p.od_die_gap_across = 0
                p.od_die_gap_around = 0
                p.od_cylinder_teeth_1 = False


    # =======================
    # BUSINESS LOGIC
    # =======================

    def unlink(self):
        if any(record.state != 'draft' for record in self):
            raise UserError("You can only delete draft proof requests.")
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('od.proof.request') or '/'
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        self.update_product(vals)
        return res

    def update_product(self, vals={}):
        if not self._context.get('no_create_pdt'):
            fields_to_sync = [
                'od_application', 'od_continouse_print', 'od_application_temp', 'od_adhesive',
                'od_print_finishing', 'od_sec_printing', 'od_color_matching_ref', 'od_printing_sude',
                'od_pms_no', 'od_speacial_req', 'od_no_of_colors', 'od_type_of_printing',
                'od_type_of_primer', 'od_art_ref_no', 'od_art_work_code', 'od_conv_format',
                'od_core', 'od_die_id', 'od_raw_material_id', 'od_storage_temp', 'od_prod_to_be_filled',
                'od_container_type', 'od_width', 'od_length', 'od_printing_process', 'od_digital_ink',
                'od_screen', 'od_hot_foil', 'od_cold_foil', 'od_pcs_roll', 'od_pack_roll', 'od_of_roll',
                'od_cartons', 'od_pallet_spec', 'od_note_spec', 'od_wdg_direction','od_wdg_direction_back',
                'od_cold_foil_light', 'od_silver_foil', 'od_glossy_lamination', 'od_matt_lamination','od_holographic_foil','od_embossing','uom_id'
            ]

            for field in fields_to_sync:
                if field in vals:
                    self.product_id.write({field: vals[field]})
                elif not vals:
                    self.product_id.write({field: self[field]})
                self.product_id.write({
                    'default_code':self.od_art_work_code,
                    'od_wdg_direction':self.od_wdg_direction,
                    'od_wdg_direction_back':self.od_wdg_direction_back,
                    'od_no_of_colors':self.od_no_of_colors,
                    'od_delivery_date':self.od_delivery_date,
                    'od_job_no':self.od_job_no,
                    'od_user_id':self.od_user_id,
                    'od_yards':self.od_yards,
                    'od_inch':self.od_inch,
                    'od_rolls':self.od_rolls,
                    'od_box':self.od_box,
                    'od_plastic':self.od_plastic,
                    'od_printed':self.od_printed,
                    'od_plain':self.od_plain,
                    'od_inkin':self.od_inkin,
                    'od_inkout':self.od_inkout,
                    'od_lbw':self.od_lbw,
                    'od_speacial_req_id':[(6,0,self.od_speacial_req_id.ids)],
                    'uom_id':self.uom_id and self.uom_id.id,
                    'uom_po_id':self.uom_id and self.uom_id.id,
                    'od_product_segment':self.product_segment,
                    })


    def is_field_empty(self, check_fields):
        for field_val, field_label in check_fields.items():
            if self.product_segment not in ('tape','stretched_film','ribbon'):
                if not field_val:
                    raise UserError(f"The field '{field_label}' is empty. Please fill it.")

    def check_list_field(self):
        self.is_field_empty({
            self.date: 'Date',
            self.product_id: 'Product',
            self.partner_id: "Client",
            self.submission_date: 'Submission Date',
            self.product_segment: 'Product Segment',
            # self.od_art_ref_no: 'Artwork Ref No',
            self.od_art_work_code: 'Artwork Code'
        })

    def btn_confirm(self):
        if not self.product_id:
            raise UserError("Need a Product to Confirm.")
        self.write({'state': 'waiting'})

    def btn_approve(self):
        self.check_list_field()
        self.write({'state': 'approved'})

    def btn_reset(self):
        self.write({'state': 'draft'})

    def _compute_count(self):
        for rec in self:
            bom_ids = self.env['mrp.bom'].search([('product_id', '=', rec.product_id.id)])
            rec.od_bom_count = len(bom_ids)

    def od_view_bom(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'BoM',
            'view_mode': 'tree,form',
            'res_model': 'mrp.bom',
            'domain': [('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)],
            'context': {
                'default_product_tmpl_id': self.product_id.product_tmpl_id.id,
                'default_product_id': self.product_id.id
            }
        }

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for rec in self:
            rec.customer = rec.partner_id.customer_rank > 0 if rec.partner_id else False

    @api.onchange('raw_mat_id')
    def onchange_raw_mat_id(self):
        for rec in self:
            rec.od_raw_material_id = rec.raw_mat_id.id if rec.raw_mat_id else False

    def od_create_po(self):
        self = self.sudo()
        if not self.raw_mat_id:
            raise UserError("Please choose a Raw Material.")

        product = self.env['product.product']
        parameter_obj = self.env['ir.config_parameter']
        product_categ = self.env.ref('orchid_radiant_house_v18.od_product_categ_param')

        if (not product_categ) or (product_categ and not(int(product_categ.value))):
            raise UserError(_('System Parameter "product_categ" not set.'))

        route_id = self.env.ref('mrp.route_warehouse0_manufacture').id

        # vals = product.default_get(['uom_id', 'uom_po_id'])
        # vals.update({
        vals = {
            'name': self.product_name,
            'od_customer_id': self.partner_id.id,
            'od_product_type': 'finished_product',
            'od_raw_material_id': self.raw_mat_id.id,
            'type': 'consu',
            'cost_method': 'real',
            'valuation': 'real_time',
            'route_ids': [(6, 0, [route_id])],
            'categ_id': int(product_categ.value),
            'is_storable':True,
            'uom_id':self.uom_id and self.uom_id.id,
            'uom_po_id':self.uom_id and self.uom_id.id,
            'od_proof_request_id':self.id,
        }

        self.product_id = product.create(vals).id
        self.product_id.od_proof_request_id = self.id
        self.update_product()
        return True
