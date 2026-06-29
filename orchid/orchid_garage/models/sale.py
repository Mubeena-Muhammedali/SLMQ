from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    job_id = fields.Many2one(
        'garage.job',
        string='Job Order',
        tracking=True
    )

    od_estimation_id = fields.Many2one(
        'garage.estimation',
        string='Estimation',
        readonly=True,
        copy=False,
        tracking=True,
    )

    od_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
        copy=False,
        tracking=True,
    )

    od_job_status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('in_progress', 'In Progress'),
            ('closed', 'Closed'),
        ],
        string='Job Status',
        default='draft',
        tracking=True,
    )

    od_date = fields.Date(string='Garage Date', tracking=True)
    od_vehicle_id = fields.Many2one('garage.vehicle', string='Vehicle', tracking=True)
    od_brand_id = fields.Many2one('garage.brand', string='Brand', tracking=True)
    od_model_id = fields.Many2one(
        'garage.vehicle.model',
        string='Model',
        tracking=True,
        domain="[('brand_id', '=', od_brand_id)]",
    )
    od_vin_no = fields.Char(string='VIN No', tracking=True)
    od_colour = fields.Char(string='Colour', tracking=True)
    od_kms = fields.Char(string='KMs', tracking=True)
    od_year = fields.Selection(selection='_od_get_year_selection', string='Year', tracking=True)

    od_customer_contact_no = fields.Char(string='Customer Contact No', tracking=True)
    od_charger_type_id = fields.Many2one('garage.charger.type', string='Charger Type', tracking=True)
    od_check_list_remarks = fields.Text(tracking=True)
    od_due_date_out = fields.Date(string='Due Date Out', tracking=True)
    od_promo_no = fields.Char(string='Promo No', tracking=True)
    od_sub_status_id = fields.Many2one('garage.sub.status', string='Sub Status', tracking=True)
    od_priority = fields.Selection(
        [
            ('0', 'Low'),
            ('1', 'Medium'),
            ('2', 'High'),
            ('3', 'Very High'),
        ],
        default='0',
        tracking=True,
    )

    od_vehicle_engine_id = fields.Many2one('garage.vehicle.engine', string='Vehicle Engine', tracking=True)
    od_cylinder_id = fields.Many2one('garage.cylinder', string='Cylinders', tracking=True)
    od_job_category_id = fields.Many2one('garage.job.category', string='Job Category', tracking=True)
    od_next_service_reminder_date = fields.Date(tracking=True)
    od_coupen_no = fields.Char(string='Coupen No', tracking=True)
    od_order_type_id = fields.Many2one('garage.order.type', string='Order Type', tracking=True)
    od_status_id = fields.Many2one('garage.status', string='Status', tracking=True)

    od_customer_approval = fields.Char(tracking=True)
    od_vehicle_vin_no = fields.Char(tracking=True)
    od_vehicle_model_id = fields.Many2one('garage.vehicle.model', string='Vehicle Model', tracking=True)
    od_vehicle_year = fields.Selection(selection='_od_get_year_selection', tracking=True)
    od_lpo_no = fields.Char(string='LPO No', tracking=True)
    od_re_do_job = fields.Boolean(tracking=True)
    od_driver_name_id = fields.Many2one('hr.employee', string='Driver Name', tracking=True)
    od_salesperson_id = fields.Many2one('res.users', string='Salesperson', tracking=True)
    od_lead_source_id = fields.Many2one('garage.lead.source', string='Lead Source', tracking=True)
    od_inspection_detail = fields.Html(tracking=True)
    od_tyre_check = fields.Text(tracking=True)

    od_advisor_id = fields.Many2one('hr.employee', string='Advisor', tracking=True)
    od_supervisor_id = fields.Many2one('hr.employee', string='Supervisor', tracking=True)
    od_technician_id = fields.Many2one('hr.employee', string='Technician', tracking=True)
    od_estimated_job_completion_time = fields.Datetime(tracking=True)
    od_job_completion_time = fields.Datetime(readonly=True, tracking=True)
    od_brought_name_id = fields.Char(string='Brought Name ID', tracking=True)
    od_mulkiya_name_id = fields.Char(string='Mulkiya Name ID', tracking=True)
    od_delivery_date = fields.Datetime(tracking=True)
    od_received_date = fields.Datetime(tracking=True)

    od_remarks = fields.Text(tracking=True)

    od_purchase_order_count = fields.Integer(compute='_od_compute_purchase_order_count')

    od_payment_count = fields.Integer(
        string="Payments",
        compute="_compute_payment_count"
    )

    def _compute_payment_count(self):
        for order in self:
            order.od_payment_count = self.env['account.payment'].search_count([
                ('od_sale_id', '=', order.id)
            ])

    @api.model
    def _od_get_year_selection(self):
        current_year = fields.Date.today().year
        return [(str(year), str(year)) for year in range(current_year, 1980, -1)]

    def _od_compute_purchase_order_count(self):
        PurchaseOrder = self.env['purchase.order']
        for order in self:
            order.od_purchase_order_count = PurchaseOrder.search_count([
                ('od_sale_order_id', '=', order.id),
            ])

    def od_action_view_purchase_orders(self):
        self.ensure_one()
        purchase_orders = self.env['purchase.order'].search([
            ('od_sale_order_id', '=', self.id),
        ])
        if not purchase_orders:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchases'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', purchase_orders.ids)],
            'context': {'default_od_sale_order_id': self.id},
        }

    def action_view_payments(self):
        self.ensure_one()

        payments = self.env['account.payment'].search([
            ('od_sale_id', '=', self.id)
        ])

        if len(payments) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'view_id': self.env.ref('account.view_account_payment_form').id,
                'res_id': payments.id,
                'target': 'current',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('account.view_account_payment_tree').id, 'list'),
                (self.env.ref('account.view_account_payment_form').id, 'form'),
            ],
            'domain': [('od_sale_id', '=', self.id)],
            'target': 'current',
        }

    def od_action_create_purchase_order(self):
        self.ensure_one()
        if self.od_job_status != 'in_progress':
            raise UserError(_('You can create purchase orders only when the job status is In Progress.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Purchase Order'),
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_origin': self.name,
                'default_od_sale_order_id': self.id,
                'default_od_analytic_account_id': self.od_analytic_account_id.id if self.od_analytic_account_id else False,
                'default_od_vehicle_id': self.od_vehicle_id.id if self.od_vehicle_id else False,
                'default_od_brand_id': self.od_brand_id.id if self.od_brand_id else False,
                'default_od_model_id': self.od_model_id.id if self.od_model_id else False,
                'default_od_vin_no': self.od_vin_no,
                'default_od_colour': self.od_colour,
                'default_od_kms': self.od_kms,
                'default_od_year': self.od_year,
                'default_od_customer_contact_no': self.od_customer_contact_no,
                'default_od_remarks': self.od_remarks,
                'default_company_id': self.company_id.id,
            },
        }

    def od_action_create_purchase_orders(self):
        return self.od_action_create_purchase_order()

    def _od_get_garage_analytic_plan(self):
        self.ensure_one()
        plan = self.env.ref(
            'orchid_garage.garage_job_plan_default',
            raise_if_not_found=False,
        )
        if not plan:
            raise UserError(_('Garage Job Plan analytic plan is missing.'))
        return plan

    def _od_get_garage_analytic_distribution(self):
        self.ensure_one()
        if not self.od_analytic_account_id:
            return {}
        return {str(self.od_analytic_account_id.id): 100}

    def _od_apply_garage_analytic_distribution(self):
        for order in self:
            analytic_distribution = order._od_get_garage_analytic_distribution()
            if not analytic_distribution:
                continue
            for line in order.order_line.filtered(lambda l: not l.display_type):
                line.analytic_distribution = analytic_distribution

    def _od_ensure_garage_analytic_account(self):
        self.ensure_one()
        if self.od_analytic_account_id:
            return self.od_analytic_account_id

        plan = self._od_get_garage_analytic_plan()
        analytic = self.env['account.analytic.account'].create({
            'name': self.name or self.origin or (self.od_estimation_id.name if self.od_estimation_id else False) or _('Garage Sale'),
            'partner_id': self.partner_id.id if self.partner_id else False,
            'plan_id': plan.id,
            'company_id': self.company_id.id,
        })
        self.od_analytic_account_id = analytic.id
        return analytic

    def _od_validate_related_delivery_pickings(self):
        self.ensure_one()
        pickings = self.picking_ids.filtered(
            lambda picking:
            picking.picking_type_code == 'outgoing' and
            picking.state not in ('done', 'cancel')
        )
        for picking in pickings:
            result = picking.button_validate()
            if isinstance(result, dict):
                raise UserError(_(
                    'You must validate delivery %s manually before closing the job.'
                ) % (picking.name,))

    def od_action_close_job(self):
        for order in self:
            order._od_validate_related_delivery_pickings()
            order.od_job_status = 'closed'
        return True

    def _od_apply_vehicle_defaults(self):
        for order in self:
            vehicle = order.od_vehicle_id
            if not vehicle:
                continue
            order.od_brand_id = vehicle.brand_id
            order.od_model_id = vehicle.model_id
            order.od_vin_no = vehicle.vin_no
            order.od_colour = vehicle.colour
            order.od_kms = vehicle.kms
            order.od_year = vehicle.year
            order.od_vehicle_vin_no = vehicle.vin_no
            order.od_vehicle_model_id = vehicle.model_id
            order.od_vehicle_year = vehicle.year

    @api.onchange('od_vehicle_id')
    def _od_onchange_vehicle_id(self):
        self._od_apply_vehicle_defaults()

    @api.onchange('od_estimation_id')
    def _od_onchange_estimation_id(self):
        for order in self:
            estimation = order.od_estimation_id
            if not estimation:
                continue
            if estimation.partner_id:
                order.partner_id = estimation.partner_id
            if estimation.date:
                order.od_date = estimation.date
            if estimation.vehicle_id:
                order.od_vehicle_id = estimation.vehicle_id
            order.od_brand_id = estimation.brand_id
            order.od_model_id = estimation.model_id
            order.od_vin_no = estimation.vin_no
            order.od_colour = estimation.colour
            order.od_kms = estimation.kms
            order.od_year = estimation.year
            order.od_remarks = estimation.remarks

    @api.onchange('od_job_status')
    def od_onchange_job_status(self):
        for order in self:
            if order.od_job_status == 'closed':
                continue

    @api.onchange('od_analytic_account_id')
    def _od_onchange_analytic_account_id(self):
        self._od_apply_garage_analytic_distribution()

    @api.onchange('order_line', 'od_analytic_account_id')
    def _od_onchange_order_line_analytic_distribution(self):
        self._od_apply_garage_analytic_distribution()

    def write(self, vals):
        res = super().write(vals)
        if {'od_analytic_account_id', 'order_line', 'od_estimation_id', 'od_vehicle_id', 'od_job_status'} & set(vals):
            self._od_apply_garage_analytic_distribution()
        if 'od_vehicle_id' in vals:
            self._od_apply_vehicle_defaults()
        if vals.get('state') == 'draft':
            self.od_job_status = 'draft'
        if 'od_estimation_id' in vals:
            for order in self.filtered('od_estimation_id'):
                if order.od_estimation_id and not order.od_estimation_id.sale_order_id:
                    order.od_estimation_id.sale_order_id = order.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        Estimation = self.env['garage.estimation']
        for vals in vals_list:
            estimation_id = vals.get('od_estimation_id') or self.env.context.get('default_od_estimation_id')
            if estimation_id:
                estimation = Estimation.browse(estimation_id)
                estimation_vals = estimation._prepare_sale_order_vals()
                for key, value in estimation_vals.items():
                    if key == 'order_line':
                        if not vals.get(key):
                            vals[key] = value
                    else:
                        vals.setdefault(key, value)

        return super().create(vals_list)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            order._od_ensure_garage_analytic_account()
            order.od_job_status = 'in_progress'
            if order.od_estimation_id and not order.od_estimation_id.sale_order_id:
                order.od_estimation_id.sale_order_id = order.id
        self._od_apply_garage_analytic_distribution()
        return res

    def _create_invoices(self, grouped=False, final=False, date=None):
        for order in self:
            if order.od_job_status != 'closed':
                raise UserError(_('You can create an invoice only after the job is closed.'))
        return super()._create_invoices(grouped=grouped, final=final, date=date)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id', 'order_id', 'display_type')
    def _od_onchange_garage_analytic_distribution(self):
        for line in self:
            order = line.order_id
            if not order or line.display_type:
                continue
            analytic_distribution = order._od_get_garage_analytic_distribution()
            if analytic_distribution:
                line.analytic_distribution = analytic_distribution

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            order = line.order_id
            if order and order.od_analytic_account_id and not line.display_type:
                analytic_distribution = order._od_get_garage_analytic_distribution()
                if analytic_distribution:
                    line.analytic_distribution = analytic_distribution
        return lines

    def write(self, vals):
        res = super().write(vals)
        if {'order_id', 'product_id', 'display_type'} & set(vals):
            for line in self:
                order = line.order_id
                if order and order.od_analytic_account_id and not line.display_type:
                    analytic_distribution = order._od_get_garage_analytic_distribution()
                    if analytic_distribution:
                        line.analytic_distribution = analytic_distribution
        return res
