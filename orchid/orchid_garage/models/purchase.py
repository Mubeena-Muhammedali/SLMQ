from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    od_sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        tracking=True,
    )

    od_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        tracking=True,
    )

    od_vehicle_id = fields.Many2one('garage.vehicle', string='Vehicle', tracking=True)
    od_brand_id = fields.Many2one('garage.brand', string='Brand', tracking=True)
    od_model_id = fields.Many2one('garage.vehicle.model', string='Model', tracking=True)
    od_vin_no = fields.Char(string='VIN No', tracking=True)
    od_colour = fields.Char(string='Colour', tracking=True)
    od_kms = fields.Char(string='KMs', tracking=True)
    od_year = fields.Selection(selection='_od_get_year_selection', string='Year', tracking=True)
    od_customer_contact_no = fields.Char(string='Customer Contact No', tracking=True)
    od_remarks = fields.Text(string='Remarks', tracking=True)

    @api.model
    def _od_get_year_selection(self):
        current_year = fields.Date.today().year
        return [(str(year), str(year)) for year in range(current_year, 1980, -1)]

    def _od_get_sale_order_default_vals(self):
        self.ensure_one()
        sale_order = self.od_sale_order_id
        if not sale_order:
            return {}
        return {
            'od_analytic_account_id': sale_order.od_analytic_account_id.id or False,
            'origin': sale_order.name,
            'od_vehicle_id': sale_order.od_vehicle_id.id or False,
            'od_brand_id': sale_order.od_brand_id.id or False,
            'od_model_id': sale_order.od_model_id.id or False,
            'od_vin_no': sale_order.od_vin_no,
            'od_colour': sale_order.od_colour,
            'od_kms': sale_order.od_kms,
            'od_year': sale_order.od_year,
            'od_customer_contact_no': sale_order.od_customer_contact_no,
            'od_remarks': sale_order.od_remarks,
        }

    def _od_apply_sale_order_defaults(self):
        if self.env.context.get('od_skip_sale_order_defaults'):
            return
        for order in self:
            default_vals = order._od_get_sale_order_default_vals()
            if not default_vals:
                continue
            order.with_context(od_skip_sale_order_defaults=True).write(default_vals)

    def od_action_view_sale_order(self):
        self.ensure_one()
        sale_order = self.od_sale_order_id
        if not sale_order:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.onchange('od_sale_order_id')
    def _od_onchange_sale_order_id(self):
        for order in self:
            default_vals = order._od_get_sale_order_default_vals()
            for field_name, value in default_vals.items():
                order[field_name] = value
            order._od_apply_sale_analytic_distribution()

    def _od_get_sale_analytic_distribution(self):
        self.ensure_one()
        analytic_account = self.od_analytic_account_id
        if not analytic_account and self.od_sale_order_id:
            analytic_account = self.od_sale_order_id.od_analytic_account_id
        if not analytic_account:
            return {}
        return {str(analytic_account.id): 100}

    def od_check_sale_order_job_status(self):
        for order in self:
            sale_order = order.od_sale_order_id
            if sale_order and sale_order.od_job_status != 'in_progress':
                raise UserError(_('You can create purchase orders only when the job status is In Progress.'))

    def _od_apply_sale_analytic_distribution(self):
        for order in self:
            analytic_distribution = order._od_get_sale_analytic_distribution()
            if not analytic_distribution:
                continue
            for line in order.order_line.filtered(lambda l: not l.display_type):
                line.analytic_distribution = analytic_distribution

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('od_skip_sale_order_defaults'):
            return res
        if {'od_sale_order_id', 'od_analytic_account_id'} & set(vals):
            self.od_check_sale_order_job_status()
            self._od_apply_sale_order_defaults()
        if {'od_sale_order_id', 'order_line'} & set(vals):
            self._od_apply_sale_analytic_distribution()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders.od_check_sale_order_job_status()
        orders.with_context(od_skip_sale_order_defaults=True)._od_apply_sale_order_defaults()
        orders._od_apply_sale_analytic_distribution()
        return orders


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    od_sale_line_id = fields.Many2one(
        'sale.order.line',
        string='Sale Order Line',
        ondelete='set null',
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            order = line.order_id
            analytic_distribution = order._od_get_sale_analytic_distribution() if order else {}
            if analytic_distribution and not line.display_type:
                line.analytic_distribution = analytic_distribution
        return lines

    @api.onchange('product_id', 'order_id', 'display_type', 'od_sale_line_id')
    def _od_onchange_sale_analytic_distribution(self):
        for line in self:
            order = line.order_id
            if not order or line.display_type:
                continue
            analytic_distribution = order._od_get_sale_analytic_distribution()
            if analytic_distribution:
                line.analytic_distribution = analytic_distribution

    @api.onchange('od_sale_line_id')
    def _od_onchange_sale_line_id(self):
        for line in self:
            order = line.order_id
            if not order or line.display_type:
                continue
            analytic_distribution = order._od_get_sale_analytic_distribution()
            if analytic_distribution:
                line.analytic_distribution = analytic_distribution

    def write(self, vals):
        res = super().write(vals)
        if {'order_id', 'product_id', 'display_type', 'od_sale_line_id'} & set(vals):
            for line in self:
                order = line.order_id
                analytic_distribution = order._od_get_sale_analytic_distribution() if order else {}
                if analytic_distribution and not line.display_type:
                    line.analytic_distribution = analytic_distribution
        return res
