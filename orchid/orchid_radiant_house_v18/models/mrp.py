# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # ========== Field Definitions ==========
    # Sales Related Fields
    od_sale_order_line_id = fields.Many2one('sale.order.line', string="Sale Line")
    # od_actual_qty = fields.Float(string="SO Qty", readonly=True)
    od_price_unit = fields.Float(string="Unit Price", readonly=True, digits=(16, 3))
    # od_opening_qty = fields.Float(string="Opening Qty", readonly=True)
    
    # Production Type Flags
    od_new_die = fields.Boolean(string="New Online Die")
    od_new_order = fields.Boolean(string="New Job")
    od_new_plate = fields.Boolean(string="New Plate")
    od_repeat_job = fields.Boolean(string="Repeat Job")
    od_existing_die = fields.Boolean(string="Existing Die", copy=False)
    od_flat_bed_die = fields.Boolean(string="New Flatbed Die", copy=False)
    od_old_flat_bed_die = fields.Boolean(string="Old Flatbed Die", copy=False)
    od_online_die = fields.Boolean(string="Old Online Die", copy=False)
    od_repeat_correction = fields.Boolean(string="Repeat+Correction", copy=False)
    od_plate_manufacturing = fields.Boolean(string="Plate Manufacturing")
    
    # Time Tracking Fields
    od_start = fields.Datetime(string="Start Time")
    od_stop = fields.Datetime(string="End Time")
    od_ideal = fields.Float(string="Ideal Time")
    od_machine_extra_minute = fields.Float(string="Machine Default Time (min.)", default=5)
    od_digital = fields.Boolean(string="Digital")
    
    # Production Details
    od_production_start_date = fields.Date(string="Production Start date")
    od_consumedbalance = fields.Boolean(string="Consumed Balance Rawmaterial")
    od_at_least_produced_once = fields.Boolean(string="Atleast Produced Once", copy=False)
    od_validity_date = fields.Date(string="Delivery Date")
    od_remarks = fields.Text(string="Remarks")
    od_analytic_id = fields.Many2one('account.analytic.account', string="Analytic", readonly=True)
    
    # Material Calculation Fields (Computed)
    od_good_mtr = fields.Float(string="Good Meter", compute='_compute_material_calculations', store=True)
    od_make_ready_waste = fields.Float(string="Make Ready Waste", compute="_compute_material_calculations", store=True)
    od_process_waste = fields.Float(string="Process Waste", compute="_compute_material_calculations", store=True)
    od_misc_waste = fields.Float(string="Miscellaneous Waste", compute="_compute_material_calculations", store=True)
    od_total_reqd_mtr = fields.Float(string="Total Required Meter", compute="_compute_material_calculations", store=True)
    od_printing_time = fields.Float(string="Printing Time", compute="_compute_material_calculations", store=True)
    od_make_ready_time = fields.Float(string="Make Ready Time", compute="_compute_material_calculations", store=True)
    od_cleaning_time = fields.Float(string="Cleaning Time", compute="_compute_material_calculations", store=True)
    od_total_time = fields.Float(string="Total Time", compute="_compute_material_calculations", store=True)
    
    # Machine Time Fields (Computed)
    od_machine_minute = fields.Float(string="Machine Time (min.)", compute="_compute_machine_time", store=True)
    od_machine_hrs = fields.Float(string="Machine Time (hrs.)", compute="_compute_machine_time", store=True)
    od_hours = fields.Float(string="Consumed Time (hrs.)", compute="_compute_consumed_time", store=True)
    
    # Costing Fields
    od_overhead_manual = fields.Float(string="Overhead(Manual)", readonly=True)
    od_overhead_auto = fields.Float(string="Overhead(Auto)", readonly=True)
    od_overhead_total = fields.Float(string="Overhead Total", compute="_compute_overhead_total")
    od_per_unit_cost = fields.Float(string="Per Unit Cost", compute="_compute_per_unit_cost")
    # od_cylinder = fields.Many2one('od.cylinder.teeth', related='product_id.od_die_id.od_cylinder_teeth_1', string='Cylinder')
    od_cylinder = fields.Many2one('od.cylinder.teeth', string='Cylinder')
    od_landed_cost_ids = fields.Many2many('stock.landed.cost', string="Landed Costs")
    od_raw_material_cost = fields.Float(string="Raw Material Cost")
    od_costing_computed = fields.Boolean(string="Costing Computed", default=False)
    
    # Relational Fields
    od_overhead_line = fields.One2many('od.mrp.overhead.line', 'mrp_id', string="Overhead", copy=False)
    cost_sheet_lines_oh = fields.One2many('od.mrp.cost.sheet.lines', 'production_id', 
                                         domain=[('product_type', '=', 'overhead')], string="Overhead Costing Lines")
    cost_sheet_lines_rm = fields.One2many('od.mrp.cost.sheet.lines', 'production_id', 
                                         domain=[('product_type', '=', 'raw')], string="RM Costing Lines")
    cost_sheet_lines_fp = fields.One2many('od.mrp.cost.sheet.lines', 'production_id', 
                                         domain=[('product_type', '=', 'finished')], string="FP Costing Lines")
    od_mrp_id = fields.Many2one('mrp.production', string="Repeat Job")
    od_customer_uom_id = fields.Many2one('uom.uom', string="Customer UOM")
    od_customer_order = fields.Float(string="Customer Order")
    od_intercompany_transfer_ids = fields.One2many('od.mrp.intercompany.line','mrp_id', string="Inter Company Lines")

    
    # ==========Plate Mrp Field Definitions ==========
    od_plate_manufacturing = fields.Boolean(
        string="Is Plate Manufacturing Order", 
        default=False
    )
    
    od_machine_id = fields.Many2one(
        'product.product', 
        string="Machine",
        default=lambda self: self._get_plate_machine()
    )

    od_date_finished = fields.Date(string="Done Date")
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
    ], string='Product Segment', related='product_id.od_product_segment', store=True)

    od_partner_id = fields.Many2one(
        'res.partner', 
        string="Customer",
        related="od_sale_order_line_id.order_partner_id", store=True
    )

    od_salesman_id = fields.Many2one(
        'res.users', 
        string="Salesman",
        related="od_sale_order_line_id.salesman_id", store=True
    )

    
    # ========== Compute Methods ==========
    @api.depends('product_id', 'product_qty')
    def _compute_material_calculations(self):
        """Compute material requirements and time calculations based on product specifications"""
        for production in self:
            # Initialize default values
            production.update({
                'od_good_mtr': 0.0,
                'od_make_ready_waste': 0.0,
                'od_process_waste': 0.0,
                'od_misc_waste': 0.0,
                'od_total_reqd_mtr': 0.0,
                'od_printing_time': 0.0,
                'od_make_ready_time': 0.0,
                'od_cleaning_time': 0.0,
                'od_total_time': 0.0
            })

            if not production.product_id:
                continue

            try:
                # Configuration parameters
                printing_speed_param = self.env['ir.config_parameter'].get_param('od_printing_speed_mtr_hr')
                printing_speed_param = int(printing_speed_param)
                printing_speed = float(printing_speed_param) if printing_speed_param else 1.0
                
                no_of_color = int(production.product_id.od_no_of_colors_1 or 0)

                # Calculate waste and time
                make_ready_waste = no_of_color * 80
                production.od_make_ready_waste = make_ready_waste

                # Calculate material requirements
                if not production.od_plate_manufacturing:
                    die = production.product_id.od_die_id
                    ups_across = die.od_ups_across or 1
                    gap_around = die.od_gap_around or 0
                    length = production.product_id.od_length or 0
                    if production.od_sale_order_line_id.od_proof_request_ids:
                        die = production.od_sale_order_line_id.od_proof_request_ids.od_die_id
                        ups_across = production.od_sale_order_line_id.od_proof_request_ids.od_die_ups_across or 1
                        gap_around = production.od_sale_order_line_id.od_proof_request_ids.od_die_gap_around or 0
                    elif production.product_id.od_proof_request_id:
                        die = production.product_id.od_proof_request_id.od_die_id
                        ups_across = production.product_id.od_proof_request_id.od_die_ups_across or 1
                        gap_around = production.product_id.od_proof_request_id.od_die_gap_around or 0
                    # if not die:
                    #     raise UserError(_("Die not configured for product %s") % production.product_id.name)
                    
                    # ups_across = die.od_ups_across or 1
                    # gap_around = die.od_gap_around or 0
                    length = production.product_id.od_length or 0
                    
                    good_mtr = ((length + gap_around) * production.product_qty) / ups_across
                    good_mtr /= 1000
                else:
                    good_mtr = 0.0

                # Calculate time components
                make_ready_time = 20 * no_of_color
                cleaning_time = 10 * no_of_color
                process_waste = (good_mtr * 50) / 2000
                misc_waste = good_mtr * 0.025
                total_reqd_mtr = good_mtr + make_ready_waste + process_waste + misc_waste
                printing_time = (total_reqd_mtr / printing_speed) * 60

                # Update production values
                production.update({
                    'od_good_mtr': good_mtr,
                    'od_process_waste': process_waste,
                    'od_misc_waste': misc_waste,
                    'od_total_reqd_mtr': total_reqd_mtr,
                    'od_printing_time': printing_time,
                    'od_make_ready_time': make_ready_time,
                    'od_cleaning_time': cleaning_time,
                    'od_total_time': printing_time + make_ready_time + cleaning_time
                })
            except (ValueError, ZeroDivisionError) as e:
                _logger.error("Error computing material calculations: %s", e)
                raise UserError(_("Error in material calculations. Please check product configuration."))

    @api.depends('od_start', 'od_stop')
    def _compute_machine_time(self):
        """Calculate machine time from start and stop datetime"""
        for production in self:
            if production.od_start and production.od_stop and production.od_stop > production.od_start:
                delta = production.od_stop - production.od_start
                total_minutes = delta.total_seconds() // 60
                working_minutes = min(total_minutes, 9 * 60)  # Cap at 9 hours
                production.od_machine_hrs = working_minutes // 60
                production.od_machine_minute = working_minutes % 60
            else:
                production.od_machine_hrs = 0
                production.od_machine_minute = 0

    @api.depends('od_machine_minute', 'od_machine_hrs', 'od_digital', 'od_machine_extra_minute')
    def _compute_consumed_time(self):
        """Compute total consumed time including extra minutes for digital machines"""
        for production in self:
            if production.od_digital:
                production.od_hours = production.od_machine_hrs + (
                    (production.od_machine_minute + production.od_machine_extra_minute) / 60
                )
            else:
                production.od_hours = production.od_machine_hrs + (production.od_machine_minute / 60)

    @api.depends('od_overhead_manual', 'od_overhead_auto')
    def _compute_overhead_total(self):
        """Compute total overhead cost"""
        for production in self:
            production.od_overhead_total = production.od_overhead_manual + production.od_overhead_auto

    @api.depends('od_overhead_total', 'product_qty')
    def _compute_per_unit_cost(self):
        """Compute per unit cost"""
        for production in self:
            if production.product_qty:
                production.od_per_unit_cost = production.od_overhead_total / production.product_qty
            else:
                production.od_per_unit_cost = 0

    def _compute_button_visibility(self):
        """Compute visibility of update quantity button"""
        for production in self:
            # Add your specific logic here
            production.od_update_qty_visibility = production.state == 'draft'

    # ========== Constraint Methods ==========
    @api.constrains('od_sale_order_line_id', 'od_plate_manufacturing')
    def _check_manufacturing_source(self):
        """Ensure MO is created from sale orders when applicable"""
        for production in self:
            if not production.od_sale_order_line_id and not production.od_plate_manufacturing:
                raise ValidationError(_("MO's can be created from sale orders only!!!"))

    @api.constrains('od_new_die', 'od_new_plate', 'od_repeat_job', 'od_existing_die','od_new_order')
    def _check_required_checks(self):
        """Validate at least one production type is selected"""
        for production in self:
            if not any([production.od_new_die, production.od_new_plate, 
                        production.od_repeat_job, production.od_existing_die, production.od_new_order]):
                raise ValidationError(_("At least one of New Die, New Plate, Repeat Job, New Order must be checked"))

    # ========== Onchange Methods ==========

    @api.onchange('od_mrp_id')
    def onchange_od_mrp_id(self):
        for mrp in self:
            mrp_id =mrp.od_mrp_id
            raw_material_lines = []
            for line in mrp_id.move_raw_ids:
                vals = {'location_dest_id':line.location_dest_id and line.location_dest_id.id,'name':line.name,'product_id':line.product_id.id,'product_uom':line.product_uom and line.product_uom.id or False,'product_uom_qty':line.product_uom_qty}
                raw_material_lines.append((0,0,vals))
            mrp.move_raw_ids.unlink()
            mrp.move_raw_ids = raw_material_lines

    # @api.onchange('od_new_die', 'od_new_plate', 'od_repeat_job')
    # def _onchange_production_type(self):
    #     """Handle mutual exclusivity between production types"""
    #     for mrp in self:
    #         if mrp.od_repeat_job:
    #             mrp.od_new_die = False
    #             mrp.od_new_plate = False
    #         elif any([mrp.od_new_die, mrp.od_new_plate]):
    #             mrp.od_repeat_job = False

    # ========== CRUD Methods ==========
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set origin from sale order and validate manufacturing source"""
        for vals in vals_list:
            # Validate manufacturing source
            if 'od_sale_order_line_id' in vals and 'od_plate_manufacturing' in vals:
                if not vals.get('od_sale_order_line_id') and not vals.get('od_plate_manufacturing'):
                    raise UserError(_("MO's can be created from sale orders only!!!"))

            if vals.get('od_plate_manufacturing'):
                sequence_code = 'od.plate.production'
            else:
                sequence_code = 'mrp.production'
            
            # Get next sequence value
            sequence = self.env['ir.sequence'].next_by_code(sequence_code)
            if sequence:
                vals['name'] = sequence
        
        productions = super().create(vals_list)

        for production in productions:
            # Set origin from sale order if available
            if production.od_sale_order_line_id and not production.origin:
                production.origin = production.od_sale_order_line_id.order_id.name
            
        return productions

    def unlink(self):
        """Prevent deletion of confirmed productions"""
        if any(production.state != 'draft' for production in self):
            raise UserError(_("Cannot delete confirmed productions"))
        return super().unlink()

    # ========== Action Methods ==========
    def action_confirm(self):
        """Override confirm to add validations"""
        for production in self:
            # Validate required checks
            if not any([production.od_new_die, production.od_new_plate, 
                        production.od_repeat_job, production.od_existing_die]):
                raise UserError(_("At least one of New Die, New Plate, Repeat Job must be checked"))
            
            # Validate machine is set
            if not production.od_machine_id:
                raise UserError(_("Machine must be set"))
            
            # Validate time is set for non-plate manufacturing
            if not production.od_hours and not production.od_plate_manufacturing:
                raise UserError(_("Consumed time must be defined"))
            
            # Get default overhead products
            production.od_get_default_overhead_products()
            
        return super().action_confirm()

    def button_mark_done(self):
        """Override mark done to handle cost calculations"""
        for production in self:
            # Validate quantity
            production.od_check_qty()

            # for backordercases
            # Get default overhead products
            if not production.od_overhead_line:
                production.od_get_default_overhead_products()
            
            # Call super method
            res = super(MrpProduction, production).button_mark_done()
            
            # Calculate costs
            total_raw_material_cost = total_raw_material_qty = 0
            main_raw_material_cost = main_raw_material_qty = 0
            finished_pdt_qty_producing = production.qty_producing
            
            # Calculate material costs
            for raw_line in production.move_raw_ids:
                total_raw_material_cost += raw_line.price_unit * raw_line.od_consumed
                total_raw_material_qty += raw_line.od_consumed
                
                # Check for main material classification
                classification_id = self.env['ir.config_parameter'].get_param('orchid_class_id')
                if classification_id:
                    classification_id = int(classification_id)
                    pdt_classification_id = raw_line.product_id.orchid_class_id.id
                    if pdt_classification_id == classification_id:
                        main_raw_material_cost += raw_line.price_unit * raw_line.od_consumed
                        main_raw_material_qty += raw_line.od_consumed
            
            # Create accounting moves if needed
            if production.move_raw_ids and total_raw_material_qty != 0:
                production.od_create_move(
                    finished_pdt_qty_producing, 
                    total_raw_material_cost, 
                    total_raw_material_qty, 
                    main_raw_material_cost, 
                    main_raw_material_qty, 
                    production.product_qty
                )
            
            # Create landed costs if overhead lines exist
            if production.od_overhead_line:
                production.od_create_landed_cost(production)
             
            if production.state=='done':
                production.od_date_finished = fields.Date.today()  

                # update the produced qty in the pickings ,of the sale, that are not in done/cancel stages.
                sale_id = production.od_sale_order_line_id and production.od_sale_order_line_id.order_id
                if sale_id:
                    picking_ids = sale_id.picking_ids
                    picking_ids = picking_ids.filtered(lambda x:x.state not in ('done','cancel'))
                    if picking_ids:
                        move_ids = picking_ids.mapped('move_ids_without_package').filtered(lambda x:x.product_id.id==production.product_id.id)
                        if move_ids:
                            move_ids.write({'od_produced_qty':production.qty_produced})

            return res

    # def action_cancel(self):
    #     """Unlink the cancelled MO from sale order line"""
    #     # Remove from sale order line
    #     for production in self:
    #         if production.od_sale_order_line_id and production.id in production.od_sale_order_line_id.od_mrp_ids.ids:
    #             sale_mrp_ids = production.od_sale_order_line_id.od_mrp_ids.ids
    #             sale_mrp_ids.remove(production.id)
    #             production.od_sale_order_line_id.od_mrp_ids = [(6, 0, sale_mrp_ids)]
                
    #     return super().action_cancel()

    # ========== Business Methods ==========
    def od_action_view_account_moves(self):
        """Action to view account moves related to this manufacturing order"""
        self.ensure_one()
        stock_move_ids = self.move_raw_ids.ids+self.move_finished_ids.ids
        od_move_ids = self.env['account.move'].search(['|',('stock_move_id','in', stock_move_ids),('od_mrp_id', '=', self.id)]).ids
        
        # Add landed cost moves
        if self.od_landed_cost_ids:
            for landed_cost_id in self.od_landed_cost_ids:
                od_move_ids.append(landed_cost_id.account_move_id.id)
                
        # Prepare action
        action = {
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        
        if len(od_move_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': od_move_ids[0],
            })
        else:
            action.update({
                'name': _("Entries Generated by %s", self.name),
                'domain': [('id', 'in', od_move_ids)],
                'view_mode': 'list,form',
            })
            
        return action

    def od_get_default_overhead_products(self):
        """Configure default overhead products based on production parameters"""
        if self.od_overhead_line:
            self.od_overhead_line.unlink()
            
        overhead_lines = []
        consume_time = self.od_hours
        fproduct = self.product_id
        mach_pdt = self.od_machine_id
        need_ink = self.od_check_ink(fproduct)
        
        # Get default service products
        products = self.env['product.product'].search([
            ('type', '=', 'service'),
            ('od_default', '=', True)
        ])
        
        # Add ink product if needed
        if need_ink:
            # ink_pdt_id = self.get_id_from_param('od_ink_id')
            ink_pdt_id = self.company_id.od_ink_id
            
            if ink_pdt_id:
                # ink_pdt = self.env['product.product'].browse(int(ink_pdt_id))
                ink_pdt = ink_pdt_id
                ink_val = self.od_make_overhead_line(ink_pdt, consume_time)
                overhead_lines.append(ink_val)
        
        # Add machine product
        if mach_pdt:
            mach_val = self.od_make_overhead_line(mach_pdt, consume_time)
            overhead_lines.append(mach_val)
            
        # Add other default products
        for pdt in products:
            vals = self.od_make_overhead_line(pdt, consume_time)
            overhead_lines.append(vals)
            
        # Add machine-specific overhead products
        new_overhead_lines = []
        for ol in self.od_machine_id.od_overhead_pdts:
            mach_val = {
                'product_id': ol.product_id.id,
                'od_auto': ol.product_id.od_auto,
                'eval_code': ol.eval_code,
                'qty': 1 if self.od_plate_manufacturing else (consume_time if ol.product_id.od_timebase else 1),
                'uom_id':ol.uom_id.id,
            }
            new_overhead_lines.append((0, 0, mach_val))
            
        # Update overhead lines
        self.od_overhead_line = new_overhead_lines

    def od_make_overhead_line(self, product, consume_time):
        """Create an overhead line dictionary for the given product"""
        return {
            'product_id': product.id,
            'od_auto': product.od_auto,
            'qty': consume_time if product.od_timebase else 1
        }

    def od_check_ink(self, product):
        """Check if ink is needed based on product colors"""
        color = product.od_no_of_colors_1
        return bool(color and int(color) > 0)

    def get_id_from_param(self, param):
        """Get ID value from system parameter"""
        parameter_obj = self.env['ir.config_parameter']
        param_obj = parameter_obj.search([('key', '=', param)])
        
        if (not param_obj) or (not (int(param_obj.value)>1)):
            raise UserError(_('Settings Warning! Parameter %s not defined. Configure it in System Parameters.') % param)
            
        return param_obj.value

    def od_get_move_vals(self):
        date = fields.Date.context_today(self)
        ref = self.name
        # journal_id = self.env['ir.config_parameter'].search([('key','=','od_overhead_journal')]).value
        # journal_id = int(journal_id)
        # if (not journal_id) or (not (journal_id>1)):
        #     raise UserError(_("od_overhead_journal parameter is not set !!"))
        journal_id = self.company_id.od_overhead_journal_id and self.company_id.od_overhead_journal_id.id
        if not (journal_id):
            raise UserError(_("Please set Overhead Journal!!"))
        
        move_vals = {'date': date,'journal_id': journal_id,'ref':ref, 'move_type':'entry', 'od_mrp_id':self.id}
        return move_vals

    def od_get_account_move_lines(self,factor,material_cost,raw_material_cost,material_sqm,raw_material_qty):
        move_lines =[]
        debit_amount = 0.0
        cred_amount  = 0.0
        ref = self.name
        date = fields.Date.context_today(self)
        auto_total = manual_total = 0
        for line in self.od_overhead_line:
            move_line_vals = {'name': ref,'ref': ref,'date': date,'product_id':line.product_id and line.product_id.id}
            qty = line.qty
            mrp_obj = line.mrp_id
            product_id = line.product_id and line.product_id.id or False
            account_id = line.product_id.property_account_expense_id.id or line.product_id.categ_id.property_account_expense_categ_id.id
            # ink_product_id = self.env['ir.config_parameter'].search([('key','=','od_ink_id')]).value
            # ink_product_id = int(ink_product_id)
            # if (not ink_product_id) or (not (ink_product_id>1)):
            #     raise UserError("od_ink_id parameter is not set")
            ink_product_id = self.company_id.od_ink_id and self.company_id.od_ink_id.id
            if not (ink_product_id):
                raise UserError(_("Please set Ink Product!!"))
        
            if not account_id:
                raise UserError("Overhead Product %s Expense Account Not Set" %line.product_id.name)
            od_kg_uom_id = self.env['ir.config_parameter'].search([('key','=','od_kg_uom_id')]).value
            od_kg_uom_id = int(od_kg_uom_id)
            if (not od_kg_uom_id) or (not (od_kg_uom_id>1)):
                raise UserError("kg_weight_id parameter is not set")
            if line.od_auto:
                # eval_code = line.product_id and  line.product_id.od_eval_code
                eval_code = line.eval_code
                if not eval_code:
                    raise UserError("Product %s Overhead Eval Code Expression Not set" %line.product_id.name)
                
                kg_raw_qty = 0
                avg_conversion_rate = 1

                if product_id == ink_product_id:
                    for raw_line in self.move_raw_ids:
                        if raw_line.product_id.uom_id.id == od_kg_uom_id:
                            kg_raw_qty += raw_line.od_consumed
                            avg_conversion_rate = raw_line.product_id.od_avg_conversion_rate
                    if kg_raw_qty != 0:
                        material_sqm = kg_raw_qty
                cost = eval(eval_code)
                cred_amount = round((qty * cost),2)

            else:
                cred_amount = round((line.amount * factor),2)

            credit_amt = cred_amount
            if product_id == ink_product_id:
                if kg_raw_qty !=0:
                    cred_amount = round((credit_amt*avg_conversion_rate),2)

            if line.od_auto:
                auto_total += cred_amount
            else:
                manual_total += cred_amount

            if not mrp_obj.od_at_least_produced_once:
                vals = move_line_vals
                vals.update({'account_id':account_id,'credit':cred_amount,'debit':0.0,'product_id':product_id,'quantity': qty,'od_overhead_line_id':line.id})
                move_lines.append((0,0,vals))
                debit_amount += cred_amount
            else:
                vals = move_line_vals
                if not line.product_id.od_only_in_firstproduction:
                    vals.update({'account_id':account_id,'credit':cred_amount,'debit':0.0,'product_id':product_id,'quantity': qty,'od_overhead_line_id':line.id})
                    move_lines.append((0,0,vals))
                    debit_amount += cred_amount
        move_line_vals = {'name': ref,'ref': ref,'date': date}
        debit_lines = move_line_vals
        # acc_id = self.get_id_from_param('od_production_acc')
        # acc_id = int(acc_id)
        acc_id = self.company_id.od_production_acc_id and self.company_id.od_production_acc_id.id
        if not (acc_id):
            raise UserError(_("Please set Production Account!!"))
    
        move_line_length =len(move_lines) - 1
        cr_amount = 0.0
        if move_lines:
            for cr_index in range(move_line_length):
                cr_amount += move_lines[cr_index][2]['credit']
            credit_amount = round((debit_amount - cr_amount),2)
            move_lines[move_line_length][2]['credit'] = round(credit_amount,2)
            debit_lines.update({'account_id':acc_id,'debit':round(debit_amount,2),'credit':0.0})
            move_lines.append((0,0,debit_lines))
        self.write({'od_overhead_auto':auto_total,'od_overhead_manual':manual_total,'od_overhead_total':round(auto_total+manual_total)})
        return move_lines

    def od_create_move(self, finished_pdt_qty_producing, total_raw_material_cost, 
                      total_raw_material_qty, main_raw_material_cost, main_raw_material_qty, planned_qty):
        """Create accounting moves for production costs"""
        # Implementation details would go here
        producing_qty = finished_pdt_qty_producing
        raw_material_cost = total_raw_material_cost
        raw_material_qty = total_raw_material_qty
        material_cost = main_raw_material_cost
        material_sqm = main_raw_material_qty
        move_vals = self.od_get_move_vals()
        factor = producing_qty/planned_qty
        move_lines = self.od_get_account_move_lines(factor,material_cost,raw_material_cost,material_sqm,raw_material_qty)
        if move_lines and not self.od_at_least_produced_once:
            move_vals.update({'line_ids':move_lines})
            oh_debit = 0
            oh_credit = 0
            for line in move_vals['line_ids']:
                if line[2]['debit'] !=0:
                    oh_debit += line[2]['debit']
                    oh_debit_line = line
                if line[2]['credit'] !=0:
                    oh_credit += line[2]['credit']
            if oh_debit != oh_credit:
                oh_debit = oh_credit
                oh_debit_line[2]['debit'] = oh_debit

            move_id = self.env['account.move'].create(move_vals)
            self.write({'od_at_least_produced_once':True})
            if move_id:
                move_id.action_post()

    def od_create_landed_cost(self, production_id):
        """Create landed cost for production overhead"""
        if production_id:
            # product_id = self.get_id_from_param('od_overhead_product_id')
            # account_id = self.get_id_from_param('od_overhead_account_id')
            
            # if not product_id or not account_id:
            #     raise UserError(_("Overhead product or account not configured in system parameters"))
            product_id = self.company_id.od_overhead_product_id and self.company_id.od_overhead_product_id.id
            if not (product_id):
                raise UserError(_("Please set Overhead Product!!"))

            account_id = self.company_id.od_overhead_account_id and self.company_id.od_overhead_account_id.id
            if not (account_id):
                raise UserError(_("Please set Overhead Account!!"))
                
            cost_line_vals = {
                'product_id': int(product_id),
                'name': 'Overhead Cost',
                'account_id': int(account_id),
                'split_method': 'by_quantity',
                'price_unit': production_id.od_overhead_total
            }
            
            header_vals = {
                'mrp_production_ids': [(6, 0, production_id.ids)],
                'target_model': 'manufacturing',
                'cost_lines': [(0, 0, cost_line_vals)]
            }
            od_landed_cost_id = self.env['stock.landed.cost'].create(header_vals)
            od_landed_cost_id.button_validate()
            production_id.od_landed_cost_ids = [(6, 0, od_landed_cost_id.ids)]

    def od_check_qty(self):
        if not self.move_raw_ids:
            raise UserError("Raw Materials are not set!!!")
        for line in self.move_raw_ids:
            if not line.product_id.qty_available>0:
                raise UserError(_("No enough stock for Raw Material '%s' !!!")%(line.product_id.display_name))
            base_qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id, rounding_method='HALF-UP')
            if base_qty > line.product_id.qty_available:
                raise UserError(_("No enough stock for Raw Material '%s' !!!")%(line.product_id.display_name))


    def od_create_costing_sheet(self):
        """
        Create a comprehensive costing sheet for the manufacturing order
        by analyzing raw material, overhead, and finished product costs
        """
        # Remove existing cost sheet lines
        self.cost_sheet_lines_oh.unlink()
        self.cost_sheet_lines_rm.unlink()
        self.cost_sheet_lines_fp.unlink()
        
        # Get all account moves related to this production that aren't landed costs
        stock_move_ids = self.move_raw_ids.ids+self.move_finished_ids.ids
        move_domain = ['|',
            ('stock_move_id','in', stock_move_ids),
            '&',
            ('od_mrp_id', '=', self.id),
            ('landed_costs_ids', '=', False)
        ]
        od_move_ids = self.env['account.move'].search(move_domain)
        # print("od_move_ids",od_move_ids)
        
        # Get overhead journal parameter
        # overhead_journal_param = self.env['ir.config_parameter'].search([
        #     ('key', '=', 'od_overhead_journal')
        # ])
        # overhead_journal_id = int(overhead_journal_param.value)
        # print("koooo",overhead_journal_param)
        # if (not overhead_journal_param) or (not (overhead_journal_id>1)):
        #     raise UserError(_("'od_overhead_journal' parameter is not set"))
        overhead_journal_id = self.company_id.od_overhead_journal_id and self.company_id.od_overhead_journal_id.id
        if not (overhead_journal_id):
            raise UserError(_("Please set Overhead Journal!!"))
        
        # Categorize moves
        overhead_moves = od_move_ids.filtered(
            lambda x: x.journal_id.id == overhead_journal_id
        )
        raw_moves = od_move_ids.filtered(
            lambda x: x.stock_move_id.id in self.move_raw_ids.ids
        )

        finished_moves = od_move_ids.filtered(
            lambda x: x.stock_move_id.id in self.move_finished_ids.ids
        )
        
        # Calculate costs for each category
        if od_move_ids:
            self._calculate_raw_material_costs(raw_moves)
            self._calculate_overhead_costs(overhead_moves)
            self._calculate_finished_product_costs(finished_moves)
        
        self.od_costing_computed = True

    def _calculate_raw_material_costs(self, raw_move_ids):
        """Calculate and create cost sheet lines for raw materials"""
        if not raw_move_ids:
            raise UserError(_("No cost for Raw Materials!!!"))
        
        # Use parameterized query to prevent SQL injection
        raw_query = """
            SELECT 
                aml.product_id as product_id,
                SUM(aml.quantity) as qty,
                CASE 
                    WHEN SUM(aml.quantity) <> 0 THEN (SUM(aml.debit) / SUM(aml.quantity))
                    ELSE 0 
                END AS unit_cost,
                SUM(aml.debit) as amount
            FROM account_move_line aml
            WHERE aml.debit > 0 AND aml.move_id in %s 
            GROUP BY aml.product_id
        """
        
        self._cr.execute(raw_query, (tuple(raw_move_ids.ids),))
        
        # Create cost sheet lines for raw materials
        cost_sheet_line_obj = self.env['od.mrp.cost.sheet.lines']
        for result in self._cr.dictfetchall():
            cost_sheet_line_obj.create({
                'production_id': self.id,
                'product_id': result['product_id'],
                'unit_cost': result['unit_cost'],
                'product_type': 'raw',
                'qty': result['qty'],
                'amount': result['amount']
            })

    def _calculate_overhead_costs(self, overhead_moves):
        """Calculate and create cost sheet lines for overhead costs"""
        if not overhead_moves:
            raise UserError(_("No cost for Overhead Materials"))
        
        # Use parameterized query to prevent SQL injection
        overhead_query = """
            SELECT 
                ol.product_id as product_id,
                SUM(ol.qty) as qty,
                CASE 
                    WHEN SUM(ol.qty) <> 0 THEN (SUM(aml.credit) / SUM(ol.qty))
                    ELSE 0 
                END AS unit_cost,
                SUM(aml.credit) as amount,
                ol.uom_id as uom_id
            FROM account_move_line aml
            LEFT JOIN od_mrp_overhead_line ol ON ol.id = aml.od_overhead_line_id
            WHERE abs(aml.credit) > 0 AND aml.move_id in %s 
            GROUP BY ol.product_id,ol.uom_id
        """
        
        self._cr.execute(overhead_query, (tuple(overhead_moves.ids),))
        
        # Create cost sheet lines for overhead
        cost_sheet_line_obj = self.env['od.mrp.cost.sheet.lines']
        for result in self._cr.dictfetchall():
            unit_cost = result['unit_cost']
            qty = result['qty']
            amount = result['amount']
            uom_id = result['uom_id'] or False

            ink_pdt_id = self.company_id.od_ink_id
            if result.get('product_id') == ink_pdt_id.id:
                classification_id = self.env['ir.config_parameter'].get_param('orchid_class_id')
                qty=sum(l.od_consumed for l in self.move_raw_ids.filtered(lambda x:x.product_id.orchid_class_id.id==classification_id)) or 0
                if qty:
                    unit_cost = amount/qty
            oh_vals ={
                'production_id': self.id,
                'product_id': result['product_id'],
                'unit_cost': unit_cost,
                'product_type': 'overhead',
                'qty': qty,
                'amount': amount,
                'uom_id':uom_id,
            }
            print("oh_vals",oh_vals)
            cost_sheet_line_obj.create(oh_vals)

    def _calculate_finished_product_costs(self, finished_moves):
        """Calculate and create cost sheet lines for finished products"""
        # Find finished product move lines
        fp_move_line_ids = finished_moves.line_ids.filtered(lambda x:x.product_id.id==self.product_id.id and x.debit>0)
        
        # Calculate total overhead cost
        total_overhead_cost = sum(
            cost.amount_total for cost in self.od_landed_cost_ids
        )
        
        # Calculate finished product cost
        finished_product_query = """
            SELECT 
                aml.product_id as product_id,
                SUM(aml.debit) as amount
            FROM account_move_line aml
            WHERE aml.id in %s 
            GROUP BY aml.product_id
        """
        
        self._cr.execute(finished_product_query, (tuple(fp_move_line_ids.ids),))
        
        # Create cost sheet lines for finished products
        cost_sheet_line_obj = self.env['od.mrp.cost.sheet.lines']
        total_unit_cost = 0
        for result in self._cr.dictfetchall():
            total_amount = result['amount'] + total_overhead_cost
            unit_cost = total_amount / self.qty_produced if self.qty_produced else 0
            total_unit_cost+=unit_cost
            
            cost_sheet_line_obj.create({
                'production_id': self.id,
                'product_id': result['product_id'],
                'unit_cost': unit_cost,
                'product_type': 'finished',
                'qty': self.qty_produced,
                'amount': total_amount
            })
        # self.od_sale_order_line_id.od_cost = total_unit_cost
        self.od_sale_order_line_id.order_id.od_find_cost()

    def od_create_costing_sheet_cron(self):
        """Cron method to create costing sheets for completed productions"""
        query = """
            SELECT id FROM mrp_production 
            WHERE state='done' AND date_finished>='2025-05-31' AND od_costing_computed IS NOT TRUE
        """
        self._cr.execute(query)
        results = self._cr.fetchall()
        record_ids = [z[0] for z in results]
        records = self.env['mrp.production'].browse(record_ids)
        
        for record in records:
            if (not record.cost_sheet_lines_fp) or (not record.cost_sheet_lines_rm) or (not record.cost_sheet_lines_oh):
                record.od_create_costing_sheet()

    def _get_plate_machine(self):
        """
        Get the plate machine based on configuration parameter or product search
        Returns the machine ID if found, otherwise False
        """
        if self.env.context.get('default_od_plate_manufacturing'):
            # First try to get from system parameter
            machine_param = self.env['ir.config_parameter'].search([
                ('key', '=', 'od_plate_machine')
            ])
            
            if machine_param and self.env.context.get('default_od_plate_manufacturing'):
                try:
                    return int(machine_param.value)
                except (ValueError, TypeError):
                    _logger.UserError("Invalid machine ID in system parameter")
            
        # Fallback to product search by name
        if self.env.context.get('default_od_plate_manufacturing'):
            machine = self.env['product.product'].search([
                ('name', '=', 'Machine - PLATE MACHINE')
            ], limit=1)
            
            if machine:
                return machine.id
        
        return False

    # def od_get_proof_request_specs(self):
    #     """Return a clean list of (label, value) pairs for proof request fields."""
    #     self.ensure_one()
    #     proof_request = self.od_sale_order_line_id.od_proof_request_ids or self.product_id.od_proof_request_id
    #     if not proof_request:
    #         return []

    #     # Define all label–field mappings you want to show
    #     fields_map = [
    #                     ('Product Segment', proof_request.product_segment),
    #                     ('Delivery Date', proof_request.od_delivery_date),
    #                     ('Micron', proof_request.od_micron),
    #                     ('Yards', proof_request.od_yards),
    #                     ('Inch', proof_request.od_inch),
    #                     ('Rolls', proof_request.od_rolls),
    #                     ('Box', proof_request.od_box),
    #                     ('Plastic', proof_request.od_plastic),
    #                     ('Ink Out', proof_request.od_inkout),
    #                     ('Ink In', proof_request.od_inkin),
    #                     ('Core', proof_request.od_core),
    #                     ('Width', proof_request.od_width),
    #                     ('Length', proof_request.od_length),
    #                     ('LBW', proof_request.od_lbw),
    #                     ('Printing Process', proof_request.od_printing_process),
    #                     ('Printing Side', proof_request.od_printing_sude),
    #                     ('Front Qty', proof_request.od_application_temp),
    #                     ('Back Qty', proof_request.od_storage_temp),
    #                     ('Winding Direction', proof_request.od_wdg_direction),
    #                     ('Winding Direction Back', proof_request.od_wdg_direction_back),
    #                     ('Continuous Print', proof_request.od_continouse_print),
    #                     ('Art Ref No', proof_request.od_art_ref_no),
    #                     ('Type of Primer', proof_request.od_type_of_primer),
    #                     ('Digital Ink', proof_request.od_digital_ink),
    #                     ('Embossing', proof_request.od_embossing),
    #                     ('Special Requirement', proof_request.od_speacial_req),
    #                     ('Special Requirement (Tags)', ', '.join(proof_request.od_speacial_req_id.mapped('name')) if proof_request.od_speacial_req_id else ''),
    #                     ('Type of Printing', proof_request.od_type_of_printing),
    #                     ('Print Finishing', proof_request.od_print_finishing),
    #                     ('Secondary Printing', proof_request.od_sec_printing),
    #                     ('No of Colors', proof_request.od_no_of_colors),
    #                     ('Screen', proof_request.od_screen),
    #                     ('Hot Foil', proof_request.od_hot_foil),
    #                     ('Cold Foil', proof_request.od_cold_foil),
    #                     ('Cold Foil Light', proof_request.od_cold_foil_light),
    #                     ('Holographic Foil', proof_request.od_holographic_foil),
    #                     ('Silver Foil', proof_request.od_silver_foil),
    #                     ('Glossy Lamination', proof_request.od_glossy_lamination),
    #                     ('Matt Lamination', proof_request.od_matt_lamination),
    #                     ('Adhesive', proof_request.od_adhesive),
    #                     ('Color Matching Ref', proof_request.od_color_matching_ref),
    #                     ('Conversion Format', proof_request.od_conv_format),
    #                     ('PMS No', proof_request.od_pms_no),
    #                     ('Product to be Filled', proof_request.od_prod_to_be_filled),
    #                     ('Container Type', proof_request.od_container_type),
    #                     ('Application', proof_request.od_application),
    #                     ('PCS/Roll', proof_request.od_pcs_roll),
    #                     ('Pack/Roll', proof_request.od_pack_roll),
    #                     ('Of Roll', proof_request.od_of_roll),
    #                     ('Cartons', proof_request.od_cartons),
    #                     ('Pallet Spec', proof_request.od_pallet_spec),
    #                     ('Die', proof_request.od_die_id if proof_request.od_die_id else '')
    #                 ]

    #     # Only return the fields that actually have a value
    #     return [(label, val) for label, val in fields_map if val]


    # def od_get_proof_request_specs(self):
    #     """Return a clean list of (label, value) pairs for proof request fields, showing labels for selection fields."""
    #     self.ensure_one()
    #     proof_request = self.od_sale_order_line_id.od_proof_request_ids or self.product_id.od_proof_request_id
    #     if not proof_request:
    #         return []

    #     # Define field–label pairs (technical field name as string instead of direct access)
    #     fields_map = [
    #         ('Product Segment', 'product_segment'),
    #         ('Delivery Date', 'od_delivery_date'),
    #         ('Micron', 'od_micron'),
    #         ('Yards', 'od_yards'),
    #         ('Inch', 'od_inch'),
    #         ('Rolls', 'od_rolls'),
    #         ('Box', 'od_box'),
    #         ('Plastic', 'od_plastic'),
    #         ('Ink Out', 'od_inkout'),
    #         ('Ink In', 'od_inkin'),
    #         ('Core', 'od_core'),
    #         ('Width', 'od_width'),
    #         ('Length', 'od_length'),
    #         ('LBW', 'od_lbw'),
    #         ('Printing Process', 'od_printing_process'),
    #         ('Printing Side', 'od_printing_sude'),
    #         ('Front Qty', 'od_application_temp'),
    #         ('Back Qty', 'od_storage_temp'),
    #         ('Winding Direction', 'od_wdg_direction'),
    #         ('Winding Direction Back', 'od_wdg_direction_back'),
    #         ('Continuous Print', 'od_continouse_print'),
    #         ('Art Ref No', 'od_art_ref_no'),
    #         ('Type of Primer', 'od_type_of_primer'),
    #         ('Digital Ink', 'od_digital_ink'),
    #         ('Embossing', 'od_embossing'),
    #         ('Special Requirement', 'od_speacial_req'),
    #         ('Special Requirement (Tags)', 'od_speacial_req_id'),
    #         ('Type of Printing', 'od_type_of_printing'),
    #         ('Print Finishing', 'od_print_finishing'),
    #         ('Secondary Printing', 'od_sec_printing'),
    #         ('No of Colors', 'od_no_of_colors'),
    #         ('Screen', 'od_screen'),
    #         ('Hot Foil', 'od_hot_foil'),
    #         ('Cold Foil', 'od_cold_foil'),
    #         ('Cold Foil Light', 'od_cold_foil_light'),
    #         ('Holographic Foil', 'od_holographic_foil'),
    #         ('Silver Foil', 'od_silver_foil'),
    #         ('Glossy Lamination', 'od_glossy_lamination'),
    #         ('Matt Lamination', 'od_matt_lamination'),
    #         ('Adhesive', 'od_adhesive'),
    #         ('Color Matching Ref', 'od_color_matching_ref'),
    #         ('Conversion Format', 'od_conv_format'),
    #         ('PMS No', 'od_pms_no'),
    #         ('Product to be Filled', 'od_prod_to_be_filled'),
    #         ('Container Type', 'od_container_type'),
    #         ('Application', 'od_application'),
    #         ('PCS/Roll', 'od_pcs_roll'),
    #         ('Pack/Roll', 'od_pack_roll'),
    #         ('Of Roll', 'od_of_roll'),
    #         ('Cartons', 'od_cartons'),
    #         ('Pallet Spec', 'od_pallet_spec'),
    #         ('Die', 'od_die_id'),
    #         ('Ups Across', 'od_die_ups_across'),
    #         ('Ups Around', 'od_die_ups_around'),
    #         ('Gap Around', 'od_die_gap_around'),
    #         ('Gap Across', 'od_die_gap_across'),
    #     ]

    #     result = []
    #     for label, field_name in fields_map:
    #         if not hasattr(proof_request, field_name):
    #             continue

    #         field_val = getattr(proof_request, field_name)
    #         if not field_val:
    #             continue

    #         # If field is a selection → get display label
    #         field = proof_request._fields[field_name]
    #         if field.type == 'selection':
    #             display_val = dict(proof_request.fields_get([field_name], ['selection'])[field_name]['selection']).get(field_val, field_val)
    #         elif field.type == 'many2one':
    #             display_val = field_val.display_name
    #         elif field_name == 'od_speacial_req_id':  # many2many tag field
    #             display_val = ', '.join(field_val.mapped('name'))
    #         else:
    #             display_val = field_val

    #         result.append((label, display_val))

    #     return result


    def od_get_proof_request_specs(self):
        self.ensure_one()
        proof_request = self.od_sale_order_line_id.od_proof_request_ids or self.product_id.od_proof_request_id
        if not proof_request:
            return []

        fields_map = [
            ('Product Segment', 'product_segment'),
            ('Delivery Date', 'od_delivery_date'),
            ('Micron', 'od_micron'),
            ('Yards', 'od_yards'),
            ('Inch', 'od_inch'),
            ('Rolls', 'od_rolls'),
            ('Box', 'od_box'),
            ('Plastic', 'od_plastic'),
            ('Ink Out', 'od_inkout'),
            ('Ink In', 'od_inkin'),
            ('Core', 'od_core'),
            ('Width', 'od_width'),
            ('Length', 'od_length'),
            ('LBW', 'od_lbw'),
            ('Printing Process', 'od_printing_process'),
            ('Printing Side', 'od_printing_sude'),
            ('Front Qty', 'od_application_temp'),
            ('Back Qty', 'od_storage_temp'),
            ('Winding Direction', 'od_wdg_direction'),
            ('Winding Direction Back', 'od_wdg_direction_back'),
            ('Continuous Print', 'od_continouse_print'),
            ('Art Ref No', 'od_art_ref_no'),
            ('Type of Primer', 'od_type_of_primer'),
            ('Digital Ink', 'od_digital_ink'),
            ('Embossing', 'od_embossing'),
            ('Special Requirement', 'od_speacial_req'),
            ('Special Requirement (Tags)', 'od_speacial_req_id'),
            ('Type of Printing', 'od_type_of_printing'),
            ('Print Finishing', 'od_print_finishing'),
            ('Secondary Printing', 'od_sec_printing'),
            ('No of Colors', 'od_no_of_colors'),
            ('Screen', 'od_screen'),
            ('Hot Foil', 'od_hot_foil'),
            ('Cold Foil', 'od_cold_foil'),
            ('Cold Foil Light', 'od_cold_foil_light'),
            ('Holographic Foil', 'od_holographic_foil'),
            ('Silver Foil', 'od_silver_foil'),
            ('Glossy Lamination', 'od_glossy_lamination'),
            ('Matt Lamination', 'od_matt_lamination'),
            ('Adhesive', 'od_adhesive'),
            ('Color Matching Ref', 'od_color_matching_ref'),
            ('Conversion Format', 'od_conv_format'),
            ('PMS No', 'od_pms_no'),
            ('Product to be Filled', 'od_prod_to_be_filled'),
            ('Container Type', 'od_container_type'),
            ('Application', 'od_application'),
            ('PCS/Roll', 'od_pcs_roll'),
            ('Pack/Roll', 'od_pack_roll'),
            ('Of Roll', 'od_of_roll'),
            ('Cartons', 'od_cartons'),
            ('Pallet Spec', 'od_pallet_spec'),
            ('Die', 'od_die_id'),
            ('Ups Across', 'od_die_ups_across'),
            ('Ups Around', 'od_die_ups_around'),
            ('Gap Around', 'od_die_gap_around'),
            ('Gap Across', 'od_die_gap_across'),
        ]

        result = []
        force_after_die = False

        for label, field_name in fields_map:
            if not hasattr(proof_request, field_name):
                continue

            field_val = getattr(proof_request, field_name)

            # # Turn on flag when Die has value
            # if field_name == 'od_die_id' and field_val:
            #     force_after_die = True

            # Skip empty fields unless we are *after Die*
            # if not field_val and not force_after_die:
            #     continue
            if not field_val:
                continue

            field = proof_request._fields[field_name]
            if field.type == 'selection':
                display_val = dict(
                    proof_request.fields_get([field_name], ['selection'])[field_name]['selection']
                ).get(field_val, field_val)
            elif field.type == 'many2one':
                display_val = field_val.display_name if field_val else ''
            elif field_name == 'od_speacial_req_id':  # many2many
                display_val = ', '.join(field_val.mapped('name')) if field_val else ''
            else:
                display_val = field_val or ''

            result.append((label, display_val))
        if self.od_cylinder:
            result.append(('Cylinder', self.od_cylinder.name))
        if self.od_digital:
            result.append(('Machine', self.od_machine_id.name))
        if self.od_sale_order_line_id:
            if self.od_sale_order_line_id.order_id.user_id:
                result.append(('Salesman',self.od_sale_order_line_id.order_id.user_id.name))

        return result





class OdMrpOverheadLine(models.Model):
    _name = "od.mrp.overhead.line"
    _description = "Overhead Line for Manufacturing"

    @api.depends('qty', 'cost')
    def _compute_amount(self):
        """Compute amount based on quantity and cost"""
        for line in self:
            line.amount = line.qty * line.cost
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        """Update line values when product changes"""
        for line in self:
            if line.product_id:
                line.od_auto = line.product_id.od_auto
                if line.product_id.od_timebase:
                    line.qty = line.mrp_id.od_hours
    
    mrp_id = fields.Many2one('mrp.production', "MO", ondelete="cascade")
    product_id = fields.Many2one('product.product', string="Product")
    qty = fields.Float(string="Qty/Hour", default=1)
    cost = fields.Float(string="Cost")
    amount = fields.Float(string="Amount", compute="_compute_amount")
    od_auto = fields.Boolean(string="Auto")
    eval_code = fields.Text(string="Eval Code")
    uom_id = fields.Many2one('uom.uom', string="Uom")

class OdMrpCostSheetLines(models.Model):
    _name = 'od.mrp.cost.sheet.lines'
    _description = 'Cost Sheet Lines'
    
    production_id = fields.Many2one('mrp.production', string="Production")
    product_id = fields.Many2one('product.product', string='Product')
    unit_cost = fields.Float('Unit Cost')
    qty = fields.Float('Qty')
    amount = fields.Float('Amount')
    product_type = fields.Selection([
        ('overhead', 'Oh'),
        ('raw', 'Rm'),
        ('finished', 'Fm'),
    ], string='Product Type', default='raw')
    uom_id = fields.Many2one('uom.uom', string="Uom")


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.onchange('product_id')
    def onchange_product_id(self):
        """Update UOM based on product when in production context"""
        for move in self:
            product = move.product_id.with_context(lang=move._get_lang())
            move.name = product.partner_ref
        
            # Use production UOM if in production context
            if move.production_id or move._context.get('default_raw_material_production_id'):
                move.product_uom = product.od_production_uom_id.id or product.uom_id.id
            else:
                move.product_uom = product.uom_id.id

    @api.depends('quantity', 'product_uom', 'od_product_uom')
    def od_compute_consumed_sqm(self):
        """Compute consumed quantity in square meters"""
        for move in self:
            # print("heloooooooooooooooooooooooooooooooooooo")
            od_kg_uom_id = self.env['ir.config_parameter'].search([('key','=','od_kg_uom_id')]).value
            od_kg_uom_id = int(od_kg_uom_id)
            if (not od_kg_uom_id) or (not (od_kg_uom_id>1)):
                raise UserError("od_kg_uom_id parameter is not set")

            od_meter_uom_id = self.env['ir.config_parameter'].search([('key','=','od_meter_uom_id')]).value
            od_meter_uom_id = int(od_meter_uom_id)
            if (not od_meter_uom_id) or (not (od_meter_uom_id>1)):
                raise UserError("od_meter_uom_id parameter is not set")
            # print("fffffffff",move.product_uom.id,od_meter_uom_id, od_kg_uom_id)
            if move.product_uom and move.product_uom.id in [od_meter_uom_id, od_kg_uom_id]:  # Specific UOM IDs
                q = move.product_uom._compute_quantity(
                    move.quantity, 
                    move.od_product_uom, 
                    rounding_method='HALF-UP'
                )
                # sqm conversion for raadiant chnages on dec30 2025
                mm_width = move.product_id.od_raw_width
                # print("kjihgffffffffffff",q,move.quantity,mm_width,move.product_id,move.product_id.od_raw_width)
                if mm_width:
                    # calculation based on the ss given by radiant---meter qty(to consume)*mm_width/1000 eg given by them 2000mtr*280mm/1000=560sqm
                    # print("errrrrrrrpppp")
                    q = move.quantity*mm_width/1000
                    # print("qweerrrr4r",q,move.quantity,mm_width)
            else:
                q = move.quantity
            # print("qqqqqqqqqqqqqqqqqqq",q)
                
            move.od_consumed = q
            
            # Set price unit if not set
            if not move.price_unit or move.price_unit == 0:
                move.price_unit = move.product_id.standard_price

    od_product_uom = fields.Many2one('uom.uom', string="Uom(Base)", related="product_id.uom_id", 
                                    readonly=True, store=True)
    od_consumed = fields.Float(string="Consumed(sqm)", compute="od_compute_consumed_sqm")


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    od_overhead_line_id = fields.Many2one('od.mrp.overhead.line', string="Overhead Line")

class AccountMove(models.Model):
    _inherit = "account.move"

    od_mrp_id = fields.Many2one('mrp.production', string="Production")

class OdMrpInterCompanyLine(models.Model):
    _name = "od.mrp.intercompany.line"
    _description = "Inter Company Transfer Line for Manufacturing"

    mrp_id = fields.Many2one('mrp.production', "MO", ondelete="cascade", copy=False)
    product_id = fields.Many2one('product.product', string="Product")
    qty = fields.Float(string="Qty", default=1)
    price_unit = fields.Float(string="Unit Price", default=1)
    company_id = fields.Many2one('res.company', string="Company", related="mrp_id.company_id", store=True)
    from_company_id = fields.Many2one('res.company', string="From")
    state = fields.Selection([('Draft','Draft'),('Validated','Validated')], string="State", default='Draft')
    transfer_picking_id = fields.Many2one('stock.picking', string="Outgoing Transfer")
    receive_picking_id = fields.Many2one('stock.picking', string="Incoming Transfer")

    @api.onchange('product_id','from_company_id')
    def onchange_product_id(self):
        for line in self:
            if line.product_id:
                raw_product_ids = self.mrp_id.move_raw_ids.mapped('product_id').ids
                if line.product_id.id not in raw_product_ids:
                    raise UserError(_("This product is not found in this MO Raw Materials!!"))
                # line.price_unit = line.product_id.standard_price
                if line.sudo().from_company_id:
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
                'price_unit': rec.price_unit,
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
                'price_unit': rec.price_unit,
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



    def button_validate(self):
        # create intercompany transfer--recipt order in current company and delivery order in from company
        # check if the prodduct belong to the rawmaterials in the mrp
        self.action_intercompany_transfer()
        self.state = 'Validated'


class StockMove(models.Model):
    _inherit = "stock.move"

    od_produced_qty = fields.Float(string="Produced Qty")