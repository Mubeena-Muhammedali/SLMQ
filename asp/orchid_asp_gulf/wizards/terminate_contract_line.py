# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pandas as pd


class OrchidTerminateContractLine(models.Model):
	_name = 'od.terminate.contract.line'
	_description = "Terminate Contract Line"

	@api.model
	def default_get(self, fields):
		result = super(OrchidTerminateContractLine, self).default_get(fields)
		if not result.get('contract_line_id') and self.env.context.get('active_id'):
			result['contract_line_id'] = self.env.context.get('active_id')
		return result

	contract_line_id = fields.Many2one('od.asp.contract.line', string="Contract Line")
	termination_date = fields.Date(string="Termination Date")
	termination_reason = fields.Char(string="Termination Reason")

	def button_terminate(self):
		if self.termination_date and self.termination_reason:
			self.contract_line_id.sudo().write({'termination_date':self.termination_date,'termination_reason':self.termination_reason,'state':'terminate'})
			start_date = self.contract_line_id.billing_from
			end_date = self.termination_date
			months = pd.date_range(start_date, end_date, freq='M')
			frequency=len(months)
			self.contract_line_id.order_line_id.od_frequency=frequency
			return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.asp.contract',
			  'res_id': self.contract_line_id.order_id.id,
			  'type': 'ir.actions.act_window',
			  }
