from odoo import fields, models, _
from odoo.exceptions import UserError


class GarageDiscountWizard(models.TransientModel):
    _name = 'garage.discount.wizard'
    _description = 'Garage Discount Wizard'

    estimation_id = fields.Many2one(
        'garage.estimation',
        required=True
    )

    amount = fields.Float(
        string='Discount Amount',
        required=True
    )

    def action_confirm(self):

        self.ensure_one()

        estimation = self.estimation_id

        discount_product = (
            estimation.company_id.sale_discount_product_id
        )

        if not discount_product:

            values = {
                'name': _('Discount'),
                'type': 'service',
                'invoice_policy': 'order',
                'list_price': 0.0,
                'company_id': estimation.company_id.id,
                'taxes_id': None,
            }

            services_category = self.env.ref(
                'product.product_category_services',
                raise_if_not_found=False
            )

            if services_category:
                values['categ_id'] = services_category.id

            discount_product = self.env[
                'product.product'
            ].sudo().create(values)

            estimation.company_id.sale_discount_product_id = (
                discount_product.id
            )

        existing_discount_line = estimation.line_ids.filtered(
            lambda l:
            not l.display_type and
            l.product_id == discount_product
        )[:1]

        discount_amount = abs(self.amount) * -1

        if existing_discount_line:

            existing_discount_line.unit_price = (
                discount_amount
            )

        else:

            self.env['garage.estimation.line'].create({
                'estimation_id': estimation.id,
                'product_id': discount_product.id,
                'name': discount_product.name,
                'qty': 1,
                'unit_price': discount_amount,
                'sequence': 999,
            })

        return {'type': 'ir.actions.act_window_close'}