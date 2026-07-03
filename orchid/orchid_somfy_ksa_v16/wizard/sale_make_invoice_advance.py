# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        for so in self.sale_order_ids:
            if so.partner_id and so.partner_id.od_lic_expiry_date:
                today_date = fields.Date.today()
                if so.partner_id.od_lic_expiry_date<today_date:
                    raise UserError(_("License for this customer has been expired!!"))

        moves = self._create_invoices(self.sale_order_ids)
        for move in moves:
            move.button_update_custom_duty_line()

        if self.env.context.get('open_invoices'):
            return self.sale_order_ids.action_view_invoice()

        return {'type': 'ir.actions.act_window_close'}
