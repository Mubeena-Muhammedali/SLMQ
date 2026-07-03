from odoo import models, fields, api,_
from datetime import  timedelta, tzinfo, time, date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

class OrchidBudget(models.Model):
	_inherit = 'orchid.budget'

	@api.model
	def default_get(self, fields):
		result = super(OrchidBudget, self).default_get(fields)
		lines = []
		report_template_id = self.env['od.report.template'].search([('show_group_budget','=',True)])
		for  report_template in  report_template_id:
			lines.append((0,0,{'report_template_id':report_template.id,'name':report_template.name}))
		template_ids = self.env['od.report.template'].search([('display_details','=','accounts'),('report_value','=','pl'),('id','not in',report_template_id.ids)], order="sequence asc")
		for template_id in template_ids:
			account_ids = template_id.account_account_ids.mapped('name')
			for account_id in account_ids:
				lines.append((0,0,{'account_id':account_id.id,'name':account_id.display_name}))

		result['od_budget_line_mnth']=lines
		return result

	def od_approve(self):
		# for line in self.od_budget_line_mnth:
		# 	if not (line.group_id or line.account_id or line.cost_center):
				# raise UserError('Please Fill Any of Group,Account,Cost Center')				
		self.write({'od_state':'approved'})

class OrchidBudgetLines(models.Model):
	_inherit='orchid.budget.line'

	report_template_id=fields.Many2one('od.report.template',string='Report Template')
	name = fields.Char(string="Account/Group")


