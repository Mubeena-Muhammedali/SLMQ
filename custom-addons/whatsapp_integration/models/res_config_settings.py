from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    twilio_sid = fields.Char(string="Twilio SID", config_parameter='twilio.sid')
    twilio_token = fields.Char(string="Twilio Auth Token", config_parameter='twilio.token')
    twilio_whatsapp_number = fields.Char(string="Twilio WhatsApp Number", config_parameter='twilio.whatsapp_number')