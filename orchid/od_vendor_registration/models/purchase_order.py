from odoo import api, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner_id = vals.get('partner_id')

            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)
                partner._check_vendor_document_expiry()

        return super().create(vals_list)