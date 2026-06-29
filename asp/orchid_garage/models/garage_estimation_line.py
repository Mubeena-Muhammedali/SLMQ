from odoo import api, fields, models
from collections import defaultdict


class GarageEstimationLine(models.Model):
    _name = 'garage.estimation.line'
    _description = 'Garage Estimation Line'
    _inherit = ['mail.thread']
    _order = 'sequence, id'

    estimation_id = fields.Many2one(
        'garage.estimation',
        ondelete='cascade'
    )

    sequence = fields.Integer(default=10)

    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note'),
    ], default=False)

    name = fields.Char(
        'Description',
        tracking=True
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        tracking=True
    )

    remarks = fields.Char(
        string='Remarks',
        tracking=True
    )

    qty = fields.Float(
        string='Qty',
        default=1.0,
        tracking=True
    )

    unit_price = fields.Float(
        string='Unit Price',
        tracking=True
    )

    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        check_company=True,
        tracking=True
    )

    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_amount',
        store=True,
        tracking=True
    )

    price_total = fields.Monetary(
        string='Total',
        compute='_compute_amount',
        store=True,
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='estimation_id.currency_id',
        store=True
    )

    company_id = fields.Many2one(
        'res.company',
        related='estimation_id.company_id',
        store=True
    )

    @api.depends('qty', 'unit_price', 'tax_ids')
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
                partner=line.estimation_id.partner_id
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

    @api.onchange('product_id', 'company_id')
    def _onchange_tax_ids(self):
        lines_by_company = defaultdict(lambda: self.env['garage.estimation.line'])
        cached_taxes = {}
        for line in self:
            lines_by_company[line.company_id] += line
        for company, lines in lines_by_company.items():
            for line in lines.with_company(company):
                taxes = None
                if line.product_id:
                    taxes = line.product_id.taxes_id._filter_taxes_by_company(company)
                if not line.product_id or not taxes:
                    # Nothing to map
                    line.tax_ids = False
                    continue
                fiscal_position = line.estimation_id.partner_id.property_account_position_id
                cache_key = (fiscal_position.id, company.id, tuple(taxes.ids))
                cache_key += line._get_custom_compute_tax_cache_key()
                if cache_key in cached_taxes:
                    result = cached_taxes[cache_key]
                else:
                    result = fiscal_position.map_tax(taxes)
                    cached_taxes[cache_key] = result
                # If company_id is set, always filter taxes by the company
                line.tax_ids = result

    def _get_custom_compute_tax_cache_key(self):
        """Hook method to be able to set/get cached taxes while computing them"""
        return tuple()