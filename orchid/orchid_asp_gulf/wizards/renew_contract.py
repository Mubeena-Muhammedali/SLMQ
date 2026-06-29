# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidContractRenew(models.Model):
	_name = 'od.renew.contract.wiz'
	_description = "Contract Renew"

	@api.model
	def default_get(self, fields):
		result = super(OrchidContractRenew, self).default_get(fields)
		if not result.get('contract_id') and self.env.context.get('active_id'):
			result['contract_id'] = self.env.context.get('active_id')
		return result

	contract_id = fields.Many2one('od.asp.contract', string="Contract")
	new_quotation= fields.Boolean(string="Create New Quotation", default=False)

	def button_renew(self):
		if self.contract_id:
			action=self.contract_id.button_renew(self.new_quotation)
			return action
			