# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class OrchidReportTemplate(models.Model):
	_name = "od.report.template"
	_description="Report Template"

	name=fields.Char(string="Name")
	company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company.id)
	account_grp_id = fields.Many2one('account.group', string="Account Group", required=True, check_company=True)
	sequence = fields.Integer(string="Sequence", required=True)
	display_details = fields.Selection([('accounts','Display Accounts'),('compute','Compute'),('report_value','Report Value')], string="Display Details", required=True)
	account_group_ids = fields.One2many('od.report.template.group', 'template_id', string="Account Child Groups")
	account_account_ids = fields.One2many('od.report.template.account', 'template_id', string="Account Group Accounts")
	report_value = fields.Selection([('pl','Profit & Loss'),('tb','Trial Balance'),('bl','Balance Sheet')], string="Report", required=True,default='tb')
	sign = fields.Selection([('-1','Reverse sign'),('1','Preserve Sign')], string="Sign", default="1")
	report_template_id = fields.Many2one('od.report.template', string="Report Template")
	@api.onchange('account_grp_id')
	def onchange_name(self):
		for template in self:
			if template.account_grp_id:
				template.name=template.account_grp_id.name



class OrchidReportTemplateGroup(models.Model):
	_name = "od.report.template.group"
	_description="Report Template Child Groups"

	name=fields.Many2one('od.report.template', string="Group", domain=[('display_details','=','accounts')], check_company=True)
	template_id = fields.Many2one('od.report.template', string=" Report Template", ondelete='cascade')
	company_id = fields.Many2one('res.company', string="Company", related="template_id.company_id")

class OrchidReportTemplateAccount(models.Model):
	_name = "od.report.template.account"
	_description="Report Template Group Accounts"

	name=fields.Many2one('account.account', string="Account", check_company=True)
	template_id = fields.Many2one('od.report.template', string=" Report Template", check_company=True, ondelete='cascade')
	company_id = fields.Many2one('res.company', string="Company", related="template_id.company_id")
