 # -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime,timedelta
from odoo.exceptions import AccessError, UserError, ValidationError
from itertools import groupby
from odoo.tools import float_compare, date_utils, email_split, email_re
ACCOUNT_DOMAIN = "['&', '&', '&', ('deprecated', '=', False), ('account_type', 'not in', ('asset_receivable','liability_payable','asset_cash','liability_credit_card')), ('company_id', '=', current_company_id), ('is_off_balance', '=', False)]"


class ProductOpeningFormBatch(models.Model):
	_name = "od.product.opening.form.batch"
	_inherit = ['mail.thread']
	_description="Product Opening Form Batch"

	name = fields.Char(string="Name")
	state = fields.Selection([('draft','Draft'),('submit','Submitted'),('approve','Approved')],default='draft', string="State")
	line_ids = fields.One2many('od.product.opening.form.batch.line','batch_id', string="Batch Line")
	date = fields.Date(string="Date")
	user_id = fields.Many2one('res.users', string="User")
	company_id = fields.Many2one('res.company', string="Company", default=lambda self:self.env.user.company_id)

	@api.model
	def create(self,vals):
		vals['name'] = self.sudo().env['ir.sequence'].next_by_code('od.product.opening.form.batch')
		return  super(ProductOpeningFormBatch, self).create(vals)

	def get_form_url(self):
		action = self.env.ref('orchid_somfy_ksa_v16.action_od_product_opening_form_batch')
		form_id = self.id
		url_link = "%s/?db=%s#id=%s&action=%s&view_type=form" % (
			self.env['ir.config_parameter'].get_param('web.base.url'),
			 self.env.cr.dbname,
			 form_id,
			 action.id  or False,
			 )
		return url_link

	def send_email_notification(self, recipient_email, recipient_name,cc_email, content):
		## Get email template
		template_id = self.env.ref('orchid_somfy_ksa_v16.product_opening_form_batch_notification_template')
		generate=self.env['mail.template'].browse(template_id.id)
		ctx  = self.env.context.copy()
		recipients = []
		recipients.append(recipient_email)
		recipients = list(filter(None,recipients))
		cc_recipients=[]
		for cc in cc_email:
			cc_recipients.append(cc)
		cc_recipients = list(filter(None,cc_recipients))
		today_date = fields.date.today().strftime('%d/%m/%Y')
		ctx['name'] = 'Product Opening Form Batch Notification- ' + today_date
		ctx['email_to'] = ','.join(recipients)
		ctx['email_cc'] = ','.join(cc_recipients)
		ctx['subject'] = 'Product Opening Form Batch Notification'	
		ctx['company_id'] = self.env.company
		ctx['content'] = content
		ctx['recipient_name'] = recipient_name
		generate.sudo().with_context(ctx).send_mail(self.id,force_send=True)
		return True



	def button_submit(self):

		# create product opening form
		for line in self.line_ids:
			vals = {
				'date':self.date,
				'user_id':self.user_id.id,
				'company_id':line.company_id.id,
				'product_name':line.product_name,

				'detailed_type':line.detailed_type,
				'categ_id':line.categ_id.id,
				'default_code':line.default_code,
				'orchid_arabic':line.orchid_arabic,
				'od_factory_cost':line.od_factory_cost,
				'od_sale_price':line.od_sale_price,
				'od_cost_price':line.od_cost_price,

				'orchid_group_id':line.orchid_group_id.id,
				'orchid_type_id':line.orchid_type_id.id,
				'orchid_class_id':line.orchid_class_id.id,
				'orchid_country_id':line.orchid_country_id.id,
				'orchid_hscode_id':line.orchid_hscode_id.id,

				'od_com_code':line.od_com_code,
				'od_depth':line.od_depth,
				'od_width':line.od_width,
				'od_height':line.od_height,
				'od_weight':line.od_weight,
				'od_pkg_weight':line.od_pkg_weight,
				'od_ttl_weight':line.od_ttl_weight,
				'od_cbm_vol':line.od_cbm_vol,

				'property_account_income_id':line.property_account_income_id.id,
				'property_account_expense_id':line.property_account_expense_id.id,
				'batch_id':self.id,
			}
			if not line.opening_form_id:
				opening_form_id = self.env['od.product.opening.form'].create(vals)
				line.opening_form_id = opening_form_id.id
			else:
				line.opening_form_id.write(vals)
			line.opening_form_id.button_submit()



		recipient_name = "Sir"
		recipient_email = "srijit.ramachandran@somfy.com"
		cc_email = ""
		content = "A product opening form batch "+ self.name +" has been submitted by "+ self.user_id.name
		self.send_email_notification(recipient_email, recipient_name,cc_email, content)
		self.state='submit'

	def button_reset_to_draft(self):
		# recipient_name = self.user_id.name
		# recipient_email = self.user_id.login
		# cc_email = ""
		# content = "The product opening form "+ self.name +" has been reset to draft"
		# self.send_email_notification(recipient_email, recipient_name,cc_email, content)
		self.state='draft'

	def button_approve(self):
		for line in self.line_ids:
			line.opening_form_id.button_approve()

		if self.user_id.id !=120:
			recipient_name = self.user_id.name
			recipient_email = self.user_id.login
			cc_email = ""
			content = "The product opening form batch "+ self.name +" has been approved"
			self.send_email_notification(recipient_email, recipient_name,cc_email, content)

		self.state='approve'

	def view_product_templates(self):
		template_ids = self.line_ids.mapped('opening_form_id').mapped('product_tmpl_id').ids
		print("juiiiiiiiiiiii",template_ids)
		domain = [('id', 'in', template_ids)]
		action = {
			'name': _('Product Template'),
			'type': 'ir.actions.act_window',
			'res_model': 'product.template',
			'view_type': 'tree',
			'view_mode': 'tree',
			'domain':[('id', 'in', template_ids)],
		}
		return action

