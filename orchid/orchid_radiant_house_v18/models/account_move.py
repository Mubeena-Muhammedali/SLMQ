# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict

class AccountMove(models.Model):
	_inherit = "account.move"

	od_picking_name = fields.Char(string="Related Stock Transfers")

class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	od_customer_order = fields.Float(string="Customer Order")
	od_customer_uom_id = fields.Many2one('uom.uom', string="Customer UOM")
