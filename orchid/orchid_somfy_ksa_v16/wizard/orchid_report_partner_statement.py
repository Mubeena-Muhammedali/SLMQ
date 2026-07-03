from odoo import api, fields, models, tools,_
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools.profiler import profile


class OrchidPartnerStatementInher(models.TransientModel):
	_inherit = 'orchid.partner.statement'


	def print_pdf_report(self):
		# if self.user_has_groups('sales_team.group_sale_salesman'):
		if not self.partner_ids:
			if not self.user_has_groups('account.group_account_invoice'):
				raise UserError(_("You must define partners !!"))
		res = super(OrchidPartnerStatementInher, self).print_pdf_report()
		return res
