from odoo import api, fields, models, _

# for gulf saleupload purpose
class AccountPaymentTerm(models.Model):
	_inherit = 'account.payment.term'

	od_code = fields.Char(string="Code")

class OrchidAccountCostCenter(models.Model):
	_inherit = "orchid.account.cost.center"

	include_pl=fields.Boolean(string="Include in P&L report")