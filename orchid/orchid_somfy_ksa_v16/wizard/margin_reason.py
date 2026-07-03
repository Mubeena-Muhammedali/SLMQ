from odoo import api, fields, models, _

class OrchidMarginSaleReason(models.TransientModel):
	_name = "od.margin.sale.reason"
	_description = "Reason for Margin < 15%"

	sale_id = fields.Many2one('sale.order', string="Sales Order")
	reason = fields.Char(string="Reason")

	@api.model
	def default_get(self, fields):
		result = super(OrchidMarginSaleReason, self).default_get()
		print("resulttttt",result)
		return result

	@api.model
	def default_get(self, fields):
		result = super(OrchidMarginSaleReason, self).default_get(fields)
		if not result.get('sale_id') :
			if self._context.get('sale_id'):
				result['sale_id'] = self._context.get('sale_id')[0]
			else:
				result['sale_id'] = self._context.get('active_id')
		return result

	def action_update_reason(self):
		return self.sale_id.action_update_reason(reason=self.reason)