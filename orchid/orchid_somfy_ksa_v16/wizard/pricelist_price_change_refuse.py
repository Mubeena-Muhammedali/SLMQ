from odoo import fields, models,_,api
from odoo.exceptions import UserError

class OrchidPricelistPriceChangeRefuse(models.TransientModel):
	_name = "od.pricelist.price.change.refuse"
	_description="Pricelist Price Change Refuse"

	pricelist_price_change_id = fields.Many2one('od.pricelist.price.change', string="Price Change")
	reason =fields.Text(string="Reason")
	account_opening_form_id = fields.Many2one('od.account.opening.form', string="Account Opening Form")
	password = fields.Char(string="Password")
	is_manager = fields.Boolean(string="Is a manager?")


	@api.model
	def default_get(self, fields):
		result = super(OrchidPricelistPriceChangeRefuse, self).default_get(fields)
		# print("jhgggggffffff",self._context)
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
		if self.env.user.has_group('sales_team.group_sale_manager'):
			result['is_manager'] = True
			approval_password_id = self.sudo().env.ref('orchid_somfy_ksa_v16.od_approval_password')
			result['password'] = approval_password_id.value
		# print (result)
		return result

	def action_refuse(self):
		# print("jhhhhhhhhhhhh")
		# approval_password_id = self.sudo().env.ref('orchid_somfy_ksa_v16.od_approval_password')
		# if self.password == approval_password_id.value:
		if self.account_opening_form_id:
			return self.account_opening_form_id.button_refuse(reason=self.reason)
		if self.pricelist_price_change_id:
			return self.pricelist_price_change_id.button_refuse(reason=self.reason)
		# else:
			# raise UserError(_("Wrong Password!!"))
		
