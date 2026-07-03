# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models, _
import base64
import codecs
from datetime import datetime
from io import BytesIO
import qrcode
import pytz

class AccountMove(models.Model):
    _inherit = 'account.move'

    qr_code = fields.Binary(string='QR code',copy=False)
    
    def action_post(self):
        res = super(AccountMove, self).action_post()
        self.generate_qrcode()
        return res

    def generate_qrcode(self):
        # if self.journal_id.id==14:
        if self.move_type in ('out_invoice','out_refund'):
            self_user = self.env.user
            if self.env.user.tz:
                date_time = datetime.now()
                normal_invoice_date = date_time.strftime("%Y-%m-%dT%H:%M:%S")
                normal_invoice_date1 = datetime.strptime(normal_invoice_date, "%Y-%m-%dT%H:%M:%S")
                inv_date_time = normal_invoice_date1.astimezone(pytz.timezone(self.env.user.tz)).isoformat()
                inv_date_time = inv_date_time.split('+')[0] + 'Z'
            else:
                inv_date_time = ''

            name_l = len(str(self.company_id.name))
            vat_registration_l = len(str(self.company_id.vat))
            time_stamp_l = len(str(inv_date_time))
            invoice_total_l = len(str(self.amount_total))
            vat_total_l = len(str(self.amount_tax))

            name_hex = self.company_id.name.encode('utf-8').hex()
            if self.company_id.vat:
                vat_registration_hex = self.company_id.vat.encode('utf-8').hex()
            else:
                vat_registration_hex = ''
            time_stamp_hex = str(inv_date_time).encode('utf-8').hex()
            invoice_total_hex = str(self.amount_total).encode('utf-8').hex()
            vat_total_hex = str(self.amount_tax).encode('utf-8').hex()

            name = '010' + hex(name_l)[2:] + name_hex if name_l <= 15 else '01' + hex(
                name_l)[2:] + name_hex
            if self.company_id.vat:
                vat_registration = '020' + hex(vat_registration_l)[
                                           2:] + vat_registration_hex if vat_registration_l <= 15 else '02' + hex(
                    vat_registration_l)[2:] + vat_registration_hex
            else:
                vat_registration = ''
            if inv_date_time:
                time_stamp = '030' + hex(time_stamp_l)[
                                     2:] + time_stamp_hex if time_stamp_l <= 15 else '03' + hex(
                    time_stamp_l)[2:] + time_stamp_hex
            else:
                time_stamp = ''

            invoice_total = '040' + hex(invoice_total_l)[
                                    2:] + invoice_total_hex if invoice_total_l <= 15 else '04' + hex(
                invoice_total_l)[2:] + invoice_total_hex

            vat_total = '050' + hex(vat_total_l)[
                                2:] + vat_total_hex if vat_total_l <= 15 else '05' + hex(
                vat_total_l)[2:] + vat_total_hex

            hex_data = name + vat_registration + time_stamp + invoice_total + vat_total
            b64 = codecs.encode(codecs.decode(hex_data, 'hex'), 'base64').decode()

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )

            qr.add_data(b64)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            self.qr_code = qr_image

    