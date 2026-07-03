from odoo import api, fields, Command,models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta,datetime
from odoo.tools import (
	date_utils,
	email_re,
	email_split,
	float_compare,
	float_is_zero,
	format_amount,
	format_date,
	formatLang,
	frozendict,
	get_lang,
	is_html_empty,
	sql
)
from dateutil.relativedelta import relativedelta
from odoo.tools import float_repr
import base64
from odoo.addons.web.controllers.utils import clean_action



class AccountInvoice(models.Model):
	_inherit = "account.move"

	od_revenue_type = fields.Selection([('sale_service','Sales Invoice-Services'),('sale_product','Sales Invoice-Products'),
										('nominal_sale','Nominal Sales'),('purchase_service','Purchase Invoice-Services'),
										('itl','Inter Location Stock Transfer')
										], string="Revenue Type", help="for vat report")
	# od_revenue_type = fields.Selection([('sale_service', 'Sales Invoice-Services'),('sale_product', 'Road'),('air', 'Air'),('express', 'Express')], string='Transportation')
	od_gross_weight = fields.Float(string='Gross Weight')
	od_no_of_packages = fields.Char(string='No.of Packages')
	od_transportation = fields.Selection([('sea', 'Sea'),('road', 'Road'),('air', 'Air'),('express', 'Express')], string='Transportation',default='sea')
	od_packing_list_no = fields.Char(string="Delivery note No.")
	od_packing_type = fields.Char(string="Packing Type")
	od_packing_qty = fields.Char(string="Packing Qty")
	# od_warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
	od_destination = fields.Char(string="Destination")
	# od_be_ref_no = fields.Char(string="B/E Ref No.")
	od_be_ref_no = fields.Text(string="B/E Ref No.")
	od_customs_bill = fields.Selection([('import', 'Import'),('temporary_exit', 'Temporary Exit'),('export', 'Export'),('re_export', 'Import for Re-Export'),
										('free_zone', 'Freezone Internal Transfer'),('fze', 'FZE Bill of Entry')], string='Customs Bill')
	od_cbm_vol = fields.Float(string="Volume CBM",digits=(12, 12))
	od_forwarder = fields.Char(string="Forwarder")
	od_gbw_ref_no = fields.Char(string="Warehouse order no.")
	od_cos_entry_id = fields.Many2one('account.move', string="Cost of Sales Entry", copy=False)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	od_exchange_rate=fields.Float(string="Exchange Rate", digits=(12, 6), help="Company currency to foreign currency rate", compute="od_compute_exchange_rate", store=True)
	# od_amount_untaxed = fields.Monetary(string='Local Untaxed Amount', store=True, readonly=True, compute='od_local_amounts', digits=(12, 4))
	# od_amount_tax = fields.Monetary(string='Local Taxes', store=True, readonly=True, compute='od_local_amounts')
	# od_amount_total = fields.Monetary(string='Local Total', store=True, readonly=True, compute='od_local_amounts')
	od_transaction_type = fields.Selection([('Transfer', 'Transfer'),('STD', 'STD'),('Marketing', 'Marketing'),('Return', 'Return'),('Office Use', 'Office Use'),('Quality', 'Quality'),('Warranty', 'Warranty'),('In House', 'In House'),('Loyalty','Loyalty'),('Service','Service')], string='Transaction Type')
	od_stamp = fields.Boolean(string="Stamp & Sign")
	od_contact_person_id = fields.Many2one('res.partner', string="Contact Person")
	od_local_transportation_id = fields.Many2one('od.local.transport.charge.master', string="Delivery Location", tracking=True)

	od_expert_prgm_inv = fields.Boolean(string="Expert program invoice", default=False)
	od_cost_journal_id = fields.Many2one('account.move', string="Extra cos entry", copy=False)

	@api.depends('amount_total_signed', 'amount_tax_signed', 'l10n_sa_confirmation_datetime', 'company_id', 'company_id.vat')
	def _compute_qr_code_str(self):
		""" Generate the qr code for Saudi e-invoicing. Specs are available at the following link at page 23
		https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Documents/20210528_ZATCA_Electronic_Invoice_Security_Features_Implementation_Standards_vShared.pdf
		"""
		def get_qr_encoding(tag, field):
			company_name_byte_array = field.encode()
			company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
			company_name_length_encoding = len(company_name_byte_array).to_bytes(length=1, byteorder='big')
			return company_name_tag_encoding + company_name_length_encoding + company_name_byte_array

		for record in self:
			qr_code_str = ''
			if record.l10n_sa_confirmation_datetime and record.company_id.vat:
				seller_name_enc = get_qr_encoding(1, record.company_id.display_name)
				company_vat_enc = get_qr_encoding(2, record.company_id.vat)
				time_sa = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), record.l10n_sa_confirmation_datetime)
				timestamp_enc = get_qr_encoding(3, time_sa.isoformat())
				invoice_total_enc = get_qr_encoding(4, float_repr(abs(record.amount_total_signed), 2))
				total_vat_enc = get_qr_encoding(5, float_repr(abs(record.amount_tax_signed), 2))

				str_to_encode = seller_name_enc + company_vat_enc + timestamp_enc + invoice_total_enc + total_vat_enc
				qr_code_str = base64.b64encode(str_to_encode).decode()
			record.l10n_sa_qr_code_str = qr_code_str
			print("qrrrrrrrrrrrrrrrrrr",qr_code_str)
			# print(s)


	def button_update_custom_duty_line(self):
		for record in self:
			source_orders = self.line_ids.sale_line_ids.order_id
			if (not source_orders.od_service) and (record.od_transaction_type not in ('Marketing','Warranty','Office Use','In House')):
				line_sum=0
				line_sum_cbm=0
				price_unit=0
				custom_price_unit=0
				line_sum_custom=0

				custom_product = self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id
				delivery_product = self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin').id
				for line in record.invoice_line_ids.filtered(lambda r:r.product_id.id not in (custom_product,delivery_product) and r.product_id.detailed_type!='service'):
					# price_subtotal = (line.price_unit * (1 - (line.discount / 100.0)))*(line.product_uom_qty+line.od_free_qty+line.od_adjustment_qty)
					price_subtotal = line.price_subtotal
					line_sum +=price_subtotal
					country_code = line.product_id.orchid_country_id.code
					if country_code!='SA':
						line_sum_custom+=price_subtotal
					date = fields.Date.context_today(self)
					rate_id = self.env['orchid.cbm.rate'].search([('name','<=',date)],limit=1, order='name desc')
					if not rate_id:
						raise UserError(_("CBM Rate is not set!!!"))
					cbm = line.product_id.od_cbm_vol*(line.quantity+line.od_free_qty+line.od_adjustment_qty)*rate_id.rate
					line_sum_cbm +=cbm
				price_unit=0.05*(line_sum)
				custom_price_unit=0.05*(line_sum_custom)
				custom_duty_line_id=record.invoice_line_ids.filtered(lambda r:r.product_id.id==custom_product)
				delivery_admin_line_id=record.invoice_line_ids.filtered(lambda r:r.product_id.id==delivery_product)
				if custom_duty_line_id:
					custom_duty_line_id.price_unit=custom_price_unit
					if not(custom_price_unit > 0):
						custom_duty_line_id.unlink()
				if delivery_admin_line_id:
					delivery_admin_line_id.price_unit=line_sum_cbm
				if source_orders.od_delivery_charge:
					record.button_update_local_transportation_line()
				# if not delivery_admin_line_id:
				# 	record.od_create_delivery_admin_line()
				# if not custom_duty_line_id and custom_price_unit>0:
				# 	record.od_create_custom_duty_line()

	def od_create_custom_duty_line(self):
		for record in self:
			line_sum=0
			price_unit=0
			for line in record.invoice_line_ids.filtered(lambda r:r.product_id.detailed_type!='service' and r.product_id.orchid_country_id.code!='SA'):
				print("kovvvvvv")
				# price_subtotal = (line.price_unit * (1 - (line.discount / 100.0)))*(line.product_uom_qty+line.od_free_qty+line.od_adjustment_qty)
				price_subtotal = line.price_subtotal
				line_sum +=price_subtotal
			price_unit=0.05*(line_sum)
			line_vals={
			'sequence':500,
			'move_id':record.id,
			'display_type':'product',
			'product_id':self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id,
			'product_uom_id':1,
			'quantity':1,
			'price_unit':price_unit,
			# 'tax_id':[(6,0,[])]
			}
			if price_unit>0:
				record.env['account.move.line'].create(line_vals)

	def od_create_delivery_admin_line(self):
		for record in self:
			line_sum=0
			price_unit=0
			for line in record.invoice_line_ids.filtered(lambda r:r.product_id.detailed_type!='service'):
				date = fields.Date.context_today(self)
				rate_id = self.env['orchid.cbm.rate'].search([('name','<=',date)],limit=1, order='name desc')
				if not rate_id:
					raise UserError(_("CBM Rate is not set!!!"))
				cbm = line.product_id.od_cbm_vol*(line.quantity+line.od_free_qty+line.od_adjustment_qty)*rate_id.rate
				line_sum +=cbm
			price_unit=(line_sum)
			line_vals={
			'sequence':501,
			'move_id':record.id,
			'display_type':'product',
			'product_id':self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin').id,
			'product_uom_id':1,
			'quantity':1,
			'price_unit':price_unit,
			# 'tax_id':[(6,0,[])]
			}
			record.env['account.move.line'].create(line_vals)

	def button_update_local_transportation_line(self):
		for record in self:
			source_orders = self.line_ids.sale_line_ids.order_id
			if (not source_orders.od_service) and (source_orders.od_delivery_charge) and (record.od_transaction_type not in ('Marketing','Warranty','Office Use','In House')):
				cost=total_cbm=total_cost=0
				cost = record.od_local_transportation_id.cost
				total_cbm = record.od_cbm_vol
				total_cost = total_cbm*cost
				if total_cbm<1:
					total_cost = cost*1
				transportation_product = self.env.ref('orchid_somfy_ksa_v16.od_product_local_transportation').id
				
				transportation_line_id=record.invoice_line_ids.filtered(lambda r:r.product_id.id==transportation_product)
				if transportation_line_id:
					transportation_line_id.price_unit=total_cost
				if not transportation_line_id:
					record.od_create_local_transportation_line()

	def od_create_local_transportation_line(self):
		for record in self:
			cost=total_cbm=total_cost=0
			cost = record.od_local_transportation_id.cost
			total_cbm = record.od_cbm_vol
			# print("hhhhhhhhhhhh",total_cbm,cost)
			# print("hhhhhhhhhhhh",type(total_cbm),type(cost))
			total_cost = total_cbm*cost
			if total_cbm<1:
				total_cost = cost*1
			line_vals={
			'sequence':500,
			'move_id':record.id,
			'product_id':self.env.ref('orchid_somfy_ksa_v16.od_product_local_transportation').id,
			'product_uom_id':1,
			'quantity':1,
			'price_unit':total_cost,
			'display_type':'product'
			# 'tax_id':[(6,0,[])]
			}
			record.env['account.move.line'].create(line_vals)
				
	def od_create_extra_cos(self):
		source_orders = self.line_ids.sale_line_ids.order_id
		if self.move_type=='out_refund' and self.reversed_entry_id:
			source_orders = self.reversed_entry_id.line_ids.sale_line_ids.order_id
		print("source_orders",source_orders,self.state)
			
		if source_orders and not(source_orders.od_route_id.id==self.env.ref('stock_dropshipping.route_drop_shipping').id):
			if self.state=='posted':
				print('kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk',self.name)
				if self.od_cost_journal_id:
					self.od_cost_journal_id.button_draft()
					print("herdddddd")
					# self.od_cost_journal_id.unlink()
				# create the entry
				entry_vals={
				'ref':"Extra cos entry to correct the cost for extra qtys",
				'date':self.invoice_date,
				'journal_id':31,
				'move_type':'entry',
				}
				line_ls=[]
				for line in self.invoice_line_ids.filtered(lambda x:x.product_id.detailed_type!='service'):
					print("hereeeeeeeeee")
					price_unit=0
					cost_line_ids =self.line_ids.filtered(lambda x:x.product_id.id==line.product_id.id and x.account_id.account_type=='expense_direct_cost')
					for mvl in cost_line_ids:
						# print("herdddssssssssssss")
						mvl.od_cost = (line.quantity+line.od_free_qty+line.od_adjustment_qty)*abs(mvl.price_unit)
						mvl.od_free_qty = line.od_free_qty
						mvl.od_adjustment_qty = line.od_adjustment_qty
						price_unit=abs(mvl.price_unit)
						line.od_per_cost = mvl.price_unit
					print("cost_line_ids",cost_line_ids,line.product_id.name)
					if not cost_line_ids or price_unit==0:
						print("nooooooooooooooooooooooo")
						if line.sale_line_ids:
							for sl in line.sale_line_ids:
								print("sllll",sl.move_ids)
								stck_move_ids = sl.move_ids.filtered(lambda x:x.picking_type_id.code=='outgoing')
								if self.move_type=='out_refund':
									stck_move_ids = sl.move_ids.filtered(lambda x:x.picking_type_id.code=='incoming')
								for sm in stck_move_ids:
									print("kkkookkk")
									outbound_acc_id = line.product_id.categ_id.property_stock_account_output_categ_id and line.product_id.categ_id.property_stock_account_output_categ_id.id
									stk_mv_id = self.env['account.move'].search([('stock_move_id','=',sm.id)])
									print("jhggg",outbound_acc_id,stk_mv_id)
									for sml in stk_mv_id.line_ids.filtered(lambda x:x.account_id.id==outbound_acc_id):
										print("smlll",sml)
										price_unit=abs(sml.debit/sml.quantity)
										if self.move_type=='out_refund':
											price_unit=abs(sml.credit/sml.quantity)

					print("priceeee*********************",price_unit)
					# print(s)
					if (line.od_free_qty+line.od_adjustment_qty)>0:
						print("justttttt",price_unit)
						debit_account_id = (line.product_id.property_account_expense_id and line.product_id.property_account_expense_id.id) or (line.product_id.categ_id.property_account_expense_categ_id and line.product_id.categ_id.property_account_expense_categ_id.id)
						credit_account_id = (line.product_id.categ_id.property_stock_account_output_categ_id and line.product_id.categ_id.property_stock_account_output_categ_id.id)
						debit_line_vals ={
						'product_id':line.product_id.id,
						'name':line.name,
						'price_unit':price_unit*-1,
						'debit':(line.od_free_qty+line.od_adjustment_qty)*abs(price_unit),
						'credit':0,
						'account_id':debit_account_id,
						'quantity':(line.od_free_qty+line.od_adjustment_qty),
						'od_parent_move_id':self.id,
						}
						credit_line_vals ={
						'product_id':line.product_id.id,
						'name':line.name,
						'price_unit':price_unit,
						'credit':(line.od_free_qty+line.od_adjustment_qty)*abs(price_unit),
						'debit':0,
						'account_id':credit_account_id,
						'quantity':(line.od_free_qty+line.od_adjustment_qty),
						'od_parent_move_id':self.id,
						}
						if self.move_type=='out_refund':
							debit_line_vals['account_id']=credit_account_id
							debit_line_vals['price_unit']=price_unit*-1
							credit_line_vals['account_id']=debit_account_id
							credit_line_vals['price_unit']=price_unit
						line_ls.append((0,0,debit_line_vals))
						line_ls.append((0,0,credit_line_vals))
					line.od_cost = (line.quantity+line.od_free_qty+line.od_adjustment_qty)*abs(price_unit)
					line.od_per_cost = abs(price_unit)


				print("entrr",entry_vals)
				# print(s)
				if line_ls:
					entry_vals['line_ids']=line_ls
					if self.od_cost_journal_id:
						self.od_cost_journal_id.date = self.invoice_date
						self.od_cost_journal_id.line_ids.unlink()
						self.od_cost_journal_id.line_ids = line_ls
					else:
						self.od_cost_journal_id = self.env['account.move'].create(entry_vals).id
					self.od_cost_journal_id.action_post()
				print("finisssss")

	
	def _build_credit_warning_message(self, record, updated_credit):
		''' Build the warning message that will be displayed in a yellow banner on top of the current record
			if the partner exceeds a credit limit (set on the company or the partner itself).
			:param record:                  The record where the warning will appear (Invoice, Sales Order...).
			:param updated_credit (float):  The partner's updated credit limit including the current record.
			:return (str):                  The warning message to be showed.
		'''
		partner_id = record.partner_id.commercial_partner_id
		if not partner_id.credit_limit or updated_credit <= partner_id.credit_limit and not partner_id.od_over_due:
			return ''
		# msg = _('%s has reached its Credit Limit of : %s\nTotal amount due ',
		# 		partner_id.name,
		# 		formatLang(self.env, partner_id.credit_limit, currency_obj=record.company_id.currency_id))
		msg=""
		euro_currency_id = record.env['res.currency'].browse(1)
		updated_credit_euro=0
		if record.currency_id.id ==1:
			updated_credit_euro = record.partner_id.commercial_partner_id.od_credit_euro + (record.amount_total)

		# print("khjjjjjjjjjjjjjjjj",updated_credit > partner_id.credit,updated_credit , partner_id.credit)
		if partner_id.credit_limit and updated_credit > partner_id.credit_limit:
			msg = _('%s has reached its Credit Limit of : %s\nTotal amount due ',
					partner_id.name,
					formatLang(self.env, partner_id.od_coverage_value, currency_obj=euro_currency_id))
		if partner_id.credit_limit and updated_credit > partner_id.credit and updated_credit > partner_id.credit_limit:
			msg += _('(including this document) ')
		# msg += ': %s' % formatLang(self.env, updated_credit, currency_obj=record.company_id.currency_id)
			msg += ': %s' % formatLang(self.env, updated_credit_euro, currency_obj=euro_currency_id)
		if record.partner_id.od_over_due:
			if msg:
				msg+= _('\n %s has over due invoices', partner_id.name)
			else:
				msg = _('%s has over due invoices', partner_id.name)

		return msg
		
	@api.depends('needed_terms')
	def _compute_invoice_date_due(self):
		res = super(AccountInvoice, self)._compute_invoice_date_due()
		for move in self:
			move.partner_id and move.partner_id.od_get_overdue()
		return res

	@api.onchange('partner_id')
	def od_user_id_change(self):
		for move in self:
			if move.partner_id:
				# move.invoice_user_id = move.partner_id.od_user_id and move.partner_id.od_user_id.id or self.env.user.id
				move.invoice_user_id = move.partner_id.user_id and move.partner_id.user_id.id or self.env.user.id
				for contact_id in move.partner_id.child_ids:
					move.od_contact_person_id = contact_id.id


	@api.depends('date','currency_id','invoice_date')
	def od_compute_exchange_rate(self):
		for record in self:
			print("restttttttttttttttt")
			date = record.date
			if record.currency_id.id == self.company_id.currency_id.id:
				record.od_exchange_rate = 1
			else:
				exchange_rate_id = self.env['res.currency.rate'].search([('currency_id','=',record.currency_id.id),('name','<=',date)],limit=1, order='name desc')
				print("hgftreeeeeeeee",exchange_rate_id)
				if exchange_rate_id:
					record.od_exchange_rate = exchange_rate_id.inverse_company_rate
				
	@api.onchange('invoice_line_ids')
	def total_gross_weight(self):
		gross=0
		for line in self.invoice_line_ids:
			gross=gross+line.od_gross_weight
		self.od_gross_weight=gross

	# def action_post(self):
	# 	# EXTENDS 'account' to update the COS Entry
	# 	res = super().action_post()
	# 	if self.move_type not in ['in_invoice','in_refund']:
	# 		if self.move_type == 'out_invoice':
	# 			where_qry=" WHERE mv_s.invoice_origin = '"+str(self.invoice_origin)+"'  AND mv.move_type = 'in_invoice' AND mv.state <> 'draft' "
	# 			qry = ('''SELECT mv.id FROM account_move mv
	# 				  LEFT JOIN purchase_order po ON po.name = mv.invoice_origin
	# 				  LEFT JOIN sale_order so ON so.name = po.origin
	# 				  LEFT JOIN account_move mv_s ON mv_s.invoice_origin = so.name '''
	# 				  + where_qry +''' ''')

			

	# 		# if self.type == 'out_refund':
	# 		# 	qry = (''' SELECT vend_cr_mv.id
	# 		# 				from account_move vend_cr_mv
	# 		# 				left join account_invoice cust_inv on cust_inv.number='%s' and cust_inv.type='out_invoice'
	# 		# 				left join account_invoice vend_inv on vend_inv.move_id=cust_inv.od_cos_entry_id and vend_inv.type='in_invoice'
	# 		# 				left join account_invoice cust_cr on cust_cr.origin=cust_inv.number and cust_cr.type='out_refund'
	# 		# 				left join account_invoice vend_cr  on vend_cr.refund_invoice_id=vend_inv.id and vend_cr.type='in_refund'
	# 		# 				left join account_invoice_line cust_cr_line on cust_cr_line.invoice_id=cust_cr.id
	# 		# 				left join account_move_line aml on aml.move_id=vend_cr.move_id
	# 		# 				where aml.product_id=cust_cr_line.product_id 
	# 		# 				-- and aml.quantity = cust_cr_line.quantity+cust_cr_line.od_free_qty 
	# 		# 				and aml.quantity = cust_cr_line.quantity+cust_cr_line.od_free_qty +cust_cr_line.od_adjustment_qty
	# 		# 				and vend_cr_mv.id=aml.move_id
	# 		# 				group  by vend_cr_mv.id
	# 		# 			''')%(self.origin)
	# 		self.env.cr.execute(qry)
	# 		result = self.env.cr.fetchall()
	# 		result = [z[0] for z in result]
	# 		if result:
	# 			self.od_cos_entry_id = result[0]
	# 		else :
	# 			if self.move_type=='out_invoice':
	# 				if self.journal_id.id not in (14,15):
	# 					raise UserError(_('You cannot confirm the vendor bill inorder to confirm this invoice.'))
	# 		# ##### mapping invoice origin to label of move line#####
	# 		# journal_ref_qry = (''' UPDATE account_move_line mvl set name=ai.origin   
	# 		# 						from account_move mv ,account_invoice ai 
	# 		# 						where mv.id=mvl.move_id and ai.number=mv.name 
	# 		# 						and  mvl.account_id= 2 
	# 		# 						and mv.journal_id=1 
	# 		# 						and ai.id=%s
	# 		# 						''')% (self.id)
	# 		# self.env.cr.execute(journal_ref_qry)

	# 	#to link cos of sales entry to sale order invoices/credit note in case the po invoice/credit note is cancelled after validating the customer invoices/credit note
	# 	if self.move_type == 'in_invoice':
	# 		where_qry=" WHERE po.name = '"+str(self.invoice_origin)+"'  AND mv.move_type = 'out_invoice' AND mv.state <> 'draft' "
	# 		po_qry = ('''SELECT mv.id FROM account_move mv
	# 			  LEFT JOIN sale_order so ON so.name = mv.invoice_origin
	# 			  LEFT JOIN purchase_order po ON po.origin = so.name
	# 			  '''+ where_qry +''' ''')
	# 		self.env.cr.execute(po_qry)
	# 		po_result = self.env.cr.fetchall()
	# 		po_result = [z[0] for z in po_result]
	# 		if po_result:
	# 			if len(po_result)==1:
	# 				update_where_qry=" WHERE mv.id= "+str(po_result[0])
	# 			if len(po_result)>1:
	# 				update_where_qry=" WHERE mv.id in "+str(tuple(po_result))
	# 			update_cos = ('''Update account_move mv set od_cos_entry_id=%s'''+update_where_qry+''' ''')%(self.move_id.id)
	# 			self.env.cr.execute(update_cos)

	# 	# if self.type == 'in_refund':
	# 	# 	vndr_qry = (''' SELECT cust_cr.id
	# 	# 				from account_invoice cust_cr
	# 	# 				left join account_invoice vend_inv on vend_inv.number='%s' and vend_inv.type='in_invoice'
	# 	# 				left join account_invoice cust_inv on vend_inv.move_id=cust_inv.od_cos_entry_id and cust_inv.type='out_invoice'
	# 	# 				left join account_invoice vend_cr  on vend_cr.refund_invoice_id=vend_inv.id and vend_cr.type='in_refund'
	# 	# 				left join account_invoice_line cust_cr_line on cust_cr_line.invoice_id=cust_cr.id
	# 	# 				left join account_move_line aml on aml.move_id=vend_cr.move_id
	# 	# 				where aml.product_id=cust_cr_line.product_id 
	# 	# 				-- and aml.quantity = cust_cr_line.quantity+cust_cr_line.od_free_qty 
	# 	# 				and aml.quantity = cust_cr_line.quantity+cust_cr_line.od_free_qty +cust_cr_line.od_adjustment_qty
	# 	# 				and cust_cr.origin=cust_inv.number and cust_cr.type='out_refund' and  cust_cr.state<>'draft'
	# 	# 			''')%(self.origin)
	# 	# 	self.env.cr.execute(vndr_qry)
	# 	# 	cr_result = self.env.cr.fetchall()
	# 	# 	cr_result = [z[0] for z in cr_result]
	# 	# 	if cr_result:
	# 	# 		if len(cr_result)==1:
	# 	# 			update_where_qry=" WHERE ai.id= "+str(cr_result[0])
	# 	# 		if len(cr_result)>1:
	# 	# 			update_where_qry=" WHERE ai.id in "+str(tuple(cr_result))
	# 	# 		update_cos = ('''Update account_invoice ai set od_cos_entry_id=%s'''+update_where_qry+''' ''')%(self.move_id.id)
	# 	# 		self.env.cr.execute(update_cos)

	# 	return res

	# @api.depends('od_exchange_rate','amount_total','date_invoice')
	# def od_local_amounts(self):
	# 	for record in self:
	# 		if record.od_exchange_rate:
	# 			exchange_rate = self.od_exchange_rate
	# 			record.od_amount_untaxed = record.amount_untaxed / exchange_rate
	# 			record.od_amount_tax = record.amount_tax / exchange_rate
	# 			record.od_amount_total = record.amount_total / exchange_rate

	# 			#creating or checking the exchange rate with given rate and invoice date
	# 			if self.type == 'out_invoice':
	# 				date = self.date_invoice if self.date_invoice else datetime.today().date()
	# 				currency_rate_id = self.env['res.currency.rate'].search([('currency_id','=',self.currency_id.id),('name','=',date)])
	# 				if not currency_rate_id:
	# 					vals={'rate':exchange_rate,'name':date,'currency_id':self.currency_id.id}
	# 					self.env['res.currency.rate'].create(vals)



	#to link cos of sales entry to sale order invoice
	# origin is not set?
	def action_post(self):
		res = False
		for move in self:
			if move.journal_id.code == 'JVF' and not move.env.user.has_group('orchid_somfy_ksa_v16.od_group_journal_finalization_approve_user'):
				raise UserError(_("You are not allowed to post this journal voucher finalization entry!!"))
			if move.expense_sheet_id:
				res = super(AccountInvoice, move).action_post()
				continue

			if not move.asset_id and move.partner_id and move.partner_id.od_lic_expiry_date:
				today_date = fields.Date.today()
				if move.partner_id.od_lic_expiry_date < today_date:
					raise UserError(_("License for this customer has been expired!!"))
			if move.date and move.company_id.fiscalyear_lock_date:
				od_lock_date_month = move.company_id.fiscalyear_lock_date.month
				last_month = move.date.month - 1
				print("lasttttmonthh", last_month, od_lock_date_month)
				if last_month == 0:
					last_month = 12
				# if last_month != od_lock_date_month:#new change dec2 2025
				# 	raise UserError(_("Previous month is not closed!!! The last lock date updated is %s")%(move.company_id.fiscalyear_lock_date))
				# print(s)
			for invl in move.invoice_line_ids:
				if invl.product_id:
					if not invl.product_id.property_account_income_id:
						raise UserError(_("Please set the Income Account for the product '%s' to continue!! ") % (invl.product_id.name))
					if not invl.product_id.property_account_expense_id:
						raise UserError(_("Please set the Expense Account for the product '%s' to continue!! ") % (invl.product_id.name))

			# check if exchange rate available for current date
			date = move.date
			if move.currency_id.id == move.company_id.currency_id.id:
				move.od_exchange_rate = 1
			else:
				exchange_rate_id = move.env['res.currency.rate'].search([('currency_id', '=', move.currency_id.id), ('name', '=', date)], limit=1, order='name desc')
				if exchange_rate_id:
					move.od_exchange_rate = exchange_rate_id.inverse_company_rate
				else:
					raise UserError(_("Please set exchange rate for the date '%s' ") % (date))

			res = super(AccountInvoice, move).action_post()
			move.od_create_extra_cos()
			if move.move_type in ('out_invoice', 'out_refund'):
				qry = """UPDATE account_move_line set od_parent_move_id=%s WHERE move_id=%s""" % (move.id, move.id)
				move._cr.execute(qry)
			source_orders = move.line_ids.sale_line_ids.order_id
			if source_orders and source_orders.od_route_id.id == move.env.ref('stock_dropshipping.route_drop_shipping').id:
				if move.move_type in ['out_invoice', 'out_refund']:
					if move.move_type == 'out_invoice':
						where_qry = " WHERE ais.invoice_origin = '" + str(move.invoice_origin) + "'  AND ai.move_type = 'in_invoice' AND ai.state <> 'draft' "
						qry = ('''SELECT ai.id FROM account_move ai
						  LEFT JOIN purchase_order po ON po.name = ai.invoice_origin
						  LEFT JOIN sale_order so ON so.name = po.origin
						  LEFT JOIN account_move ais ON ais.invoice_origin = so.name '''
						  + where_qry +''' ''')

				

				if move.move_type == 'out_refund':
					qry = (''' SELECT vend_cr_mv.id
								from account_move vend_cr_mv
								left join account_move cust_inv on cust_inv.id=%s and cust_inv.move_type='out_invoice'
								left join account_move vend_inv on vend_inv.id=cust_inv.od_cos_entry_id and vend_inv.move_type='in_invoice'
								left join account_move cust_cr on cust_cr.reversed_entry_id=cust_inv.id and cust_cr.move_type='out_refund'
								left join account_move vend_cr  on vend_cr.reversed_entry_id=vend_inv.id and vend_cr.move_type='in_refund'
								left join account_move_line cust_cr_line on cust_cr_line.move_id=cust_cr.id
								left join account_move_line aml on aml.move_id=vend_cr.id
								where aml.product_id=cust_cr_line.product_id 
								-- and aml.quantity = cust_cr_line.quantity+cust_cr_line.od_free_qty 
								and aml.quantity = cust_cr_line.quantity+cust_cr_line.od_free_qty +cust_cr_line.od_adjustment_qty
								and vend_cr_mv.id=aml.move_id
								group  by vend_cr_mv.id
							''')%(self.reversed_entry_id.id)
				move.env.cr.execute(qry)
				result = self.env.cr.fetchall()
				result = [z[0] for z in result]
				if result:
					move.od_cos_entry_id = result[0]
				else :
					if move.move_type == 'out_invoice':
						if move.journal_id.id not in (14,15):#tax inv and loyalty inv jrnls
								raise UserError("Please create or confirm the Vendor/Credit Note Bill")
				##### mapping invoice origin to label of move line#####
				# journal_ref_qry = (''' UPDATE account_move_line mvl set name=ai.origin   
				# 						from account_move mv ,account_invoice ai 
				# 						where mv.id=mvl.move_id and ai.number=mv.name 
				# 						and  mvl.account_id= 2 
				# 						and mv.journal_id=1 
				# 						and ai.id=%s
				# 						''')% (self.id)
				# self.env.cr.execute(journal_ref_qry)

			#to link cos of sales entry to sale order invoices/credit note in case the po invoice/credit note is cancelled after validating the customer invoices/credit note
			if move.move_type == 'in_invoice':
				where_qry = " WHERE po.name = '" + str(move.invoice_origin) + "'  AND ais.move_type = 'out_invoice' AND ais.state <> 'draft' "
				po_qry = ('''SELECT ais.id FROM account_move ais
					  LEFT JOIN sale_order so ON so.name = ais.invoice_origin
					  LEFT JOIN purchase_order po ON po.origin = so.name
					  ''' + where_qry + ''' ''')
				move.env.cr.execute(po_qry)
				po_result = move.env.cr.fetchall()
				po_result = [z[0] for z in po_result]
				if po_result:
					if len(po_result) == 1:
						update_where_qry = " WHERE ai.id= " + str(po_result[0])
					if len(po_result) > 1:
						update_where_qry = " WHERE ai.id in " + str(tuple(po_result))
					update_cos = ('''Update account_move ai set od_cos_entry_id=%s''' + update_where_qry + ''' ''') % (move.id)
					move.env.cr.execute(update_cos)

			if move.move_type == 'in_refund':
				vndr_qry = (''' SELECT cust_cr.id
							from account_move cust_cr
							left join account_move vend_inv on vend_inv.name='%s' and vend_inv.move_type='in_invoice'
							left join account_move cust_inv on vend_inv.id=cust_inv.od_cos_entry_id and cust_inv.move_type='out_invoice'
							left join account_move vend_cr  on vend_cr.reversed_entry_id=vend_inv.id and vend_cr.move_type='in_refund'
							left join account_move_line cust_cr_line on cust_cr_line.move_id=cust_cr.id
							left join account_move_line aml on aml.move_id=vend_cr.id
							where aml.product_id=cust_cr_line.product_id 
							-- and aml.quantity = cust_cr_line.quantity+cust_cr_line.od_free_qty 
							and aml.quantity = cust_cr_line.quantity+cust_cr_line.od_free_qty +cust_cr_line.od_adjustment_qty
							and cust_cr.invoice_origin=cust_inv.name and cust_cr.move_type='out_refund' and  cust_cr.state<>'draft'
						''') % (move.invoice_origin)
				move.env.cr.execute(vndr_qry)
				cr_result = move.env.cr.fetchall()
				cr_result = [z[0] for z in cr_result]
				if cr_result:
					if len(cr_result) == 1:
						update_where_qry = " WHERE ai.id= " + str(cr_result[0])
					if len(cr_result) > 1:
						update_where_qry = " WHERE ai.id in " + str(tuple(cr_result))
					update_cos = ('''Update account_move ai set od_cos_entry_id=%s''' + update_where_qry + ''' ''') % (move.id)
					move.env.cr.execute(update_cos)
		
		#checking for existing exchange rate
		# if self.move_type == 'out_invoice' and self.od_exchange_rate!=0:
		# 	date = self.date_invoice if self.date_invoice else datetime.today().date()
		# 	currency_rate_id = self.env['res.currency.rate'].search([('currency_id','=',self.currency_id.id),('name','=',date)])
		# 	inv_rate = self.od_exchange_rate
		# 	if currency_rate_id:
		# 		if currency_rate_id.rate != inv_rate:
		# 			msg='An exchange rate of '+str(currency_rate_id.rate)+' has already been created on this date '+str(date)+' !! \n if you want to change the rate, change it in the currency master'
		# 			raise  ValidationError(_(msg))
		return res


