from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GarageJob(models.Model):
    _name = 'garage.job'
    _description = 'Garage Job Card'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    # ---------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------

    name = fields.Char(
        string='Job No',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )

    date = fields.Date(
        default=fields.Date.context_today,
        tracking=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        tracking=True
    )

    vehicle_id = fields.Many2one(
        'garage.vehicle',
        string='Vehicle',
        tracking=True
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        tracking=True
    )

    colour = fields.Char(
        string='Color',
        tracking=True
    )

    charger_type_id = fields.Many2one(
        'garage.charger.type',
        string='Charger Type',
        tracking=True
    )

    check_list_remarks = fields.Text(
        tracking=True
    )

    due_date_out = fields.Date(
        string='Due Date Out',
        tracking=True
    )

    promo_no = fields.Char(
        string='Promo No',
        tracking=True
    )

    sub_status_id = fields.Many2one(
        'garage.sub.status',
        string='Sub Status',
        tracking=True
    )

    priority = fields.Selection(
        [
            ('0', 'Low'),
            ('1', 'Medium'),
            ('2', 'High'),
            ('3', 'Very High'),
        ],
        default='0',
        tracking=True
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Quotation',
        tracking=True
    )

    estimation_id = fields.Many2one(
        'garage.estimation',
        string='Estimation',
        readonly=True,
        copy=False,
        tracking=True
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
        copy=False,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ],
        default='draft',
        tracking=True
    )

    # ---------------------------------------------------------
    # ESTIMATION PAGE
    # ---------------------------------------------------------

    estimation_no = fields.Char(
        readonly=True,
        tracking=True
    )

    customer_contact_no = fields.Char(
        string='Customer Contact No',
        tracking=True
    )

    brand_id = fields.Many2one(
        'garage.brand',
        string='Brand',
        tracking=True
    )

    vehicle_engine_id = fields.Many2one(
        'garage.vehicle.engine',
        string='Vehicle Engine',
        tracking=True
    )

    cylinder_id = fields.Many2one(
        'garage.cylinder',
        string='Cylinders',
        tracking=True
    )

    job_category_id = fields.Many2one(
        'garage.job.category',
        string='Job Category',
        tracking=True
    )

    remarks = fields.Text(
        tracking=True
    )

    next_service_reminder_date = fields.Date(
        tracking=True
    )

    coupen_no = fields.Char(
        string='Coupen No',
        tracking=True
    )

    order_type_id = fields.Many2one(
        'garage.order.type',
        string='Order Type',
        tracking=True
    )

    status_id = fields.Many2one(
        'garage.status',
        string='Status',
        tracking=True
    )

    # ---------------------------------------------------------
    # INSPECTION PAGE
    # ---------------------------------------------------------

    customer_approval = fields.Char(
        tracking=True
    )

    vehicle_vin_no = fields.Char(
        tracking=True
    )

    vehicle_model_id = fields.Many2one(
        'garage.vehicle.model',
        string='Vehicle Model',
        tracking=True
    )

    vehicle_year = fields.Selection(
        selection='_get_year_selection',
        tracking=True
    )

    kms = fields.Char(
        tracking=True
    )

    lpo_no = fields.Char(
        string='LPO No',
        tracking=True
    )

    re_do_job = fields.Boolean(
        tracking=True
    )

    driver_name_id = fields.Many2one(
        'hr.employee',
        string='Driver Name',
        tracking=True
    )

    discount = fields.Monetary(
        tracking=True
    )

    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson',
        tracking=True
    )

    lead_source_id = fields.Many2one(
        'garage.lead.source',
        string='Lead Source',
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id'
    )

    line_ids = fields.One2many(
        'garage.job.line',
        'job_id',
        string='Lines',
        copy=True
    )

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'garage_job_ir_attachments_rel',
        'job_id',
        'attachment_id',
        string='Attachments'
    )

    inspection_detail = fields.Html(
        tracking=True
    )

    tyre_check = fields.Text(
        tracking=True
    )

    advisor_id = fields.Many2one(
        'hr.employee',
        string='Advisor',
        tracking=True
    )

    supervisor_id = fields.Many2one(
        'hr.employee',
        string='Supervisor',
        tracking=True
    )

    technician_id = fields.Many2one(
        'hr.employee',
        string='Technician',
        tracking=True
    )

    estimated_job_completion_time = fields.Datetime(
        tracking=True
    )

    job_completion_time = fields.Datetime(
        readonly=True,
        tracking=True
    )

    brought_name_id = fields.Char(
        string='Brought Name ID',
        tracking=True
    )

    mulkiya_name_id = fields.Char(
        string='Mulkiya Name ID',
        tracking=True
    )

    delivery_date = fields.Datetime(
        tracking=True
    )

    received_date = fields.Datetime(
        tracking=True
    )

    purchase_order_count = fields.Integer(
        compute='_compute_purchase_order_count'
    )


    def _compute_purchase_order_count(self):

        PurchaseOrder = self.env['purchase.order']
        for rec in self:
            rec.purchase_order_count = PurchaseOrder.search_count([
                ('job_id', '=', rec.id)
            ])

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        for rec in self:
            vehicle = rec.vehicle_id
            if not vehicle:
                continue
            if vehicle.partner_id:
                rec.partner_id = vehicle.partner_id
            rec.brand_id = vehicle.brand_id
            rec.vehicle_model_id = vehicle.model_id
            rec.vehicle_vin_no = vehicle.vin_no
            rec.vehicle_year = vehicle.year
            rec.colour = vehicle.colour
            rec.kms = vehicle.kms

    def _get_vehicle_snapshot_vals(self):
        self.ensure_one()
        vehicle = self.vehicle_id
        partner = self.partner_id or vehicle.partner_id
        brand = self.brand_id or vehicle.brand_id
        vehicle_model = self.vehicle_model_id or vehicle.model_id
        return {
            'partner_id': partner.id if partner else False,
            'customer_contact_no': partner.phone if partner else False,
            'brand_id': brand.id if brand else False,
            'vehicle_model_id': vehicle_model.id if vehicle_model else False,
            'vehicle_vin_no': self.vehicle_vin_no or vehicle.vin_no,
            'vehicle_year': self.vehicle_year or vehicle.year,
            'colour': self.colour or vehicle.colour,
            'kms': self.kms or vehicle.kms,
        }

    def _ensure_analytic_account(self):
        self.ensure_one()
        if self.analytic_account_id:
            self._apply_analytic_distribution_to_related_orders()
            return self.analytic_account_id

        plan = self.env.ref(
            'orchid_garage.garage_job_plan_default',
            raise_if_not_found=False
        )
        if not plan:
            raise UserError(_('Garage Job Plan analytic plan is missing.'))

        analytic = self.env['account.analytic.account'].create({
            'name': self.name,
            'partner_id': (self.partner_id or self.vehicle_id.partner_id).id if (self.partner_id or self.vehicle_id.partner_id) else False,
            'plan_id': plan.id,
            'company_id': self.company_id.id,
        })
        self.analytic_account_id = analytic.id
        self._apply_analytic_distribution_to_related_orders()
        return analytic

    def _apply_analytic_distribution_to_related_orders(self):
        for job in self:
            analytic_distribution = job._get_analytic_distribution()
            if not analytic_distribution:
                continue

            if job.sale_order_id:
                for line in job.sale_order_id.order_line.filtered(lambda l: not l.display_type):
                    line.analytic_distribution = analytic_distribution

            purchase_orders = self.env['purchase.order'].search([
                ('job_id', '=', job.id),
            ])
            for order in purchase_orders:
                order._apply_job_analytic_distribution()

    def _get_analytic_distribution(self):
        self.ensure_one()
        if not self.analytic_account_id:
            return {}
        return {str(self.analytic_account_id.id): 100}

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
                'analytic_distribution': self._get_analytic_distribution(),
            })
        return vals

    def _prepare_sale_order_vals(self):
        self.ensure_one()
        partner_vals = self._get_vehicle_snapshot_vals()
        if not partner_vals['partner_id']:
            raise UserError(_('A customer is required before creating the quotation.'))
        return {
            'partner_id': partner_vals['partner_id'],
            'origin': self.name,
            'user_id': self.salesperson_id.id or self.env.user.id,
            'company_id': self.company_id.id,
            'job_id': self.id,
            'order_line': [(0, 0, self._prepare_sale_order_line_vals(line)) for line in self.line_ids],
        }

    def action_view_purchase_orders(self):

        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchases',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [
                ('job_id', '=', self.id)
            ],
            'context': {
                'default_job_id': self.id,
            }
        }

    def action_view_sale_order(self):
        self.ensure_one()
        if not self.sale_order_id:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quotation',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ---------------------------------------------------------
    # CREATE
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):

                vals['name'] = self.env[
                    'ir.sequence'
                ].next_by_code(
                    'garage.job'
                ) or _('New')

        return super().create(vals_list)

    # ---------------------------------------------------------
    # YEAR
    # ---------------------------------------------------------

    @api.model
    def _get_year_selection(self):

        current_year = fields.Date.today().year

        return [
            (str(year), str(year))
            for year in range(current_year, 1980, -1)
        ]

    # ---------------------------------------------------------
    # BUTTONS
    # ---------------------------------------------------------

    def action_start(self):
        for rec in self:
            rec._ensure_analytic_account()
            rec.state = 'in_progress'

    def action_close(self):
        for rec in self:
            rec._ensure_analytic_account()
            if not rec.sale_order_id:
                sale_order = self.env['sale.order'].create(rec._prepare_sale_order_vals())
                rec.sale_order_id = sale_order.id
            else:
                sale_order = rec.sale_order_id
                sale_order.job_id = rec.id
            rec.state = 'completed'
            rec.job_completion_time = fields.Datetime.now()



