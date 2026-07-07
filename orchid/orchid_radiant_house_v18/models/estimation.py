# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class OdEstimationProduct(models.Model):
    _name = 'od.estimation.product'
    _description = 'Estimation Product'
    _order = 'name'

    name = fields.Char(string="Product Name", required=True)
    price = fields.Monetary(string="Price", required=True, currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )


class OdEstimationTeethSize(models.Model):
    _name = 'od.estimation.teeth.size'
    _description = 'Estimation Teeth Size'
    _order = 'teeth'

    name = fields.Char(string="Name", compute='_compute_name', store=True)
    teeth = fields.Float(string="Teeth", required=True)
    length = fields.Float(string="Length", required=True)

    @api.depends('teeth', 'length')
    def _compute_name(self):
        for size in self:
            teeth = int(size.teeth) if size.teeth and size.teeth == int(size.teeth) else size.teeth
            size.name = _("%s Teeth / %s Length") % (teeth or 0, size.length or 0)


class OdEstimation(models.Model):
    _name = 'od.estimation'
    _description = 'Radiant House Estimation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string="Estimation Number", default="New", copy=False, readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string="Customer", tracking=True)
    project_detail = fields.Char(string="Project Detail", tracking=True)
    estimation_date = fields.Date(string="Estimation Date", default=fields.Date.context_today, tracking=True)
    valid_until = fields.Date(string="Valid Until", tracking=True)
    user_id = fields.Many2one('res.users', string="Responsible", default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('converted', 'Quotation Created'),
        ('cancel', 'Cancelled'),
    ], string="Status", default='draft', tracking=True)

    estimation_product_id = fields.Many2one('od.estimation.product', string="Product", tracking=True)
    quotation_id = fields.Many2one('sale.order', string="Sales Quotation", readonly=True, copy=False)
    note = fields.Text(string="Notes")

    width = fields.Float(string="Width", default=120.0)
    height = fields.Float(string="Height", default=49.0)
    across = fields.Float(string="Across", default=2.0)
    paper_width_extra = fields.Float(string="Paper Width Extra", default=16.0)
    paper_width = fields.Float(string="Paper Width", compute='_compute_estimation', store=True)
    sheets_per_roll = fields.Float(string="Stc/Roll", default=1000.0)
    paper_price = fields.Monetary(
        string="Material Price",
        related='estimation_product_id.price',
        store=True,
        readonly=True,
        currency_field='currency_id',
    )
    no_of_colors = fields.Float(string="No of Colors", default=6.0)
    number_of_plates = fields.Float(string="Number of Plates", default=5.0)
    gap_across = fields.Float(string="Gap Across", default=3.0)
    gap_around = fields.Float(string="Gap Around", default=7.0)
    price = fields.Monetary(string="Price", compute='_compute_estimation', store=True, currency_field='currency_id')

    quantity_of_rolls = fields.Float(string="Quantity of Rolls", default=10.0)
    number_of_around = fields.Float(string="Number of Around", default=4.0)
    cost_of_plates = fields.Monetary(string="Cost of Plates", compute='_compute_estimation', store=True, currency_field='currency_id')
    varnish_cost = fields.Monetary(string="Varnish Cost", compute='_compute_estimation', store=True, currency_field='currency_id')
    include_varnish = fields.Boolean(string="Include Varnish", default=True)
    ink_cost = fields.Monetary(string="Ink Cost", compute='_compute_estimation', store=True, currency_field='currency_id')
    die_cutter_cost = fields.Monetary(string="Die Cutter Cost", default=0.0, currency_field='currency_id')
    foil_width = fields.Float(string="Foil Width", compute='_compute_estimation', store=True)
    foil_cost = fields.Monetary(string="Foil Cost", compute='_compute_estimation', store=True, currency_field='currency_id')
    lamination_width = fields.Float(string="Lamination Width", compute='_compute_estimation', store=True)
    lamination_cost = fields.Monetary(string="Lamination Cost", compute='_compute_estimation', store=True, currency_field='currency_id')
    rolls_per_master = fields.Float(string="No of (1000 sct) Rolls / Master", compute='_compute_estimation', store=True)
    price_of_master = fields.Monetary(string="Price of Master", compute='_compute_estimation', store=True, currency_field='currency_id')
    total_liner_meters = fields.Float(string="Total Liner Metres for Job (m)", compute='_compute_estimation', store=True)
    total_cost_of_paper = fields.Monetary(string="Total Cost of Paper", compute='_compute_estimation', store=True, currency_field='currency_id')
    extra_line_wastage = fields.Float(string="Extra Line Wastage (m)", default=300.0)
    extra_wastage_for_printing = fields.Float(string="Extra Wastage for Printing", compute='_compute_estimation', store=True)
    include_printing_wastage = fields.Boolean(string="Include Extra Wastage for Printing", default=True)
    total_linear_meter = fields.Float(string="Total Linear Metre (m)", compute='_compute_estimation', store=True)
    cost_of_paper_with_waste = fields.Monetary(string="Cost of Paper with Waste", compute='_compute_estimation', store=True, currency_field='currency_id')

    machine_name = fields.Char(string="Machine", default="Gidue")
    machine_cost_per_hour = fields.Monetary(string="Cost per Hour", default=150.0, currency_field='currency_id')
    machine_speed = fields.Float(string="Machine Speed", default=75.0)
    make_ready_time = fields.Float(string="Make Ready Time (min)", default=30.0)
    roll_changeover_time = fields.Float(string="Roll Change Over Time", compute='_compute_estimation', store=True)
    machine_time_min = fields.Float(string="Machine Time (min)", compute='_compute_estimation', store=True)
    total_machine_hours = fields.Float(string="Total Machine Hours for Job", compute='_compute_estimation', store=True)
    additional_ribbon_cost = fields.Monetary(string="Additional Cost Ribbon", compute='_compute_estimation', store=True, currency_field='currency_id')
    total_machine_cost = fields.Monetary(string="Total Machine Cost", compute='_compute_estimation', store=True, currency_field='currency_id')
    uv_lamp_cost = fields.Monetary(string="UV Lamp Cost", compute='_compute_estimation', store=True, currency_field='currency_id')

    margin_option = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
    ], string="Margin", default='6', required=True)
    margin = fields.Float(string="Margin %", compute='_compute_estimation', store=True)
    total_cost = fields.Monetary(string="Total Cost", compute='_compute_estimation', store=True, currency_field='currency_id')
    total_sales = fields.Monetary(string="Total Sales", compute='_compute_estimation', store=True, currency_field='currency_id')
    price_per_roll = fields.Monetary(string="Price per Roll", compute='_compute_estimation', store=True, currency_field='currency_id')
    net_profit = fields.Float(string="Net Profit", compute='_compute_estimation', store=True)
    actual_profit = fields.Monetary(string="Actual Profit in Dirhams", compute='_compute_estimation', store=True, currency_field='currency_id')
    selling_price = fields.Monetary(string="Selling Price", compute='_compute_estimation', store=True, currency_field='currency_id')

    ribbon_width = fields.Float(string="Ribbon Width (mm)")
    ribbon_length = fields.Float(string="Ribbon Length (m)", default=450.0)
    ribbon_price_sqm = fields.Monetary(string="Ribbon Price / sqm", default=0.35, currency_field='currency_id')
    cost_of_each_ribbon = fields.Monetary(string="Cost of Each Ribbon", compute='_compute_estimation', store=True, currency_field='currency_id')
    across_printing = fields.Float(string="No of Across Printing", default=1.0)
    rolls_per_ribbon = fields.Float(string="Rolls / Ribbon (1000 pc)", compute='_compute_estimation', store=True)
    total_ribbon_required = fields.Float(string="Total Ribbon Required", compute='_compute_estimation', store=True)
    total_ribbon_cost = fields.Monetary(string="Total Ribbon Cost", compute='_compute_estimation', store=True, currency_field='currency_id')

    cylinder_height_1 = fields.Float(string="Height", default=49.0)
    cylinder_around_1 = fields.Float(string="Around", default=4.0)
    cylinder_teeth_size_id = fields.Many2one('od.estimation.teeth.size', string="Teeth Size")
    cylinder_teeth_1 = fields.Float(string="Teeth", default=70.0)
    repeat_length_1 = fields.Float(string="Repeat Length", compute='_compute_estimation', store=True)
    cylinder_gap_around_1 = fields.Float(string="Gap Around", compute='_compute_estimation', store=True)
    cylinder_height_2 = fields.Float(string="Height", default=43.0)
    cylinder_around_2 = fields.Float(string="Around", default=7.0)
    cylinder_teeth_2 = fields.Float(string="Teeth", default=102.0)
    repeat_length_2 = fields.Float(string="Repeat Length", compute='_compute_estimation', store=True)
    cylinder_gap_around_2 = fields.Float(string="Gap Around", compute='_compute_estimation', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('od.estimation') or 'New'
        return super().create(vals_list)

    @api.constrains('estimation_date', 'valid_until')
    def _check_valid_until(self):
        for estimation in self:
            if estimation.valid_until and estimation.estimation_date and estimation.valid_until < estimation.estimation_date:
                raise ValidationError(_("Valid Until date cannot be before Estimation Date."))

    @staticmethod
    def _safe_div(numerator, denominator):
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def _get_margin_rate(margin_option):
        return {
            '1': 0.60,
            '2': 0.55,
            '3': 0.50,
            '4': 0.45,
            '5': 0.40,
            '6': 0.35,
        }.get(margin_option, 0.35)

    @api.depends(
        'width', 'height', 'across', 'paper_width_extra', 'sheets_per_roll',
        'paper_price', 'estimation_product_id', 'estimation_product_id.price',
        'no_of_colors', 'number_of_plates', 'gap_across', 'gap_around',
        'quantity_of_rolls', 'number_of_around', 'include_varnish',
        'die_cutter_cost', 'extra_line_wastage',
        'include_printing_wastage', 'machine_cost_per_hour', 'machine_speed',
        'make_ready_time', 'margin_option', 'ribbon_width', 'ribbon_length',
        'ribbon_price_sqm', 'across_printing', 'cylinder_height_1',
        'cylinder_around_1', 'cylinder_teeth_1', 'cylinder_teeth_size_id',
        'cylinder_teeth_size_id.length', 'cylinder_height_2',
        'cylinder_around_2', 'cylinder_teeth_2')
    def _compute_estimation(self):
        for rec in self:
            rec.paper_width = (rec.width * rec.across) + rec.gap_across + rec.paper_width_extra
            rec.foil_width = rec.paper_width
            rec.lamination_width = rec.paper_width
            rec.margin = rec._get_margin_rate(rec.margin_option)
            rec.rolls_per_master = ((1000.0 / (rec.height + rec.gap_across)) * rec.across * 0.98) if (rec.height + rec.gap_across) else 0.0
            rec.total_liner_meters = rec._safe_div(rec.quantity_of_rolls, rec.rolls_per_master) * 1000.0
            rec.price_of_master = rec.paper_width * rec.paper_price
            rec.total_cost_of_paper = (rec.total_liner_meters * rec.price_of_master) / 1000.0
            rec.extra_wastage_for_printing = ((rec.total_liner_meters / 2000.0) * 40.0) if rec.include_printing_wastage else 0.0
            rec.total_linear_meter = rec.total_liner_meters + rec.extra_line_wastage + rec.extra_wastage_for_printing
            rec.cost_of_paper_with_waste = ((rec.total_linear_meter * rec.paper_width) / 1000.0) * rec.paper_price

            rec.cost_of_plates = (((((rec.width + rec.gap_across) * rec.across) * ((rec.height + rec.gap_around) * rec.number_of_around)) / 100.0) * 0.16) * rec.number_of_plates
            rec.varnish_cost = ((rec.total_linear_meter * rec.paper_width * 0.08) / 1000.0) if rec.include_varnish else 0.0
            rec.ink_cost = (((rec.paper_width * rec.total_linear_meter) / 1000.0) * 0.1 * rec.no_of_colors) / 2.0
            rec.foil_cost = (rec.foil_width * rec.total_linear_meter / 1000.0) * 0.8
            rec.lamination_cost = rec.lamination_width * rec.total_linear_meter * 0.13 / 1000.0

            rec.roll_changeover_time = (rec.total_linear_meter / 2000.0) * 10.0
            rec.machine_time_min = rec._safe_div(rec.total_linear_meter, rec.machine_speed)
            rec.total_machine_hours = (rec.make_ready_time + rec.machine_time_min + rec.roll_changeover_time) / 60.0
            rec.total_machine_cost = rec.total_machine_hours * rec.machine_cost_per_hour
            rec.uv_lamp_cost = rec.total_machine_hours * rec.no_of_colors

            rec.repeat_length_1 = rec.cylinder_teeth_size_id.length or (rec.cylinder_teeth_1 * 3.175)
            rec.cylinder_gap_around_1 = round(rec._safe_div(rec.repeat_length_1 - (rec.cylinder_height_1 * rec.cylinder_around_1), rec.cylinder_around_1), 2)
            rec.repeat_length_2 = rec.cylinder_teeth_2 * 3.175
            rec.cylinder_gap_around_2 = round(rec._safe_div(rec.repeat_length_2 - (rec.cylinder_height_2 * rec.cylinder_around_2), rec.cylinder_around_2), 2)

            rec.cost_of_each_ribbon = ((rec.ribbon_width * rec.ribbon_length) / 1000.0) * rec.ribbon_price_sqm
            rec.rolls_per_ribbon = rec._safe_div(rec.ribbon_length, rec.height + rec.gap_around) * rec.across_printing if (rec.height + rec.gap_around) else 0.0
            rec.total_ribbon_required = rec._safe_div(rec.quantity_of_rolls, rec.rolls_per_ribbon)
            rec.total_ribbon_cost = rec.total_ribbon_required * rec.cost_of_each_ribbon
            rec.additional_ribbon_cost = rec._safe_div(rec.total_ribbon_cost, rec.quantity_of_rolls)

            rec.total_cost = (
                rec.cost_of_paper_with_waste + rec.uv_lamp_cost + rec.lamination_cost +
                rec.varnish_cost + rec.ink_cost + rec.total_machine_cost +
                rec.total_ribbon_cost + rec.cost_of_plates + rec.die_cutter_cost
            )
            rec.total_sales = (rec.total_cost * rec.margin) + rec.total_cost
            rec.price_per_roll = rec._safe_div(rec.total_cost, rec.quantity_of_rolls)
            rec.selling_price = rec._safe_div(rec.total_sales, rec.quantity_of_rolls)
            rec.price = rec.selling_price
            rec.actual_profit = rec.total_sales - rec.total_cost
            rec.net_profit = rec._safe_div(rec.actual_profit, rec.total_sales)

    @api.onchange(
        'width', 'height', 'across', 'paper_width_extra', 'sheets_per_roll',
        'paper_price', 'estimation_product_id',
        'no_of_colors', 'number_of_plates', 'gap_across', 'gap_around',
        'quantity_of_rolls', 'number_of_around', 'include_varnish',
        'die_cutter_cost', 'extra_line_wastage',
        'include_printing_wastage', 'machine_cost_per_hour', 'machine_speed',
        'make_ready_time', 'margin_option', 'ribbon_width', 'ribbon_length',
        'ribbon_price_sqm', 'across_printing', 'cylinder_height_1',
        'cylinder_around_1', 'cylinder_teeth_1', 'cylinder_teeth_size_id',
        'cylinder_height_2',
        'cylinder_around_2', 'cylinder_teeth_2')
    def _onchange_estimation_inputs(self):
        for estimation in self:
            if estimation.cylinder_teeth_size_id:
                estimation.cylinder_teeth_1 = estimation.cylinder_teeth_size_id.teeth
        self._compute_estimation()

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_create_sales_quotation(self):
        for estimation in self:
            if estimation.quotation_id:
                raise UserError(_("A sales quotation is already linked to this estimation."))
            if not estimation.partner_id:
                raise UserError(_("Please select a customer before creating the sales quotation."))
            if not estimation.estimation_product_id:
                raise UserError(_("Please select an estimation product before creating the sales quotation."))
            if not estimation.quantity_of_rolls:
                raise UserError(_("Please enter a quantity before creating the sales quotation."))

            line_name = estimation.estimation_product_id.display_name
            if estimation.project_detail:
                line_name = "%s\n%s" % (line_name, estimation.project_detail)

            quotation = self.env['sale.order'].create({
                'partner_id': estimation.partner_id.id,
                'user_id': estimation.user_id.id,
                'company_id': estimation.company_id.id,
                'date_order': fields.Datetime.now(),
                'validity_date': estimation.valid_until,
                'origin': estimation.name,
                'note': estimation.note,
                'order_line': [(0, 0, {
                    'name': line_name,
                    'product_uom_qty': estimation.quantity_of_rolls,
                    'price_unit': estimation.selling_price,
                })],
            })
            estimation.write({
                'quotation_id': quotation.id,
                'state': 'converted',
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Quotation'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.quotation_id.id,
        }

    def action_view_sales_quotation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Quotation'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.quotation_id.id,
        }
