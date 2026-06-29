from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_garage_invoice_details(self):
        self.ensure_one()

        sale_orders = self.invoice_line_ids.mapped('sale_line_ids.order_id')
        sale_order = sale_orders[:1]
        if sale_order:
            garage_estimation = sale_order.od_estimation_id
            vehicle = sale_order.od_vehicle_id or (garage_estimation.vehicle_id if garage_estimation else False)
            brand = sale_order.od_brand_id or (vehicle.brand_id if vehicle else False) or (
                garage_estimation.brand_id if garage_estimation else False
            )
            model = sale_order.od_model_id or sale_order.od_vehicle_model_id or (
                vehicle.model_id if vehicle else False
            ) or (garage_estimation.model_id if garage_estimation else False)
            details = [
                ('Brand', brand.display_name if brand else ''),
                ('Model', model.display_name if model else ''),
                ('VIN No', sale_order.od_vin_no or sale_order.od_vehicle_vin_no or (vehicle.vin_no if vehicle else '') or (garage_estimation.vin_no if garage_estimation else '')),
                ('Plate No', vehicle.plate_no if vehicle else ''),
                ('Colour', sale_order.od_colour or (vehicle.colour if vehicle else '') or (garage_estimation.colour if garage_estimation else '')),
                ('KMS', sale_order.od_kms or (vehicle.kms if vehicle else '') or (garage_estimation.kms if garage_estimation else '')),
                ('Year', sale_order.od_year or sale_order.od_vehicle_year or (vehicle.year if vehicle else '') or (garage_estimation.year if garage_estimation else '')),
            ]

            return [item for item in details if item[1]]

        garage_estimation = self.env['garage.estimation'].sudo().search([
            ('sale_order_id', 'in', sale_orders.ids),
        ], limit=1)

        if not garage_estimation:
            return {}

        vehicle = garage_estimation.vehicle_id
        brand = vehicle.brand_id if vehicle else garage_estimation.brand_id
        model = vehicle.model_id if vehicle else garage_estimation.model_id
        sale_order_no = sale_order.name if sale_order else (garage_estimation.sale_order_id.name if garage_estimation.sale_order_id else '')

        details = [
            ('Brand', brand.display_name if brand else ''),
            ('Model', model.display_name if model else ''),
            ('VIN No', vehicle.vin_no if vehicle else (garage_estimation.vin_no or '')),
            ('Plate No', vehicle.plate_no if vehicle else ''),
            ('Colour', vehicle.colour if vehicle else (garage_estimation.colour or '')),
            ('KMS', vehicle.kms if vehicle else (garage_estimation.kms or '')),
            ('Year', vehicle.year if vehicle else (garage_estimation.year or '')),
        ]

        return [item for item in details if item[1]]


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_garage_sale_analytic_distribution(self):
        self.ensure_one()
        sale_orders = self.sale_line_ids.mapped('order_id')
        sale_order = sale_orders[:1]
        if not sale_order or not sale_order.od_analytic_account_id:
            return {}
        return {str(sale_order.od_analytic_account_id.id): 100}

    def _apply_garage_sale_analytic_distribution(self):
        for line in self:
            if line.display_type:
                continue
            analytic_distribution = line._get_garage_sale_analytic_distribution()
            if analytic_distribution:
                line.analytic_distribution = analytic_distribution

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._apply_garage_sale_analytic_distribution()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if {'sale_line_ids', 'move_id', 'display_type'} & set(vals):
            self._apply_garage_sale_analytic_distribution()
        return res

    @api.onchange('sale_line_ids', 'move_id', 'display_type')
    def _onchange_garage_sale_analytic_distribution(self):
        self._apply_garage_sale_analytic_distribution()
