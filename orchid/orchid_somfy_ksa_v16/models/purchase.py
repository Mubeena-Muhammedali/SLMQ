# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo.exceptions import UserError
from odoo.addons.purchase.models.purchase import PurchaseOrder as Purchase

class ProductSupplierinfo(models.Model):
	_inherit = "product.supplierinfo"
	currency_id = fields.Many2one(
		'res.currency', 'Currency',
		default=1,
		required=True)

	@api.onchange('partner_id')
	def _onchange_partner_id(self):
		self.currency_id = self.partner_id.property_purchase_currency_id.id or 1

class PurchaseOrderLine(models.Model):
	_inherit = 'purchase.order.line'

	def _prepare_account_move_line(self, move=False):
		self.ensure_one()
		res = super()._prepare_account_move_line()
		# conver price unit to company currency since all invoices should be made in company currency
		if self.order_id.od_currency_rate>0:
			sar_price = self.price_unit*self.order_id.od_currency_rate
		else:
			sar_price = self.currency_id._convert(self.price_unit,self.company_id.currency_id,self.company_id, fields.Date.today())
		res.update({
			'price_unit': sar_price,
		})
		return res
	
				
# Modification in Purchase Order
class PurchaseOrder(models.Model):
	_inherit='purchase.order'

	od_non_inventroy = fields.Boolean(string="Non Inventory", tracking=True)
	od_non_trade_inventory = fields.Boolean(string="Non Trade Inventory", tracking=True)
	currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=Purchase.READONLY_STATES,
		default=1)
	od_currency_rate = fields.Float(string="Exchange Rate", digits=(12, 6), tracking=True)

	@api.onchange('partner_id', 'company_id')
	def onchange_partner_id(self):
		# Ensures all properties and fiscal positions
		# are taken with the company of the order
		# if not defined, with_company doesn't change anything.
		self = self.with_company(self.company_id)
		if not self.partner_id:
			self.fiscal_position_id = False
			self.currency_id = 1
		else:
			self.fiscal_position_id = self.env['account.fiscal.position']._get_fiscal_position(self.partner_id)
			self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
			self.currency_id = self.partner_id.property_purchase_currency_id.id or 1
		return {}


	@api.model
	def create(self, vals):
		if vals['od_non_inventroy']:
			number = self.env['ir.sequence'].next_by_code('od.noninvetory.purchase.order')
			vals['name'] = number
		if vals['od_non_trade_inventory']:
			number = self.env['ir.sequence'].next_by_code('od.nontradeinvetory.purchase.order')
			vals['name'] = number
		res = super(PurchaseOrder, self).create(vals)
		if res.od_non_trade_inventory:
			res.od_onchange_od_non_trade_inventory()
		return res

	@api.onchange('od_non_trade_inventory')
	def od_onchange_od_non_trade_inventory(self):
		for po in self:
			if po.od_non_trade_inventory:
				# assigning non trade operation type
				po.picking_type_id=26

	def get_purchase_url(self):
		if self.state in ('purchase,done'):
			action = self.env.ref('purchase.purchase_form_action')
		else:
			action = self.env.ref('purchase.purchase_rfq')
		form_id = self.id
		url_link = "%s/?db=%s#id=%s&action=%s&view_type=form" % (
			self.env['ir.config_parameter'].get_param('web.base.url'),
			 self.env.cr.dbname,
			 form_id,
			 action.id  or False,
			 )
		return url_link


	def od_purchase_notification(self):
		# user = self.env.uid
		template_id = self.env.ref('orchid_somfy_ksa_v16.purchase_notification_template')
		generate=self.env['mail.template'].browse(template_id.id)
		ctx  = self.env.context.copy()
		recipients = []
		condition= False

		# if self.state=='to approve':
		# if self.od_non_inventroy:
		# 	condition=True
		# 	recipients.append('sathyajith.menon@somfy.com')
		# 	recipient_name = 'Sathyajith Menon'
			
		# if self.state in ('purchase','done'):
		if (not self.od_non_inventroy) and (self.partner_id.id != 111):
			# recipients.append('sharmine.dizon@somfy.com')
			# recipient_name = 'Sharmin Dizon'
			condition = True
			recipient_user_id = self.env['res.users'].search([('od_final_code','=','pur_gm')])
			if not recipient_user_id:
				raise UserError(_("No user found with code 'pur_gm' "))
			if not recipient_user_id.partner_id.email:
				raise UserError(_("No email defined in partner master for the user '%s' ")%(recipient_user_id.name))
			recipient_email = recipient_user_id.partner_id.email
			recipient_name = recipient_user_id.partner_id.name
			recipients.append(recipient_email)
			# recipients.append('jack.moussa@somfy.com')
			# recipient_name = 'Jack Moussa'
		recipients = list(filter(None,recipients))

		ctx['name'] = 'Purchase Order Notification'
		ctx['email_to'] = ','.join(recipients)
		ctx['email_cc'] = ''
		ctx['subject'] = 'Purchase Order - '+str(self.name)	

		if condition:

			if self.state =='to approve':
				ctx['content'] = 'A request for quotation '+str(self.name) +' from SOMFY SAUDI ARABIA Co. L.L.C. has been made.'
			if self.state in ('purchase','done'):
				ctx['content'] = 'A request for quotation '+str(self.name) +' from SOMFY SAUDI ARABIA Co. L.L.C. has been confirmed.'
				recipients = []
				recipients.append('sharmin.dizon@somfy.com')
				recipient_name = 'Sharmin Dizon'
				recipients = list(filter(None,recipients))
				ctx['email_to'] = ','.join(recipients)
			ctx['recipient_name'] = recipient_name
			generate.sudo().with_context(ctx).send_mail(self.id,force_send=True)

	def _approval_allowed(self):
		# print("hereeeedddddddddddddddddddddddddddddddd")
		"""Returns whether the order qualifies to be approved by the current user"""
		self.ensure_one()
		# return (
		#     self.company_id.po_double_validation == 'one_step'
		#     or (self.company_id.po_double_validation == 'two_step'
		#         and self.amount_total < self.env.company.currency_id._convert(
		#             self.company_id.po_double_validation_amount, self.currency_id, self.company_id,
		#             self.date_order or fields.Date.today()))
		#     or self.user_has_groups('purchase.group_purchase_manager'))
		# print("")
		condition =False
		condition = False
		if self.od_non_inventroy:
			condition=True
		if (not self.od_non_inventroy) and (self.partner_id.id != 111):
			condition=True
		print("conditionnnnnn",condition)
		print("bbb",((self.company_id.po_double_validation == 'one_step'
									or (self.company_id.po_double_validation == 'two_step'
										and self.amount_total < self.env.company.currency_id._convert(
											self.company_id.po_double_validation_amount, self.currency_id, self.company_id,
											self.date_order or fields.Date.today())))
						and self.user_has_groups('base.group_erp_manager')))
		return (
			((self.company_id.po_double_validation == 'one_step'
									or (self.company_id.po_double_validation == 'two_step'
										and self.amount_total < self.env.company.currency_id._convert(
											self.company_id.po_double_validation_amount, self.currency_id, self.company_id,
											self.date_order or fields.Date.today())))
						and self.user_has_groups('base.group_erp_manager')) or (not condition) or self.user_has_groups('base.group_erp_manager'))


	def button_confirm(self):
		# print("ffffffffffffffffff")
		res=super(PurchaseOrder,self).button_confirm()
		if not self.origin and self.state in ('to approve',):
			if (not self.od_non_inventroy) and (self.partner_id.id != 111):
				self.od_purchase_notification()
		for line in self.order_line:
			line.sudo().product_id.product_tmpl_id.od_get_euro_cost()
		return res

	def button_approve(self, force=False):
		res=super(PurchaseOrder,self).button_approve()
		if not self.origin and self.state in ('purchase','to approve','done'):
			if (not self.od_non_inventroy) and (self.partner_id.id != 111):
				self.od_purchase_notification()
		return res

	def _prepare_invoice(self):
		"""
		to pass customised values.
		"""
		self.ensure_one()
		res = super()._prepare_invoice()
		res.update({
			'currency_id':self.company_id.currency_id.id,#all invoices should be in company currency
			})
		return res