class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	od_gross_weight = fields.Float(string='Gross Weight',compute="compute_gross_weight")
	orchid_country_id = fields.Many2one('res.country', string='Country Of Origin')
	od_free_qty=fields.Float(string="Free quantity", digits=dp.get_precision('Product Unit of Measure'),default=0.0)
	od_adjustment_qty=fields.Float(string="Adjustment quantity", digits=dp.get_precision('Product Unit of Measure'),default=0.0)
	od_ttl_qty = fields.Float(string="Total quantity",digits=dp.get_precision('Product Unit of Measure'))
	od_transaction_type = fields.Many2one('od.transaction.type', string="Transaction Type", default=lambda self: self.env['od.transaction.type'].search([('code','=','SALE')], limit=1).id)
	od_cost = fields.Float(string="Cost for full qty")
	od_per_cost = fields.Float(string="Per Cost for full qty")
	od_parent_move_id = fields.Many2one('account.move', string="Parent Move")
	od_margin_reason = fields.Char(string="Reason")

	def open_reconcile_view(self):
		action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_grouped_matching')
		# ids = self._all_reconciled_lines().filtered(lambda l: l.matched_debit_ids or l.matched_credit_ids).ids
		ids = self._reconciled_lines()
		action['domain'] = [('id', 'in', ids)]
		return clean_action(action, self.env)
	

	@api.depends('quantity','od_free_qty','od_adjustment_qty')
	def compute_gross_weight(self):
		for line in self:
			line.od_gross_weight=(line.quantity+line.od_free_qty+line.od_adjustment_qty)*line.product_id.od_ttl_weight
			line.od_ttl_qty = line.quantity + line.od_free_qty + line.od_adjustment_qty

	@api.onchange('product_id')
	def od_onchange_country(self):
		for line in self:
			if line.product_id:
				line.orchid_country_id = line.product_id.orchid_country_id and line.product_id.orchid_country_id.id


	def _prepare_exchange_difference_move_vals(self, amounts_list, company=None, exchange_date=None):
		""" Prepare values to create later the exchange difference journal entry.
		The exchange difference journal entry is there to fix the debit/credit of lines when the journal items are
		fully reconciled in foreign currency.
		:param amounts_list:    A list of dict, one for each aml.
		:param company:         The company in case there is no aml in self.
		:param exchange_date:   Optional date object providing the date to consider for the exchange difference.
		:return:                A python dictionary containing:
			* move_vals:    A dictionary to be passed to the account.move.create method.
			* to_reconcile: A list of tuple <move_line, sequence> in order to perform the reconciliation after the move
							creation.
		"""
		company = self.company_id or company
		if not company:
			return

		journal = company.currency_exchange_journal_id
		expense_exchange_account = company.expense_currency_exchange_account_id
		income_exchange_account = company.income_currency_exchange_account_id
		od_current_date = '2023-04-30'
		od_current_date = datetime.strptime(od_current_date, '%Y-%m-%d').date()
		# print("typeeeeeeeeee",type(exchange_date),type(date.min),od_current_date)
		# print("typeeeeeeeeee",type(company._get_user_fiscal_lock_date() + timedelta(days=1)),type(date.min),type(od_current_date))
		move_vals = {
			'move_type': 'entry',
			'date': max(exchange_date or date.min, company._get_user_fiscal_lock_date() + timedelta(days=1),fields.Datetime.today().date()),
			# 'date': max(exchange_date or date.min, company._get_user_fiscal_lock_date() + timedelta(days=1),od_current_date),
			'journal_id': journal.id,
			'line_ids': [],
			'always_tax_exigible': True,
		}
		to_reconcile = []
		for line, amounts in zip(self, amounts_list):
			move_vals['date'] = max(move_vals['date'], line.date)

			if 'amount_residual' in amounts:
				amount_residual = amounts['amount_residual']
				amount_residual_currency = 0.0
				if line.currency_id == line.company_id.currency_id:
					amount_residual_currency = amount_residual
				amount_residual_to_fix = amount_residual
				if line.company_currency_id.is_zero(amount_residual):
					continue
			elif 'amount_residual_currency' in amounts:
				amount_residual = 0.0
				amount_residual_currency = amounts['amount_residual_currency']
				amount_residual_to_fix = amount_residual_currency
				if line.currency_id.is_zero(amount_residual_currency):
					continue
			else:
				continue

			if amount_residual_to_fix > 0.0:
				exchange_line_account = expense_exchange_account
			else:
				exchange_line_account = income_exchange_account

			sequence = len(move_vals['line_ids'])
			move_vals['line_ids'] += [
				Command.create({
					'name': _('Currency exchange rate difference'),
					'debit': -amount_residual if amount_residual < 0.0 else 0.0,
					'credit': amount_residual if amount_residual > 0.0 else 0.0,
					'amount_currency': -amount_residual_currency,
					'account_id': line.account_id.id,
					'currency_id': line.currency_id.id,
					'partner_id': line.partner_id.id,
					'sequence': sequence,
				}),
				Command.create({
					'name': _('Currency exchange rate difference'),
					'debit': amount_residual if amount_residual > 0.0 else 0.0,
					'credit': -amount_residual if amount_residual < 0.0 else 0.0,
					'amount_currency': amount_residual_currency,
					'account_id': exchange_line_account.id,
					'currency_id': line.currency_id.id,
					'partner_id': line.partner_id.id,
					'sequence': sequence + 1,
				}),
			]
			to_reconcile.append((line, sequence))

		return {'move_vals': move_vals, 'to_reconcile': to_reconcile}
