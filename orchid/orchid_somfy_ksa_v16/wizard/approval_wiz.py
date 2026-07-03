from odoo import api, fields, models, _
from odoo.exceptions import UserError

class OrchidApprovalWiz(models.TransientModel):
	_name = 'orchid.approval.wiz'
	_description = 'Orchid Approve'

	account_opening_form_id = fields.Many2one('od.account.opening.form', string="Account Opening Form")
	pricelist_price_change_id = fields.Many2one('od.pricelist.price.change', string="Price Change")
	password = fields.Char(string="Password")

	@api.model
	def default_get(self, fields):
		result = super(OrchidApprovalWiz, self).default_get(fields)
		# print("jhgggggffffff",self._context,result)
		if not result.get('account_opening_form_id') and self._context.get('active_model')=='od.account.opening.form':
			# print("jhtrevvvvvvvvvvvvvv")
			if self._context.get('account_opening_form_id'):
				# print("opppppppp",self._context.get('account_opening_form_id'))
				result['account_opening_form_id'] = self._context.get('account_opening_form_id')[0]
			else:
				# print("jhgggppp")
				result['account_opening_form_id'] = self._context.get('active_id')
		if not result.get('pricelist_price_change_id') and self._context.get('active_model')=='od.pricelist.price.change':
			if self._context.get('pricelist_price_change_id'):
				result['pricelist_price_change_id'] = self._context.get('pricelist_price_change_id')[0]
			else:
				result['pricelist_price_change_id'] = self._context.get('active_id')
		# print (result)
		return result

	def button_approve(self):
		# print("jhhhhhhhhhhhh")
		approval_password_id = self.sudo().env.ref('orchid_somfy_ksa_v16.od_approval_password')
		# print("lkkkkkkkkkk",self.password,approval_password,approval_password_id.value)
		if self.password == approval_password_id.value:
			if self.account_opening_form_id:
				self.account_opening_form_id.button_approve()
			if self.pricelist_price_change_id:
				self.pricelist_price_change_id.button_approve()
		else:
			raise UserError(_("Wrong Password!!"))


