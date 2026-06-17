# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class Lead2OpportunityPartner(models.TransientModel):
	_inherit = 'crm.lead2opportunity.partner'

	@api.model
	def default_get(self, fields):
		if self.env.context.get('active_id'):
			if not self.env['crm.lead'].browse(self.env.context.get('active_id')).user_id:
				raise UserError(_("Please Assign SalesPerson for the lead."))
		result = super(Lead2OpportunityPartner, self).default_get(fields)
		return result

class CrmLead(models.Model):
	_inherit = 'crm.lead'

	expected_revenue = fields.Float('One Time Revenue', tracking=True)
	recurring_revenue = fields.Float('Recurring Revenues', tracking=True)
	recurring_revenue_monthly = fields.Float('Expected MRR', store=True, compute="_compute_recurring_revenue_monthly", groups="crm.group_use_recurring_revenues")
	od_show_mark_lost_wiz = fields.Boolean(string="Show mark lost wizard button", compute="_od_compute_button_visibility")
	od_type = fields.Selection([('azure','Azure'), ('aws','AWS'), ('add','ADD'), ('amc','AMC'),
		('azzurance','Azzurance'), ('m365','M365'), ('iaas','IaaS'), ('mhs','MHS'),
		('cls','CLS'), ('ps','PS'), ('ts','TS'), ('mss','MSS'),
		('on_premise','On-Premise'), ('trading','Trading')], string="Type",tracking=True, required=True)
	od_deal_closing_date = fields.Date(string="Deal Closing Date")
	
	@api.depends('type','stage_id','active','probability')
	def _od_compute_button_visibility(self):
		od_show_mark_lost_wiz=True
		if self.type=='lead' and not self.active:
			od_show_mark_lost_wiz=False
		elif self.stage_id.id==4:
			od_show_mark_lost_wiz=False
		self.od_show_mark_lost_wiz =od_show_mark_lost_wiz

	def action_sale_quotations_new(self):
		'''changing stage to proposition when creating a quotation'''
		result = super(CrmLead, self).action_sale_quotations_new()
		self.stage_id=3
		return result

	@api.constrains('probability')
	def check_lead_probability(self):
		for record in self:
			if record.active:
				c_stage_id = record.stage_id
				n_stage_id = c_stage_id
				if c_stage_id.id!=1:
					n_id = record.stage_id.sequence+1

					n_stage_id = record.env['crm.stage'].search([('sequence','=',n_id)])
				if c_stage_id.id != n_stage_id.id:
					c_stage_probability = c_stage_id.probability
					n_stage_probability = n_stage_id.probability
					lead_probability = record.probability

					if not (n_stage_probability >lead_probability >=c_stage_probability) and c_stage_probability!=100 and c_stage_id.id!=6 :
						raise UserError(_("The probability should be between %s and %s.")%(c_stage_probability,n_stage_probability))##lower limit as base

				if c_stage_id.id == n_stage_id.id:
					lead_probability = record.probability
					c_stage_probability = c_stage_id.probability
					if not (0 <lead_probability <=c_stage_probability):
						raise UserError(_("The probability should be between %s and %s.")%(0,c_stage_probability))

	@api.depends('order_ids.state', 'order_ids.currency_id', 'order_ids.amount_untaxed', 'order_ids.date_order', 'order_ids.company_id')
	def _compute_sale_data(self):
		for lead in self:
			total = 0.0
			quotation_cnt = 0
			sale_order_cnt = 0
			company_currency = lead.company_currency or self.env.company.currency_id
			for order in lead.order_ids:
				if order.state in ('draft', 'sent','cancel'):
					quotation_cnt += 1
				if order.state not in ('draft', 'sent', 'cancel'):
					sale_order_cnt += 1
					total += order.currency_id._convert(
						order.amount_untaxed, company_currency, order.company_id, order.date_order or fields.Date.today())
			lead.sale_amount_total = total
			lead.quotation_count = quotation_cnt
			lead.sale_order_count = sale_order_cnt
