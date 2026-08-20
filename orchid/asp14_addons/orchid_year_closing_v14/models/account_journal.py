# -*- coding: utf-8 -*-
from odoo import fields,models,api,_

class OrchidAccountJournal(models.Model):
	_inherit = "account.journal"
	
	od_closing_journal = fields.Boolean(string="Closing Journal",default=False)