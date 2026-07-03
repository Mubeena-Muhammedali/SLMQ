# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class OrchidCBMRate(models.Model):
	_name = "orchid.cbm.rate"
	_description="CBM Rate Master"

	name = fields.Date(string="Date")
	rate = fields.Float(string="Rate per unit")