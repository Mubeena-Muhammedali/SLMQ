import json
import requests
from odoo import models


class TwilioWhatsApp(models.AbstractModel):
    _name = 'twilio.whatsapp'
    _description = 'Twilio WhatsApp Service'

    def _get_config(self):
        params = self.env['ir.config_parameter'].sudo()
        return {
            'sid': params.get_param('twilio.sid'),
            'token': params.get_param('twilio.token'),
            'from_number': params.get_param('twilio.whatsapp_number'),
        }

    def send_template_message(self, to_number, variables, content_sid):
        config = self._get_config()

        to_number = to_number.strip().replace(' ', '')

        data = {
            'From': f'whatsapp:{config["from_number"]}',
            'To': f'whatsapp:{to_number}',
            'ContentSid': content_sid,
            'ContentVariables': json.dumps(variables),
        }

        response = requests.post(
            f'https://api.twilio.com/2010-04-01/Accounts/{config["sid"]}/Messages.json',
            data=data,
            auth=(config['sid'], config['token'])
        )

        return response.json()

    def send_pdf_message(self, to_number, message, pdf_file):
        """
        pdf_file = binary (base64)
        """
        import requests

        config = self._get_config()

        # ✅ Clean phone number
        to_number = ''.join((to_number or '').split())

        # ✅ Create public attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'whatsapp.pdf',
            'type': 'binary',
            'datas': pdf_file,
            'mimetype': 'application/pdf',
            'public': True,
        })

        # ✅ Generate URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        media_url = f"{base_url}/web/content/{attachment.id}?download=true"

        # ✅ Send request
        data = {
            'From': f'whatsapp:{config["from_number"]}',
            'To': f'whatsapp:{to_number}',
            'Body': message,
            'MediaUrl': media_url,
        }

        response = requests.post(
            f'https://api.twilio.com/2010-04-01/Accounts/{config["sid"]}/Messages.json',
            data=data,
            auth=(config['sid'], config['token'])
        )

        return response.json()