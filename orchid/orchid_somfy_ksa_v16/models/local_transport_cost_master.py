from datetime import datetime

from odoo import api, fields, models, _


class OdLocalTransportChargeMaster(models.Model):
	_name = "od.local.transport.charge.master"
	_description = "Local Transport charge Master"

	name = fields.Char(string='Location')
	cost = fields.Float(string='Cost')