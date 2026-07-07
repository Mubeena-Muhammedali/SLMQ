# -*- coding: utf-8 -*-

from odoo import models, fields, api,_

class IrConfigParameter(models.Model):
	_inherit  = 'ir.config_parameter'

	company_id = fields.Many2one('res.company', string="Company", help="set value only if the param is company-specific")