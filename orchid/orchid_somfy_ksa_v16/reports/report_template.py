# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class OrchidReportTemplate(models.Model):
	_name = "od.report.template"
	_description="Report Template"

	name=fields.Char(string="Name")
	account_grp_id = fields.Many2one('account.group', string="Account Group", required=True)
	sequence = fields.Integer(string="Sequence", required=True)
	display_details = fields.Selection([('accounts','Display Accounts'),('compute','Compute')], string="Display Details", required=True)
	account_group_ids = fields.One2many('od.report.template.group', 'template_id', string="Account Child Groups")
	account_account_ids = fields.One2many('od.report.template.account', 'template_id', string="Account Group Accounts")
	report_value = fields.Selection([('pl','Profit & Loss'),('marketing','Marketing Report'),('balance_sheet','Balance Sheet')], string="Report", required=True,default='pl')
	
	show_group_budget = fields.Boolean(string="Show group in budget", default=False)
	 
	@api.onchange('account_grp_id')
	def onchange_name(self):
		for template in self:
			if template.account_grp_id:
				template.name=template.account_grp_id.name



class OrchidReportTemplateGroup(models.Model):
	_name = "od.report.template.group"
	_description="Report Template Child Groups"
	
	template_id = fields.Many2one('od.report.template', string=" Report Template")
	report_value = fields.Selection([('pl','Profit & Loss'),('marketing','Marketing Report')], string="Report", related="template_id.report_value", store=True)
	name=fields.Many2one('od.report.template', string="Group")

class OrchidReportTemplateAccount(models.Model):
	_name = "od.report.template.account"
	_description="Report Template Group Accounts"

	name=fields.Many2one('account.account', string="Account")
	template_id = fields.Many2one('od.report.template', string=" Report Template")