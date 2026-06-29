# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
	_inherit = "account.payment"
	
	od_check_date = fields.Date(string="Check Date",default=fields.Date.context_today)
	od_check_to = fields.Char(string="Cheque To")
	od_acc_payee= fields.Boolean(string='A/c Payee', default=True)
