# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
	_inherit = 'res.partner'

	od_exchange_rate = fields.Float(digits=0, default=1.0,string="Exchange Rate")