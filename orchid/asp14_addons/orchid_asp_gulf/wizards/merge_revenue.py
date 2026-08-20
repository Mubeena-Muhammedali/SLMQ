# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OrchidMergeRevenue(models.TransientModel):
	_name = 'od.merge.revenue.line.wiz'
	_description = "Merge Revenue Lines"

	@api.model
	def default_get(self, fields):
		result = super(OrchidMergeRevenue, self).default_get(fields)
		if not result.get('payment_id') and self.env.context.get('active_id'):
			result['payment_id'] = self.env.context.get('active_id')
		return result

	payment_id = fields.Many2one('od.contract.payment', string="Contract Payment")
	period_from = fields.Date(string="Period From")
	period_to = fields.Date(string="Period To")
	invoice_line = fields.One2many('od.contract.invoice.wiz.line','wiz_id', string="Lines")
	merge_from_period = fields.Date(string="Merge Period From")
	merge_to_period = fields.Date(string="Merge Period To")

	def merge_lines(self):
		# getlines for given Period
		# the lines for given period will be merged to given merge period even if there is another line for same period
		# if the line is already recognized warning will be there.if the entry is cancelled, the line will be merged
		get_lines_qry = '''SELECT id FROM od_contract_monthly_line
					  WHERE service_id=%s AND period_from>='%s' AND  period_to<='%s' '''%(self.payment_id.id,self.period_from,self.period_to)

		self._cr.execute(get_lines_qry)
		get_lines=self._cr.fetchall()
		if get_lines:
			line_ids=self.env['od.contract.monthly.line'].browse(line[0] for line in get_lines)
			amount=0
			for line_id in line_ids:
				if line_id.move_id and line_id.move_id.state=='posted':
					period=str(line_id.period_from)+' to '+str(line_id.period_to)
					raise UserError(_("The Revenue line for period '%s' has already been posted.Please cancel it!!")%(period))
				amount=amount+line_id.amount
			due = all(line.due for line in line_ids)
			line_vals={
			'period_from':self.merge_from_period,
			'period_to':self.merge_to_period,
			'amount':amount,
			'service_id':self.payment_id.id,
			'invoiced':False,
			'due':due,
			}
			self.env['od.contract.monthly.line'].create(line_vals)
			line_ids.unlink()
		else:
			raise UserError(_('No Revenue Lines Found for given period!!!'))