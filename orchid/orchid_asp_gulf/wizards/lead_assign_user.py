# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidLeadAssignUser(models.Model):
	_name = 'od.lead.assign.user'
	_description = "Assign Lead User"

	@api.model
	def default_get(self, fields):
		result = super(OrchidLeadAssignUser, self).default_get(fields)
		if not result.get('lead_id') and self.env.context.get('active_id'):
			result['lead_id'] = self.env.context.get('active_id')
		return result

	lead_id = fields.Many2one('crm.lead', string="Lead")
	user_id= fields.Many2one('res.users', string="Salesperson")

	def assign_user(self):
		if self.lead_id and self.user_id:
			self.lead_id.sudo().write({
				'user_id': self.user_id.id
			})

			return {
				'name': 'Opportunities',
				'type': 'ir.actions.act_window',
				'res_model': 'crm.lead',
				'view_mode': 'list',
				'views': [
					(self.env.ref('crm.crm_case_tree_view_oppor').id, 'list'),
				]
			}
