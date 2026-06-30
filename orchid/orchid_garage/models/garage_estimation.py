from datetime import datetime

from odoo import api, fields, models, _


class GarageEstimation(models.Model):
    _name = 'garage.estimation'
    _description = 'Garage Estimation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ---------------------------------------------------------
    # BASIC
    # ---------------------------------------------------------

    job_id = fields.Many2one(
        'garage.job',
        string='Job Order',
        readonly=True,
        copy=False
    )

    name = fields.Char(
        string='Estimation No',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )

    date = fields.Date(string="Date", tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed')
    ],
        string='Status',
        default='draft',
        tracking=True
    )

    # ---------------------------------------------------------
    # CUSTOMER INFO
    # ---------------------------------------------------------

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
        readonly=True
    )

    brand_id = fields.Many2one(
        'garage.brand',
        string='Brand',
        tracking=True,
        readonly=True
    )

    model_id = fields.Many2one(
        'garage.vehicle.model',
        string='Model',
        tracking=True,
        domain="[('brand_id', '=', brand_id)]",
        readonly=True
    )

    vin_no = fields.Char(
        string='VIN No',
        tracking=True,
        readonly=True
    )

    vehicle_id = fields.Many2one(
        'garage.vehicle',
        string='Vehicle',
        tracking=True
    )

    colour = fields.Char(
        string='Colour',
        tracking=True,
        readonly=True
    )

    kms = fields.Char(
        string='KMs',
        tracking=True,
        readonly=True
    )

    year = fields.Selection(
        selection='_get_year_selection',
        string='Year',
        tracking=True,
        readonly=True
    )

    user_id = fields.Many2one(
        'res.users',
        string='Service Advisor',
        default=lambda self: self.env.user,
        tracking=True,
        readonly=True
    )

    salesperson_id = fields.Many2one('res.users', string='Salesperson', tracking=True)

    # ---------------------------------------------------------
    # LINES
    # ---------------------------------------------------------

    line_ids = fields.One2many(
        'garage.estimation.line',
        'estimation_id',
        string='Estimation Lines',
        readonly=True,
        copy=True
    )

    amount_before_discount = fields.Monetary(
        string='Amount Before Discount',
        compute='_compute_amounts',
        store=True
    )

    discount_amount = fields.Monetary(
        string='Discount Amount',
        compute='_compute_amounts',
        store=True
    )

    amount_untaxed = fields.Monetary(
        string='Subtotal',
        compute='_compute_amounts',
        store=True
    )

    amount_tax = fields.Monetary(
        string='Tax Amount',
        compute='_compute_amounts',
        store=True
    )

    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
        store=True
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True
    )

    currency_id = fields.Many2one(
        'res.currency',
         default=lambda self: self.env.company.currency_id,
        store=True
    )

    note = fields.Html(
        string="Terms and conditions")

    remarks = fields.Text(
        string="Remarks")

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        readonly=True,
        copy=False,
        help='Sale order created from this estimation.'
    )

    # ---------------------------------------------------------
    # YEAR SELECTION
    # ---------------------------------------------------------

    @api.model
    def _get_year_selection(self):
        current_year = datetime.now().year

        return [
            (str(year), str(year))
            for year in range(current_year, 1980, -1)
        ]

    # ---------------------------------------------------------
    # COMPUTE
    # ---------------------------------------------------------

    @api.depends(
        'line_ids.price_subtotal',
        'line_ids.price_total',
        'line_ids.product_id'
    )
    def _compute_amounts(self):

        for rec in self:

            discount_product = rec.company_id.sale_discount_product_id

            normal_lines = rec.line_ids.filtered(
                lambda l:
                not l.display_type and
                l.product_id != discount_product
            )

            discount_lines = rec.line_ids.filtered(
                lambda l:
                not l.display_type and
                l.product_id == discount_product
            )

            amount_before_discount = sum(
                normal_lines.mapped('price_subtotal')
            )

            discount_amount = abs(sum(
                discount_lines.mapped('price_subtotal')
            ))

            subtotal = sum(
                rec.line_ids.filtered(
                    lambda l: not l.display_type
                ).mapped('price_subtotal')
            )

            total = sum(
                rec.line_ids.filtered(
                    lambda l: not l.display_type
                ).mapped('price_total')
            )

            rec.amount_before_discount = amount_before_discount
            rec.discount_amount = discount_amount
            rec.amount_untaxed = subtotal
            rec.amount_tax = total - subtotal
            rec.amount_total = total

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'garage.estimation'
                ) or _('New')

        return super().create(vals_list)

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for rec in self:
            vehicle = rec.vehicle_id
            if not vehicle:
                continue
            if vehicle.partner_id:
                rec.partner_id = vehicle.partner_id
            rec.brand_id = vehicle.brand_id
            rec.model_id = vehicle.model_id
            rec.vin_no = vehicle.vin_no
            rec.colour = vehicle.colour
            rec.year = vehicle.year
            rec.kms = vehicle.kms

    @api.onchange('partner_id', 'vehicle_id')
    def _onchange_salesperson(self):
        for rec in self:
            # Priority 1: Vehicle salesperson
            if rec.vehicle_id and rec.vehicle_id.user_id:
                rec.salesperson_id = rec.vehicle_id.user_id
            # Priority 2: Customer salesperson
            elif rec.partner_id and rec.partner_id.user_id:
                rec.salesperson_id = rec.partner_id.user_id
            else:
                rec.salesperson_id = False

    def _prepare_sale_order_line_vals(self, line):
        vals = {
            'sequence': line.sequence,
            'display_type': line.display_type,
            'name': line.name,
        }

        if not line.display_type:
            vals.update({
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty,
                'price_unit': line.unit_price,
                'tax_ids': [(6, 0, line.tax_ids.ids)],
            })

        return vals

    def _prepare_sale_order_vals(self):
        self.ensure_one()
        vehicle = self.vehicle_id
        partner = self.partner_id or vehicle.partner_id
        brand = self.brand_id or vehicle.brand_id
        vehicle_model = self.model_id or vehicle.model_id
        sale_order_lines = []
        for line in self.line_ids:
            sale_order_lines.append((0, 0, self._prepare_sale_order_line_vals(line)))
        return {
            'od_date': self.date,
            'partner_id': partner.id if partner else False,
            'user_id': self.salesperson_id.id if self.salesperson_id else False,
            'company_id': self.company_id.id,
            'origin': self.name,
            'od_vehicle_id': vehicle.id,
            'od_customer_contact_no': partner.phone if partner else False,
            'od_brand_id': brand.id if brand else False,
            'od_model_id': vehicle_model.id if vehicle_model else False,
            'od_vehicle_model_id': vehicle_model.id if vehicle_model else False,
            'od_vin_no': self.vin_no or vehicle.vin_no,
            'od_vehicle_vin_no': self.vin_no or vehicle.vin_no,
            'od_vehicle_year': self.year or vehicle.year,
            'od_colour': self.colour or vehicle.colour,
            'od_kms': self.kms or vehicle.kms,
            'note': self.note,
            'od_remarks': self.remarks,
            'od_estimation_id': self.id,
            'order_line': sale_order_lines,
        }

    # ---------------------------------------------------------
    # BUTTONS
    # ---------------------------------------------------------

    def action_open_discount_wizard(self):
        self.ensure_one()

        return {
            'name': _('Add Discount'),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.discount.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_estimation_id': self.id,
            }
        }

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'

    def action_complete(self):
        for rec in self:
            sale_order = rec.sale_order_id
            if not sale_order:
                sale_order = self.env['sale.order'].create(rec._prepare_sale_order_vals())
                rec.sale_order_id = sale_order.id
            else:
                rec.sale_order_id = sale_order.id
            rec.state = 'completed'
        return self.action_view_sale_order() if len(self) == 1 else {'type': 'ir.actions.act_window_close'}

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_view_sale_order(self):
        self.ensure_one()
        sale_order = self.sale_order_id
        if not sale_order:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }
