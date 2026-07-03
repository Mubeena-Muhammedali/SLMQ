 # -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime,timedelta
from odoo.exceptions import AccessError, UserError, ValidationError
from itertools import groupby
from odoo.tools import float_compare, date_utils, email_split, email_re

class AccountOpeningForm(models.Model):
	_name = "od.account.opening.form"
	_inherit = ['mail.thread']
	_description="Account Opening Form"

	state = fields.Selection([('draft','Draft'),('submit','Submitted'),('pre_approve','Pre-Approved'),('approve','Approved'),('gm_approve','Approved'),('refuse','Refused')],default="draft")
	refuse_reason = fields.Text(string="Refuse Reason")
	partner_id = fields.Many2one('res.partner', string="Customer")
	def get_form_url(self):
		action = self.env.ref('orchid_somfy_ksa_v16.action_od_account_opening_form')
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
		template_id = self.env.ref('orchid_somfy_ksa_v16.account_opening_form_notification_template')
		generate=self.env['mail.template'].browse(template_id.id)
		ctx  = self.env.context.copy()
		recipients = []
		# recipients.append('jack.moussa@somfy.com')
		if isinstance(recipient_email, list):
			recipients.extend(recipient_email)
		else:
			recipients.append(recipient_email)
		recipients = list(filter(None,recipients))
		cc_recipients=[]
		for cc in cc_email:
			cc_recipients.append(cc)
		cc_recipients = list(filter(None,cc_recipients))
		today_date = fields.date.today().strftime('%d/%m/%Y')
		ctx['name'] = 'Account Opening Form Notification- ' + today_date
		ctx['email_to'] = ','.join(recipients)
		ctx['email_cc'] = ','.join(cc_recipients)
		ctx['subject'] = 'Account Opening Form Notification'	
		ctx['company_id'] = self.env.company
		# ctx['content'] = "An Account opening form for "+self.partner+" has been submitted"
		ctx['content'] = content
		# ctx['recipient_name'] = 'Jack Moussa'
		ctx['recipient_name'] = recipient_name
		generate.sudo().with_context(ctx).send_mail(self.id,force_send=True)
		return True

	def button_submit(self):
		pricelist_id = self.env['product.pricelist'].search([('od_account_form_id','=',self.id)])
		if not pricelist_id:
			raise UserError(_('Please Define Pricelist!!'))
		elif pricelist_id and not pricelist_id.item_ids:		
			raise UserError(_('Please Define Pricelist Lines!!'))
		if self.initiated_user_id.has_group('orchid_somfy_ksa_v16.od_group_account_opening_form_approve_user'):
			# in case of samer, jack
			bu_manager_group_id = self.env.ref('orchid_somfy_ksa_v16.od_group_bu_manager_approve_user')
			bu_manager_id = bu_manager_group_id.users
			if not bu_manager_id:
				raise UserError(_("Please set Country Manager!!"))
			bu_manager_id = bu_manager_id[0]
			recipient_email = bu_manager_id.login
			recipient_name = bu_manager_id.name
		else:
			# if not self.initiated_user_id.od_reporting_manger_id:
			# 	raise UserError(_('Please set Reporting Manager for user %s ')%(self.initiated_user_id.name))
			# samer
			country_manager_group_id = self.env.ref('orchid_somfy_ksa_v16.od_group_account_opening_form_approve_user')
			country_manager_id = country_manager_group_id.users
			if not country_manager_id:
				raise UserError(_("Please set Country Manager!!"))
			country_manager_id = country_manager_id[0]
			recipient_email = country_manager_id.login
			recipient_name = country_manager_id.name
		content = "An Account opening form for "+self.partner+" has been submitted by "+self.initiated_user_id.name
		cc_email=[]
		self.send_email_notification(recipient_email, recipient_name,cc_email, content)
		self.state='submit'

	def button_refuse(self, reason):
		if self.env.user.id==self.initiated_user_id.id:
			raise UserError(_("You are not allowed to perform this operation !!!"))
		self.refuse_reason = reason
		recipient_email = self.initiated_user_id.login
		recipient_name = self.initiated_user_id.name
		content = "The Account opening form "+self.name+" for "+self.partner+" has been refused. Note: "+str(reason)
		cc_email=[]
		self.send_email_notification(recipient_email, recipient_name,cc_email, content)
		self.state='refuse'

	def button_reset_to_draft(self):
		self.state='draft'

	def button_pre_approve(self):
		if self.initiated_user_id.has_group('orchid_somfy_ksa_v16.od_group_account_opening_form_approve_user'):
			self.button_approve()
		else:
			recipient_email = []
			for user_id in self.env.ref('orchid_somfy_ksa_v16.od_group_account_opening_form_approve_user').users:
				if not user_id.partner_id.email:
					raise UserError(_("No email defined in partner master for the user '%s' ")%(user_id.name))
				recipient_email.append(user_id.partner_id.email)

		recipient_name = "All"
		content = "An Account opening form for "+self.partner+" has been verified and pre-approved by "+self.initiated_user_id.od_reporting_manger_id.name
		cc_email=[]
		self.send_email_notification(recipient_email, recipient_name,cc_email, content)
		self.state='pre_approve'
		# if partner_id:
		# 	domain = [('id', 'in', partner_id.ids)]
		# 	action = {
		# 		'name': _('Partner'),
		# 		'type': 'ir.actions.act_window',
		# 		'res_model': 'res.partner',
		# 		'view_type': 'form',
		# 		'view_mode': 'form',
		# 		'res_id':partner_id.id,
		# 	}
		# 	return action

	def button_approve(self):
		# create partner
		# rebate_id = self.env['orchid.volume.rebate'].search([('od_account_form_id','=',self.id)])
		# pricelist_id = self.env['product.pricelist'].search([('od_account_form_id','=',self.id)])
		# vals={
		# 'name':self.partner,
		# 'street':self.building,
		# 'street2':self.street+","+self.land_mark if self.land_mark else self.street,
		# 'city':self.district,
		# 'zip':self.zip,
		# 'state_id':self.state_id.id,
		# 'country_id':self.country_id.id,
		# 'vat':self.trn,
		# 'phone':self.phone,
		# 'email':self.email,
		# 'website':self.website,
		# 'property_product_pricelist':pricelist_id and pricelist_id.id,
		# 'od_rebate_id':rebate_id and rebate_id.id,
		# 'od_lne_buss_id':self.line_of_business_id and self.line_of_business_id.id,
		# 'od_distr_chanel_id':self.distribution_channel_id and self.distribution_channel_id.id,
		# 'od_account_form_id':self.id,
		# 'customer_rank':1,
		# 'company_type':'company'
		# }
		# partner_id = self.env['res.partner'].create(vals)
		# recipient_user_id = self.env['res.users'].search([('od_final_code','=','final')])
		# if not recipient_user_id:
		# 	raise UserError(_("No user found with code 'final' "))
		# # recipient_email = 'jack.moussa@somfy.com'
		# # recipient_name = 'Jack Moussa'
		# if not recipient_user_id.partner_id.email:
		# 	raise UserError(_("No email defined in partner master for the user '%s' ")%(recipient_user_id.name))
		# recipient_email = recipient_user_id.partner_id.email
		# recipient_name = recipient_user_id.partner_id.name
		recipient_email = []
		for user_id in self.env.ref('orchid_somfy_ksa_v16.od_group_bu_manager_approve_user').users:
			if not user_id.partner_id.email:
				raise UserError(_("No email defined in partner master for the user '%s' ")%(user_id.name))
			recipient_email.append(user_id.partner_id.email)
		recipient_name = "All"
		content = "An Account opening form for "+self.partner+" has been verified and submitted for approval by "+self.env.user.name
		cc_email=[]
		self.send_email_notification(recipient_email, recipient_name,cc_email, content)
		self.state='approve'
		# if partner_id:
		# 	domain = [('id', 'in', partner_id.ids)]
		# 	action = {
		# 		'name': _('Partner'),
		# 		'type': 'ir.actions.act_window',
		# 		'res_model': 'res.partner',
		# 		'view_type': 'form',
		# 		'view_mode': 'form',
		# 		'res_id':partner_id.id,
		# 	}
		# 	return action

	def button_gm_approve(self):
		if self.env.user.id==self.initiated_user_id.id:
			raise UserError(_("You are not allowed to perform this operation !!!"))
		# create partner
		rebate_id = self.env['orchid.volume.rebate'].search([('od_account_form_id','=',self.id)])
		pricelist_id = self.env['product.pricelist'].search([('od_account_form_id','=',self.id)])
		vals={
		'name':self.partner,
		'street':self.building,
		'street2':self.street+","+self.land_mark if self.land_mark else self.street,
		'city':self.district,
		'zip':self.zip,
		'state_id':self.state_id.id,
		'country_id':self.country_id.id,
		'vat':self.trn,
		'phone':self.phone,
		'email':self.email,
		'website':self.website,
		'property_product_pricelist':pricelist_id and pricelist_id.id,
		'od_rebate_id':rebate_id and rebate_id.id,
		'od_lne_buss_id':self.line_of_business_id and self.line_of_business_id.id,
		'od_distr_chanel_id':self.distribution_channel_id and self.distribution_channel_id.id,
		'od_account_form_id':self.id,
		'customer_rank':1,
		'company_type':'company',
		'od_m_segment':self.m_segment,
		'user_id':self.initiated_user_id and self.initiated_user_id.id,
		'property_payment_term_id':self.payment_term_id and self.payment_term_id.id,
		'is_company':True,
		}
		if self.country_id.code == 'SA':
			vals['od_ksa_partner'] = True
		partner_id = self.env['res.partner'].create(vals)
		recipient_email = self.initiated_user_id.login
		recipient_name = self.initiated_user_id.name
		cc_email = [self.initiated_user_id.od_reporting_manger_id.login,'zia.urrahman@somfy.com']
		content = "The Account opening form for "+self.partner+" has been approved"
		self.send_email_notification(recipient_email, recipient_name,cc_email, content)
		self.state='gm_approve'
		if partner_id:
			self.partner_id = partner_id.id
			for pr in pricelist_id:
				pr.partner_id = partner_id.id
			for vr in rebate_id:
				vr.partner_id = partner_id.id
				
			domain = [('id', 'in', partner_id.ids)]
			action = {
				'name': _('Partner'),
				'type': 'ir.actions.act_window',
				'res_model': 'res.partner',
				'view_type': 'form',
				'view_mode': 'form',
				'res_id':partner_id.id,
			}
			return action

	def expiry_email_notification(self):
		today_date=fields.date.today()
		documents=self.search([])
		for doc in documents:
			email_date=doc.expiry_date-timedelta(days=10)
			if today_date==email_date:
				recipient_email = doc.initiated_user_id.login
				recipient_name = doc.initiated_user_id.name
				cc_email = []
				content = "Your document "+doc.name+" is going to expire on "+str(doc.expiry_date)
				doc.send_email_notification(recipient_email, recipient_name,cc_email, content)
		
	def create_pricelist(self):
		pricelist_id = self.env['product.pricelist'].search([('od_account_form_id','=',self.id)])
		action = self.env["ir.actions.actions"]._for_xml_id("product.product_pricelist_action2")
		if len(pricelist_id) == 1:
			form_view = [(self.env.ref('product.product_pricelist_view').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
			action['res_id'] = pricelist_id.id
		else:
			form_view = [(self.env.ref('product.product_pricelist_view').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
		
		if len(self) == 1:
			context={
				'default_od_account_form_id':self.id,
			}
		action['context'] = context
		return action

	def create_volume_rebate(self):
		pricelist_id = self.env['orchid.volume.rebate'].search([('od_account_form_id','=',self.id)])
		action = self.env["ir.actions.actions"]._for_xml_id("orchid_somfy_ksa_v16.action_orchid_volume_rebate")
		if len(pricelist_id) == 1:
			form_view = [(self.env.ref('orchid_somfy_ksa_v16.orchid_volume_rebate_form_view').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
			action['res_id'] = pricelist_id.id
		else:
			form_view = [(self.env.ref('orchid_somfy_ksa_v16.orchid_volume_rebate_form_view').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
		
		if len(self) == 1:
			context={
				'default_od_account_form_id':self.id,
			}
		action['context'] = context
		return action
	# company_data

	#company Information
	name = fields.Char(string="Form No.")
	initiated_user_id = fields.Many2one('res.users', string="Initiated Sales Person", required=True, tracking=True, default=lambda self:self.env.user)
	date = fields.Date(string="Date", tracking=True, default=fields.Date.context_today)
	business_unit = fields.Selection([('GCC-B2K','GCC-B2K'),('GCC-UQO','GCC-UQO'),('GCC-KSA','GCC-KSA')], string="Business Unit", tracking=True)
	partner = fields.Char(string="Partner Name", required=True, tracking=True)
	building = fields.Char(string="Building Name", required=True, tracking=True)
	street = fields.Char(string="Street Name", required=True, tracking=True)
	zip = fields.Char(string="Post Box No.", required=True, tracking=True)
	district = fields.Char(string="District", tracking=True)
 
	country_id = fields.Many2one('res.country', string="Country", required=True, tracking=True)
	# country_id = fields.Many2one('res.country', string="Country", required=True, tracking=True)
	state_id = fields.Many2one('res.country.state', string="State", required=True, tracking=True)

	land_mark = fields.Char(string="Nearest LandMark", tracking=True)
	phone = fields.Char(string="Telephone No", required=True, tracking=True)
	fax = fields.Char(string="Fax No", tracking=True)
	email = fields.Char(string="Email", required=True, tracking=True)
	website = fields.Char(string="Website", tracking=True)

	@api.onchange('date')
	def onchange_date(self):
		for form in self:
			if form.date:
				if form.date<fields.date.today():
					raise UserError(_('Date should not be less than today.'))
	@api.model
	def create(self,vals):
		result = super(AccountOpeningForm, self).create(vals)
		code_name = 'od.account.opening.form'+str(result.country_id.code)
		sequence_id = self.sudo().env['ir.sequence'].search([('code','=',code_name)])
		if sequence_id:
			result.name = self.sudo().env['ir.sequence'].next_by_code(code_name)
		else:
			seq_vals = {
			'name':"Account Opening Form "+str(result.country_id.name),
			'code':code_name,
			'prefix':str(result.country_id.code)+str("/%(year)s/"),
			'padding':4,
			}
			sequence_id = self.sudo().env['ir.sequence'].create(seq_vals)
			result.name = self.sudo().env['ir.sequence'].next_by_code(code_name)

		return result

	
	#Legal Status
	business_entity_type = fields.Selection([('Propnetorship','Propnetorship'),('Partnership','Partnership'),('Limited Liability Co (LLC)','Limited Liability Co (LLC)'),('Public Joint Stock Co (PJSC)','Public Joint Stock Co (PJSC)')], string="Business Entity Type", tracking=True, required=True)
	ct_license_no = fields.Char(string="Commercial/Trade License No", tracking=True, required=True)
	ct_license_date = fields.Date(string="Commercial/Trade License Expiry Date", tracking=True, required=True)
	license_issuing_authority = fields.Char(string="License Issuing Authority", tracking=True, required=True)
	commerce_reg_no = fields.Char(string="Chamber of Commerce Reg No", tracking=True, required=True)
	commerce_date = fields.Date(string="Chamber of Commerce Expiry Date", tracking=True, required=True)
	owner = fields.Char(string="Name of Owner", tracking=True, required=True)
	owner_country_id = fields.Many2one('res.country', string="Owner Nationality", tracking=True, required=True)
	sponsor = fields.Char(string="Name of Sponsor", tracking=True, required=True)
	sponsor_country_id = fields.Many2one('res.country', string="Sponsor Nationality", tracking=True, required=True)
	trn = fields.Char(string="TRN", tracking=True, required=True)
	commercial_reg = fields.Binary(string="Commercial Registration Certificate", required=True)
	vat_reg = fields.Binary(string="VAT Registration Certificate", required=True)
	expiry_date=fields.Date(string="Expiry Date",required=True,tracking=True)



	# procurement&shipping process
	ordering_type = fields.Selection([('Purchase Order','Purchase Order'),('Pro forma Confirmation','Pro forma Confirmation'),('Pro Confirmation','Pro forma Confirmation')],string="Ordering Type")
	inco_terms = fields.Selection([('Ex Works','Ex Works'),('FOB','FOB'),('CFR','CFR'),('DDP','DDP')],string="Incoterms", required=True)
	shipping_building = fields.Char(string="Building Name", required=True, tracking=True)
	shipping_street = fields.Char(string="Street Name", required=True, tracking=True)
	shipping_zip = fields.Char(string="Post Box No.", required=True, tracking=True)
	shipping_district = fields.Char(string="District", tracking=True, required=True)
	shipping_state_id = fields.Many2one('res.country.state', string="State", required=True, tracking=True)
	shipping_country_id = fields.Many2one('res.country', string="Country", required=True, tracking=True)
	shipping_land_mark = fields.Char(string="Nearest LandMark", tracking=True, required=True)
	shipping_phone = fields.Char(string="Telephone No", required=True, tracking=True,)
	order_confirm_partner_id = fields.Char(string="Person Authorised to  order/confirm Prov Inv", tracking=True)
	order_receive_partner_id = fields.Char(string="Person Authorised to  receive delivery", tracking=True)

	# Business Model& Financial data
	line_of_business_id = fields.Many2one('orchid.line.of.business', string="Line of Business", tracking=True, required=True)
	distribution_channel_id = fields.Many2one('orchid.distribution.channel', string="Distribution Channel", tracking=True, required=True, ondelete='restrict')
	manufacturing_assembly = fields.Selection([('Yes','Yes'),('No','No')], string="Manufacturing/Assembly", tracking=True, required=True, ondelete='restrict')
	branches = fields.Selection([('Yes','Yes'),('No','No')], string="Branches", tracking=True, required=True)
	m_segment = fields.Selection([('ICC','ICC'),('IWC','IWC'),('REA','REA'),('REC','REC'),('CBS','CBS'),('OTH','OTH'),('ESP','ESP')], string="Market Segment", tracking=True, required=True)
	no_emp = fields.Integer(string="Total No. of Employees")
	no_management_staff = fields.Integer(string="No. of Management staff")
	turnover = fields.Float(string="Turnover Declaration(€)")
	expected_turnover = fields.Float(string="Potential/Expected Turnover Declaration with Somfy")
	projects =fields.Char(string="Major Projects Handled, if any", tracking=True)
	bank_ids = fields.One2many('od.account.opening.form.bank.line','form_id', string="Banks")
	vendor_ids = fields.One2many('od.account.opening.form.vendor.line','form_id', string="Vendors")
	customer_ids = fields.One2many('od.account.opening.form.customer.line','form_id', string="Customers")
	# cash = fields.Selection([('advance','Cash in Advance'),('cod','Cash on Delivery'),('current','Current Dated Cheque'),('30','30 Days post Dated Cheque'),('60','60 Days post Dated Cheque'),('90','90 Days post Dated Cheque')], string="Cash", tracking=True, required=True)
	# cheque = fields.Selection([('cash','Cash against Document'),('cod','Cash on Delivery'),('60','L/C 60 Days from Inv/Spt'),('90','90 Days from Inv/Spt'),('120','120 Days from Inv/Spt')], string="Cheque", tracking=True, required=True)
	payment_term_id=fields.Many2one('account.payment.term', string="Payment Terms")
	document_trade = fields.Selection([('0_days','0 Days'),('30','30 Days'),('60','60 Days'),('90','90 Days'),('120','120 Days')], string="Documents & Trade Finance", tracking=True, required=True)
	open_credit = fields.Float(string="Open Credit (Transfer on Due Date)")
	remittance_details = fields.Text(string="Remittance Account Details")



class Pricelist(models.Model):
	_inherit = 'product.pricelist'

	od_account_form_id = fields.Many2one('od.account.opening.form', string="Partner Form")

	def write(self, values):
		if self._context.get('active_model') == 'od.account.opening.form':
			if self.od_account_form_id.state != 'draft':
				raise UserError(_('You cannot edit this record!!!'))
		return super(Pricelist, self).write(values)

	@api.model
	def create(self, values):
		# print("acttttttttt",self._context)
		if self._context.get('active_model') == 'od.account.opening.form':
			od_account_form_id = self.env['od.account.opening.form'].search([('id','=',self._context.get('default_od_account_form_id'))])
			if od_account_form_id.state != 'draft':
				raise UserError(_('You cannot create this record!!!'))
		return super(Pricelist, self).create(values)

class Partner(models.Model):
	_inherit = 'res.partner'

	od_account_form_id = fields.Many2one('od.account.opening.form', string="Partner Form")

class VolumeRebate(models.Model):
	_inherit = 'orchid.volume.rebate'

	od_account_form_id = fields.Many2one('od.account.opening.form', string="Partner Form")

	def write(self, values):
		# print("acttttttttt",self._context)
		if self._context.get('active_model') == 'od.account.opening.form':
			if self.od_account_form_id.state != 'draft':
				raise UserError(_('You cannot edit this record!!!'))
		return super(VolumeRebate, self).write(values)

	@api.model
	def create(self, values):
		# print("acttttttttt",self._context)
		if self._context.get('active_model') == 'od.account.opening.form':
			od_account_form_id = self.env['od.account.opening.form'].search([('id','=',self._context.get('default_od_account_form_id'))])
			if od_account_form_id.state != 'draft':
				raise UserError(_('You cannot create this record!!!'))
		return super(VolumeRebate, self).create(values)


class AccountOpeningFormBank(models.Model):
	_name = "od.account.opening.form.bank.line"
	# _inherit = ['mail.thread']
	_description="Account Opening Form Bank Details"

	name= fields.Char(string="Bank Name", required=True)
	acc_no= fields.Char(string="Account No", required=True)
	branch= fields.Char(string="Bank Branch", required=True)
	country_id= fields.Many2one('res.country', string="Country", required=True)
	address= fields.Text(string="Address", required=True)
	form_id = fields.Many2one('od.account.opening.form', string="Accounting Form", ondelete='cascade')

class AccountOpeningFormVendor(models.Model):
	_name = "od.account.opening.form.vendor.line"
	# _inherit = ['mail.thread']
	_description="Account Opening Form Vendor Details"
	name= fields.Char(string="Vendor", required=True)
	phone= fields.Char(string="Phone", required=True)
	form_id = fields.Many2one('od.account.opening.form', string="Accounting Form", ondelete='cascade')



class AccountOpeningFormCustomer(models.Model):
	_name = "od.account.opening.form.customer.line"
	# _inherit = ['mail.thread']
	_description="Account Opening Form Customer Details"

	name= fields.Char(string="Customer", required=True)
	phone= fields.Char(string="Phone", required=True)
	form_id = fields.Many2one('od.account.opening.form', string="Accounting Form", ondelete='cascade')

