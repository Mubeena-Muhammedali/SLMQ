# -*- coding: utf-8 -*-

from odoo import models, fields, api


#Modification in User Master
class ResUsers(models.Model):
	_inherit = 'res.users'

	od_reporting_manger_id = fields.Many2one('res.users',string='Reporting Manager', ondelete='restrict')
	od_final_code = fields.Char(string="Final Code")