class ProductOpeningFormBatchLine(models.Model):
	_name = "od.product.opening.form.batch.line"
	_description = "Product Opening Form Batch Line"

	batch_id = fields.Many2one('od.product.opening.form.batch', string="Batch ID", ondelete="cascade", copy=False)
	opening_form_id = fields.Many2one('od.product.opening.form', string="Product Opening Form")
	
	

	# general
	product_name = fields.Char(string="Product Name")
	orchid_arabic = fields.Char(string='Arabic Name')
	default_code = fields.Char(string="Internal Reference")
	detailed_type = fields.Selection([('product', 'Storable Product'),('consu', 'Consumable'),
		('service', 'Service')],default='product', string="Product Type")
	categ_id = fields.Many2one('product.category', string="product Line")
	company_id = fields.Many2one('res.company', string="Company", default=lambda self:self.env.user.company_id)
	od_factory_cost = fields.Float(string="Factory Cost")
	od_sale_price = fields.Float(string="Sale Price")
	od_cost_price = fields.Float(string="Cost Price Euro")

	# product details
	orchid_group_id =  fields.Many2one('orchid.product.group', string="Group")
	orchid_type_id =  fields.Many2one('orchid.product.type', string='Type')
	orchid_class_id =  fields.Many2one('orchid.product.classification', string='Classification')
	orchid_country_id = fields.Many2one('res.country', string='Country Of Origin')
	orchid_hscode_id = fields.Many2one('orchid.product.hscode', string='HS Code')

	# specification
	od_com_code = fields.Char(string='Commodity Code')
	od_depth = fields.Float(string='Depth(mm)')
	od_width = fields.Float(string='Width(mm)')
	od_height = fields.Float(string='Height(mm)')
	od_weight = fields.Float(string='Weight(kg)')
	od_pkg_weight = fields.Float(string='Packaging Weight')
	od_ttl_weight = fields.Float(string='Total Weight')
	od_cbm_vol = fields.Float(string='CBM',digits=(12, 12))


	# accounting
	property_account_income_id = fields.Many2one('account.account', company_dependent=True,
		string="Income Account",
		domain=ACCOUNT_DOMAIN,
		help="Keep this field empty to use the default value from the product category.")
	property_account_expense_id = fields.Many2one('account.account', company_dependent=True,
		string="Expense Account",
		domain=ACCOUNT_DOMAIN,
		help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")

	