class GarageJobLine(models.Model):
    _name = 'garage.job.line'
    _description = 'Garage Job Line'
    _order = 'sequence, id'

    job_id = fields.Many2one(
        'garage.job',
        ondelete='cascade'
    )

    sequence = fields.Integer(
        default=10
    )

    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ])

    company_id = fields.Many2one(
        'res.company',
        related='job_id.company_id',
        store=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )

    name = fields.Char(
        string='Description'
    )

    remarks = fields.Char(
        string='Remarks'
    )

    qty = fields.Float(
        string='Qty',
        default=1.0
    )

    unit_price = fields.Float(
        string='Unit Price'
    )

    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        check_company=True
    )

    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_amount',
        store=True
    )

    price_total = fields.Monetary(
        string='Total',
        compute='_compute_amount',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='job_id.currency_id',
        store=True
    )

    @api.depends('qty', 'unit_price', 'tax_ids', 'display_type')
    def _compute_amount(self):
        for line in self:
            if line.display_type:
                line.price_subtotal = 0.0
                line.price_total = 0.0
                continue

            taxes = line.tax_ids.compute_all(
                line.unit_price,
                currency=line.currency_id,
                quantity=line.qty,
                product=line.product_id,
                partner=line.job_id.partner_id
            )
            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included']

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.name = line.product_id.display_name
                line.unit_price = line.product_id.lst_price
                line.tax_ids = line.product_id.taxes_id.filtered(
                    lambda t: t.company_id.id == line.company_id.id
                )
