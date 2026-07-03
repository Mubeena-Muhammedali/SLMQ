from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from collections import OrderedDict
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd
import calendar
from datetime import *

class OrchidSalesRegister(models.TransientModel):
	_name = 'orchid.sale.register.wiz'
	_description = 'Sales Register'
	
	
	from_date = fields.Date(string="Start Date",required=True)	
	to_date = fields.Date(string="End Date",required=True)
	# stock_product = fields.Boolean(string="Without Service Products")
	service_product = fields.Boolean(string="Service Products only")
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	motor_product = fields.Boolean(string="Motor Products Only")
	credit_note = fields.Boolean(string="With Credit Note", default=True)
	warehouse_id = fields.Selection([('global','Global'),('dubai','Dubai'),('france','France')],string="Warehouse",default='global')
	user_id = fields.Many2one('res.users', string="Sales Team", check_company=True)
	factory_price = fields.Boolean(string="Factory Price")
	# exchange_rate = fields.Float(string="Exchange Rate", default=1)
	show_in_euro =  fields.Boolean(string="Show in Euro", default=True)
	exchange_rate_id = fields.Many2one('orchid.budget.rate',string="Excange Rate", check_company=True)
	partner_id = fields.Many2one('res.partner', string="Customer")
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)
	# reverse_rate_id = fields.Many2one('orchid.budget.rate',string="Reverse Excange Rate")
	product_id= fields.Many2one('product.product', string="Product")
	separate_qty = fields.Boolean(string="Separate Qty", default=False)
	transaction_type = fields.Selection([('Transfer', 'Transfer'),('STD', 'STD'),('Marketing', 'Marketing'),('Return', 'Return'),('Office Use', 'Office Use'),('Quality', 'Quality'),('Warranty', 'Warranty'),('In House', 'In House')], string='Transaction Type')
	with_service = fields.Boolean(string="With Service Product", default=False)


	# @api.model
	# def default_get(self, fields):
	# 	res = super(OrchidSalesRegister, self).default_get(fields)
	# 	exchange_rate_id = self.env['orchid.budget.rate'].search([('from_currency_id','=',1),('to_currency_id','=',131)], order="id asc", limit=1)
	# 	# r_from_currenncy_id = exchange_rate_id.to_currency_id.id
	# 	# r_to_currenncy_id = exchange_rate_id.from_currency_id.id
	# 	# r_exchange_rate_id = self.env['orchid.budget.rate'].search([('from_currency_id','=',r_from_currenncy_id),('to_currency_id','=',r_to_currenncy_id)], order="id asc", limit=1)
	# 	values = {
	# 		'exchange_rate_id':exchange_rate_id.id,
	# 		# 'reverse_rate_id':r_exchange_rate_id.id,
	# 	}
	# 	res.update(values)
	# 	return res

	@api.onchange('separate_qty')
	def onchange_filter(self):
		for rec in self:
			if rec.separate_qty:
				rec.service_product = False


	@api.onchange('service_product')
	def onchange_filter1(self):
		for rec in self:
			if rec.service_product:
				rec.separate_qty = False
				rec.with_service = False

	@api.onchange('with_service')
	def onchange_filter2(self):
		for rec in self:
			if rec.with_service:
				rec.service_product = False

	@api.onchange('from_date')
	def last_day_of_month(self):
		if self.from_date:
			any_day=datetime.strptime(str(self.from_date),'%Y-%m-%d')
			next_month = any_day.replace(day=28) + timedelta(days=4)  # this will never fail
			to_date=next_month - timedelta(days=next_month.day)
			to_date=to_date.strftime('%Y-%m-%d')
			self.to_date=to_date

	def get_old_sale_data(self, date_from, date_to, where_qry):
		select_str = """ SELECT 
							ail.id as ail_id,
							ail.od_margin_reason as margin_reason,
							 res.ref as ref,
							 res.od_ban_bp as bp_code,
							 tmpl.default_code as default_code,
							 ru.name as currency,
							 date_part('year',ai.invoice_date) as year,
							 date_part('month',ai.invoice_date) as month,

							 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.price_subtotal) * (-1)
							 ELSE (ail.price_subtotal) END as subtotal,
							 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.debit) * (-1)
							 ELSE (ail.credit) END as sale_sar,

							 cst.amount_currency_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) as cost,
							 cst.cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) as cost_sar,

							 ai.invoice_date as date,
							 ai.name as name,
							
							 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.price_unit) * (-1)
							 ELSE ail.price_unit END as unit_price,

							 res.name as partner,
							 res.od_name_unamed as unnamed,
							 tmpl.name as product,

							 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN cust_in.invoice_origin
							 ELSE ai.invoice_origin END as origin,

							 opg.name as pdt_group,
							 hs.name as hs_code,
							 rc.name as country,
							 -- sw.name as warehouse,
							 trans.name as transaction_type,
							 orchid_product_brand.name as brand,
							 dist_chan.name as distribution_channel,
							 rsp.name as user,
							 ru.id as currency_id,
							 tmpl.id as pdt_id ,
							 lb.name as line_of_bsns,
							 tmpl.od_factory_cost as factory_cost,
							 ai.od_exchange_rate as exch_rate,
							 ai.id as invoice_id,
							 pay.name ->> 'en_US'  as payment_term"""
			
			
		if self.separate_qty:
			select_str += ",CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity * (-1))\
						 ELSE (ail.quantity) END as quantity,\
						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.od_free_qty * (-1))\
						 ELSE (ail.od_free_qty) END as free_qty,\
						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.od_adjustment_qty * (-1))\
						 ELSE (ail.od_adjustment_qty) END as adj_qty"
		else:
			select_str += ",CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) * (-1)\
						 ELSE (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END as quantity"

		# left join
		left_join_str = """ LEFT JOIN account_move_line ail ON ail.move_id = ai.id
						LEFT JOIN res_partner res  ON res.id = ai.partner_id
						LEFT JOIN product_product pp ON pp.id = ail.product_id
						LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
						LEFT JOIN res_currency ru ON ru.id = ai.currency_id
						LEFT JOIN orchid_account_invoice_dropshipping_cost cst ON ail.move_id = cst.inv_id and ail.product_id = cst.product_id 
							
						LEFT JOIN account_move cust_in ON cust_in.id = ai.reversed_entry_id AND ai.move_type = 'out_refund'
						LEFT JOIN orchid_product_group opg ON opg.id = tmpl.orchid_group_id
						LEFT JOIN orchid_product_hscode hs ON hs.id = tmpl.orchid_hscode_id
						LEFT JOIN res_country rc ON rc.id = ail.orchid_country_id
						LEFT JOIN res_users rs ON rs.id = ai.invoice_user_id
						LEFT JOIN res_partner rsp ON rsp.id = rs.partner_id
						LEFT JOIN od_transaction_type trans ON trans.id = ail.od_transaction_type
						LEFT JOIN orchid_product_brand ON orchid_product_brand.id = tmpl.orchid_brand_id
						LEFT JOIN orchid_distribution_channel dist_chan ON res.od_distr_chanel_id = dist_chan.id
						LEFT JOIN orchid_line_of_business lb ON lb.id = res.od_lne_buss_id
						LEFT JOIN account_payment_term pay ON pay.id=ai.invoice_payment_term_id """


		group_by = """  res.ref,
					res.od_ban_bp,
					tmpl.default_code,
					ru.name,
					ai.invoice_date,
					ai.name,
					res.name,
					tmpl.name,
					opg.name,
					ai.invoice_origin,
					cust_in.invoice_origin,
					ai.move_type,
					ail.id,
					ail.quantity,
					ail.od_free_qty,
					ail.od_adjustment_qty,
					-- cst.amount_currency_cost,
					hs.name,
					rc.name,
					trans.name,
					orchid_product_brand.name,
					dist_chan.name,
					tmpl.od_factory_cost,
					rsp.name,
					ru.id,
					tmpl.id,
					lb.name,
					cst.amount_currency_cost,
					ai.od_exchange_rate,
					cst.cost,
					ail.debit,
					ail.credit,
					res.od_name_unamed,
					ai.id ,
					pay.name """

		qry = ("""%s FROM account_move ai
					%s
				  WHERE (ail.display_type='product') AND ai.company_id=%s AND ai.invoice_date BETWEEN '%s' AND '%s' 
				   AND """ + where_qry +"""
				  GROUP BY %s """)%(select_str,left_join_str,self.company_id.id, date_from, date_to,group_by)

		self.env.cr.execute(qry)
		print("old qryyy",qry)
		data_result = self.env.cr.dictfetchall()
		print("hhhh",data_result)
		# if not data_result:
		# 	raise UserError('There is no data to generate')

		old_data_ls = []
		ail_id_ls = []

		for data in data_result:
			if data['ail_id'] not in ail_id_ls:
				ail_id_ls.append(data['ail_id'])
				margin_reason=data['margin_reason']
				sales=data['subtotal'] or 0
				cos =  data['cost'] or 0
				unit_price=data['unit_price']
				date=data['date']
				pca_cos = 0
				pca_cos_euro = 0
				product_segment = ""
				if data['pdt_id']:
					tmpl_id = self.env['product.template'].browse(data['pdt_id'])
					domain = ['&', ('state', 'in', ['purchase', 'done']), ('product_id', 'in', tmpl_id.product_variant_ids.ids)]
					po_line_id = self.env['purchase.order.line'].search(domain, order='id desc',limit=1)
					if po_line_id:
						pca_cos_euro = po_line_id.price_unit * data['quantity']
					pca_cos = tmpl_id.standard_price * data['quantity']
					product_segment =  ",".join(tmpl_id.od_product_segment_id.mapped('name'))
				named = ''
				if data['unnamed']:
					if data['unnamed']=='named':
						named='Named'
					if data['unnamed']=='un_named':
						named='UnNamed'
					if data['unnamed']=='out_of_scope':
						named='Out of Scope'
				if date:
					date =datetime.strptime(str(date),'%Y-%m-%d').strftime('%d-%m-%Y')
				sales_company = data['sale_sar'] or 0
				cos_company = data['cost_sar'] or 0
				factory_cost =factory_cost_sar= 0
				if data['factory_cost']:
					if self.separate_qty:
						factory_cost = data['factory_cost'] * (data['quantity']+data['adj_qty']+data['free_qty'])
					else:
						factory_cost = data['factory_cost'] * data['quantity']
					factory_cost_sar = factory_cost*(data['exch_rate'] or 1)

				if data['date']:
					if str(data['date'])>='2023-01-01' and str(data['date'])<='2023-04-30':
						# print("salesssss",sales)
						cos = cos_company*0.223700
						factory_cost_sar = factory_cost * 4.470273

				currency_rate =  data['exch_rate'] or 1
				if data['currency_id']!=1:
					
					if data['date']:
						if str(data['date'])>='2023-01-01' and str(data['date'])<='2023-04-30':
							# print("salesssss",sales)
							sales = sales*0.223700
							cos = cos*0.223700
							unit_price=unit_price*0.223700
						else:
							# sales=0
							# cos=0
							# unit_price=0
							# convert to euro
							date_str = datetime.strptime(date, '%d-%m-%Y')
							date_str = date_str.strftime('%Y-%m-%d')
							euro_currency_id = self.env['res.currency'].browse(1)
							currency_rate = self.env['res.currency']._get_conversion_rate(
								from_currency=self.company_id.currency_id,
								to_currency=euro_currency_id,
								company=self.company_id,
								date=date_str,
							)
							sales = sales*currency_rate
							cos = cos*currency_rate
							unit_price = unit_price*currency_rate
					else:
						sales=0
						cos=0
						unit_price=0
				margin_per = 0
				if sales:
					margin_per = ((sales - cos)/(sales if sales else 1))*100

						
						
				

				vals ={'Customer Reference':data['ref'],
					   'Customer Code':data['bp_code'],
					   'Product Code':data['default_code'],
					   'Local Currency' : data['currency'],
					   'Year':data['year'],
					   'Month':data['month'],
					   'Quantity':data['quantity'] or 0,
					   
					   'Sales':sales or 0,
					   'COS':cos or 0,
					   # 'Exchange Rate':data['exch_rate'] or 1,
					   'Exchange Rate':currency_rate,
					   'Sales SAR':sales_company or 0,
					   'COS SAR':cos_company or 0,
					   'Invoice Date':date,
					   'Invoice Number':data['name'],
					   'Unit Price':unit_price or 0,
					   'Customer':data['partner'],
					   'Named/Un Named':named,
					   'Product':data['product'].get('en_US') if data['product'] else "",
					   'Sale Order':data['origin'],
					   'Product Family':data['pdt_group'],
					   'HS Code':data['hs_code'],
					   'Country of Origin':data['country'].get('en_US') if data['country'] else '',
					   'Transaction Type':data['transaction_type'],
					   'Brand':data['brand'],
					   'Distribution Channel':data['distribution_channel'],
					   'Product Segment':product_segment,
					   # 'Factory Price':data['factory_cost'] or 0,
					   'Factory Price':factory_cost or 0,
					   'Factory Price SAR':factory_cost_sar,
					   'Sales person':data['user'],
					   'Line of Business': data['line_of_bsns'],
					   'PCA COS SAR':pca_cos,
					   'PCA COS Euro':pca_cos_euro,
					   'Margin%':margin_per,
					   'Margin Control Reason':margin_reason or "",
					   'Payment Terms':data['payment_term'],
					   }
				if self.separate_qty:
					vals.update({'Free Quantity':data['free_qty'] or 0,
								 'Adjustment Quantity':data['adj_qty'] or 0,})
				if self.service_product:
					invoice_id = data['invoice_id']
					invoice = self.env['account.move'].browse(invoice_id)
					# print("pddddddddddd",data['pdt_id'],self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id,self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin').id)
					if data['pdt_id'] and data['pdt_id']==self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty_product_template').id:
						invoice_value = (unit_price*100)/5
						cbm = invoice.od_cbm_vol
						vals.update({'5%':unit_price,'Invoice Value':invoice_value,'Gross Weight':invoice.od_gross_weight,'Dimension':cbm})
					if data['pdt_id'] and data['pdt_id']==self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin_product_template').id:
						# invoice_value = (unit_price*100)/5
						# invoice_id = data['invoice_id']
						# invoice = self.env['account.move'].browse(invoice_id)
						invoice_value = (unit_price/(invoice.od_cbm_vol if invoice.od_cbm_vol else 1))
						cbm = invoice.od_cbm_vol
						vals.update({'Dimension':cbm,'Rate':invoice_value,'Gross Weight':invoice.od_gross_weight})
					
				old_data_ls.append(vals)
		return old_data_ls


	def get_new_sale_data(self, date_from, date_to, where_qry):
		select_str = """ SELECT 
							 ail.id as ail_id,
							 ail.od_margin_reason as margin_reason,
							 res.ref as ref,
							 res.od_ban_bp as bp_code,
							 tmpl.default_code as default_code,
							 ru.name as currency,
							 date_part('year',ai.invoice_date) as year,
							 date_part('month',ai.invoice_date) as month,

							 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.price_subtotal) * (-1)
							 ELSE (ail.price_subtotal) END as subtotal,
							 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.debit) * (-1)
							 ELSE (ail.credit) END as sale_sar,

							 cst.amount_currency_cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) as cost,
							 cst.cost * (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) as cost_sar,

							 ai.invoice_date as date,
							 ai.name as name,
							
							 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.price_unit) * (-1)
							 ELSE ail.price_unit END as unit_price,

							 res.name as partner,
							 res.od_name_unamed as unnamed,
							 tmpl.name as product,

							 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN cust_in.invoice_origin
							 ELSE ai.invoice_origin END as origin,

							 opg.name as pdt_group,
							 hs.name as hs_code,
							 rc.name as country,
							 -- sw.name as warehouse,
							 trans.name as transaction_type,
							 orchid_product_brand.name as brand,
							 dist_chan.name as distribution_channel,
							 rsp.name as user,
							 ru.id as currency_id,
							 tmpl.id as pdt_id ,
							 lb.name as line_of_bsns,
							 tmpl.od_factory_cost as factory_cost,
							 ai.od_exchange_rate as exch_rate,
							 ai.id as invoice_id,
							 pay.name ->> 'en_US' as payment_term"""
			
			
		if self.separate_qty:
			select_str += ",CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity * (-1))\
						 ELSE (ail.quantity) END as quantity,\
						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.od_free_qty * (-1))\
						 ELSE (ail.od_free_qty) END as free_qty,\
						 CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.od_adjustment_qty * (-1))\
						 ELSE (ail.od_adjustment_qty) END as adj_qty"
		else:
			select_str += ",CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) * (-1)\
						 ELSE (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END as quantity"

		# left join
		left_join_str = """ LEFT JOIN account_move_line ail ON ail.move_id = ai.id
						LEFT JOIN res_partner res  ON res.id = ai.partner_id
						LEFT JOIN product_product pp ON pp.id = ail.product_id
						LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
						LEFT JOIN res_currency ru ON ru.id = ai.currency_id
						LEFT JOIN orchid_account_invoice_cost cst ON ail.move_id = cst.inv_id and ail.product_id = cst.product_id 
							
						LEFT JOIN account_move cust_in ON cust_in.id = ai.reversed_entry_id AND ai.move_type = 'out_refund'
						LEFT JOIN orchid_product_group opg ON opg.id = tmpl.orchid_group_id
						LEFT JOIN orchid_product_hscode hs ON hs.id = tmpl.orchid_hscode_id
						LEFT JOIN res_country rc ON rc.id = ail.orchid_country_id
						LEFT JOIN res_users rs ON rs.id = ai.invoice_user_id
						LEFT JOIN res_partner rsp ON rsp.id = rs.partner_id
						LEFT JOIN od_transaction_type trans ON trans.id = ail.od_transaction_type
						LEFT JOIN orchid_product_brand ON orchid_product_brand.id = tmpl.orchid_brand_id
						LEFT JOIN orchid_distribution_channel dist_chan ON res.od_distr_chanel_id = dist_chan.id
						LEFT JOIN orchid_line_of_business lb ON lb.id = res.od_lne_buss_id
						LEFT JOIN account_payment_term pay ON pay.id=ai.invoice_payment_term_id """


		group_by = """  res.ref,
					res.od_ban_bp,
					tmpl.default_code,
					ru.name,
					ai.invoice_date,
					ai.name,
					res.name,
					tmpl.name,
					opg.name,
					ai.invoice_origin,
					cust_in.invoice_origin,
					ai.move_type,
					ail.id,
					ail.quantity,
					ail.od_free_qty,
					ail.od_adjustment_qty,
					-- cst.amount_currency_cost,
					hs.name,
					rc.name,
					trans.name,
					orchid_product_brand.name,
					dist_chan.name,
					tmpl.od_factory_cost,
					rsp.name,
					ru.id,
					tmpl.id,
					lb.name,
					cst.amount_currency_cost,
					ai.od_exchange_rate,
					cst.cost,
					ail.debit,
					ail.credit,
					res.od_name_unamed,
					ai.id ,
					pay.name
					"""

		qry = ("""%s FROM account_move ai
					%s
				  WHERE (ail.display_type='product') AND ai.company_id=%s AND ai.invoice_date BETWEEN '%s' AND '%s' 
				  AND (ai.od_cos_entry_id is null) AND """ + where_qry +"""
				  GROUP BY %s """)%(select_str,left_join_str,self.company_id.id,date_from,date_to,group_by)

		self.env.cr.execute(qry)
		print("new qryyy",qry)
		data_result = self.env.cr.dictfetchall()
		# print("hhhh",data_result)
		# if not data_result:
		# 	raise UserError('There is no data to generate')

		new_data_ls = []
		ail_id_ls = []

		for data in data_result:
			if data['ail_id'] not in ail_id_ls:
				ail_id_ls.append(data['ail_id'])
				margin_reason = data['margin_reason']
				sales=data['subtotal'] or 0
				cos =  data['cost'] or 0
				unit_price=data['unit_price']
				date=data['date']
				pca_cos = 0
				pca_cos_euro = 0
				product_segment=""
				if data['pdt_id']:
					tmpl_id = self.env['product.template'].browse(data['pdt_id'])
					domain = ['&', ('state', 'in', ['purchase', 'done']), ('product_id', 'in', tmpl_id.product_variant_ids.ids)]
					po_line_id = self.env['purchase.order.line'].search(domain, order='id desc',limit=1)
					if po_line_id:
						pca_cos_euro = po_line_id.price_unit * data['quantity']
					pca_cos = tmpl_id.standard_price * data['quantity']
					product_segment =  ",".join(tmpl_id.od_product_segment_id.mapped('name'))
				named = ''
				if data['unnamed']:
					if data['unnamed']=='named':
						named='Named'
					if data['unnamed']=='un_named':
						named='UnNamed'
					if data['unnamed']=='out_of_scope':
						named='Out of Scope'
				if date:
					date =datetime.strptime(str(date),'%Y-%m-%d').strftime('%d-%m-%Y')
				sales_company = data['sale_sar'] or 0
				cos_company = data['cost_sar'] or 0
				factory_cost =factory_cost_sar= 0
				if data['factory_cost']:
					if self.separate_qty:
						factory_cost = data['factory_cost'] * (data['quantity']+data['adj_qty']+data['free_qty'])
					else:
						factory_cost = data['factory_cost'] * data['quantity']
					factory_cost_sar = factory_cost*(data['exch_rate'] or 1)

				if data['date']:
					if str(data['date'])>='2023-01-01' and str(data['date'])<='2023-04-30':
						# print("salesssss",sales)
						cos = cos_company*0.223700
						factory_cost_sar = factory_cost * 4.470273

				currency_rate = data['exch_rate'] or 1
				if data['currency_id']!=1:
					
					if data['date']:
						if str(data['date'])>='2023-01-01' and str(data['date'])<='2023-04-30':
							# print("salesssss",sales)
							sales = sales*0.223700
							cos = cos*0.223700
							unit_price=unit_price*0.223700
						else:
							# sales=0
							# cos=0
							# unit_price=0
							# convert to euro
							# print("dateeeee",date)
							date_str = datetime.strptime(date, '%d-%m-%Y')
							date_str = date_str.strftime('%Y-%m-%d')
							# print("date_str",date_str,type(date_str))
							date_str=date_str
							euro_currency_id = self.env['res.currency'].browse(1)
							currency_rate = self.env['res.currency']._get_conversion_rate(
								from_currency=self.company_id.currency_id,
								to_currency=euro_currency_id,
								company=self.company_id,
								date=date_str,
							)
							sales = sales*currency_rate
							cos = cos*currency_rate
							unit_price = unit_price*currency_rate
					else:
						sales=0
						cos=0
						unit_price=0
				margin_per = 0
				if sales:
					margin_per = ((sales - cos)/(sales if sales else 1))*100
						
						
				
					print(data['brand'],"brrrr")
				vals ={'Customer Reference':data['ref'],
					   'Customer Code':data['bp_code'],
					   'Product Code':data['default_code'],
					   'Local Currency' : data['currency'],
					   'Year':data['year'],
					   'Month':data['month'],
					   'Quantity':data['quantity'] or 0,
					   
					   'Sales':sales or 0,
					   'COS':cos or 0,
					   # 'Exchange Rate':data['exch_rate'] or 1,
					   'Exchange Rate':currency_rate,
					   'Sales SAR':sales_company or 0,
					   'COS SAR':cos_company or 0,
					   'Invoice Date':date,
					   'Invoice Number':data['name'],
					   'Unit Price':unit_price or 0,
					   'Customer':data['partner'],
					   'Named/Un Named':named,
					   'Product':data['product'].get('en_US') if data['product'] else "",
					   'Sale Order':data['origin'],
					   'Product Family':data['pdt_group'],
					   'HS Code':data['hs_code'],
					   'Country of Origin':data['country'].get('en_US') if data['country'] else '',
					   'Transaction Type':data['transaction_type'],
					   'Brand':data['brand'],
					   'Distribution Channel':data['distribution_channel'],
					   'Product Segment':product_segment,
					   # 'Factory Price':data['factory_cost'] or 0,
					   'Factory Price':factory_cost or 0,
					   'Factory Price SAR':factory_cost_sar,
					   'Sales person':data['user'],
					   'Line of Business': data['line_of_bsns'],
					   'PCA COS SAR':pca_cos,
					   'PCA COS Euro':pca_cos_euro,
					   'Margin%':margin_per,
					   'Margin Control Reason':margin_reason or "",
					   'Payment Terms':data['payment_term'],
					   }
				if self.separate_qty:
					vals.update({'Free Quantity':data['free_qty'] or 0,
								 'Adjustment Quantity':data['adj_qty'] or 0,})
				if self.service_product:
					invoice_id = data['invoice_id']
					invoice = self.env['account.move'].browse(invoice_id)
					# print("pddddddddddd",data['pdt_id'],self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id,self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin').id)
					if data['pdt_id'] and data['pdt_id']==self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty_product_template').id:
						invoice_value = (unit_price*100)/5
						cbm = invoice.od_cbm_vol
						vals.update({'5%':unit_price,'Invoice Value':invoice_value,'Gross Weight':invoice.od_gross_weight,'Dimension':cbm})
					if data['pdt_id'] and data['pdt_id']==self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin_product_template').id:
						# invoice_value = (unit_price*100)/5
						# invoice_id = data['invoice_id']
						# invoice = self.env['account.move'].browse(invoice_id)
						invoice_value = (unit_price/(invoice.od_cbm_vol if invoice.od_cbm_vol else 1))
						cbm = invoice.od_cbm_vol
						vals.update({'Dimension':cbm,'Rate':invoice_value,'Gross Weight':invoice.od_gross_weight})
					
				new_data_ls.append(vals)
		return new_data_ls


	def sale_data(self):
		sale_data = []
		exempt_pdts_ls = [self.env.ref('orchid_somfy_ksa_v16.od_product_delivery_admin').id,self.env.ref('orchid_somfy_ksa_v16.od_product_local_transportation').id,self.env.ref('orchid_somfy_ksa_v16.od_product_custom_duty').id]
		where_qry = " ai.move_type IN ('out_invoice') AND  ai.state IN ('posted') AND ai.od_expert_prgm_inv is not true"
		# print("hgttt",where_qry)
		if self.credit_note:
			where_qry = " ai.move_type IN ('out_invoice','out_refund') AND  ai.state IN ('posted') AND ai.od_expert_prgm_inv is not true"
		# if not self.service_product:
		if (not self.service_product) and (not self.with_service):
			where_qry = where_qry + " AND ail.product_id NOT IN " + str(tuple(exempt_pdts_ls))
		if self.service_product:
			where_qry = where_qry + " AND tmpl.type = 'service' "
		if self.warehouse_id=='dubai':
			where_qry = where_qry+ "AND ai.od_warehouse_id = 1"
		if self.warehouse_id=='france':
			where_qry = where_qry+ "AND ai.od_warehouse_id = 2"
		if self.user_id:
			where_qry = where_qry+ "AND ai.invoice_user_id =" + str(self.user_id.id)
		if self.partner_id:
			where_qry = where_qry+ "AND ai.partner_id =" + str(self.partner_id.id)
		if self.product_id:
			where_qry = where_qry+ "AND ail.product_id =" + str(self.product_id.id)
		if self.transaction_type:
			# print("uhtttt",self.transaction_type)
			where_qry = where_qry+ "AND ai.od_transaction_type = '"+self.transaction_type+"'"
		# if self.date_from.month()
		print("ssssssssss",self.from_date.month,self.from_date.year)
		new_ls = []
		old_ls = []
		print("verrrrrr",pd. __version__)
		if str(self.from_date)>'2023-04-30':
			# print("newwwwwwwwwwwwwwwwwwwwwwwwwww",n)
			new_ls = self.get_new_sale_data(self.from_date,self.to_date,where_qry)
		elif str(self.to_date)<'2023-05-01':
			# print("olddddddddd",o)
			old_ls = self.get_old_sale_data(self.from_date,self.to_date,where_qry)
		elif str(self.from_date)<'2023-04-30' and str(self.to_date)>'2023-05-01':
			# print("mixxxxxxxxxxxxxxxx",m)
			old_ls = self.get_old_sale_data(self.from_date,'2023-04-30',where_qry)
			new_ls = self.get_new_sale_data('2023-05-01',self.to_date,where_qry)


		if new_ls:
			sale_data+=new_ls
		if old_ls:
			sale_data+=old_ls
		# print("sale_data",sale_data)
		if not sale_data:
			raise UserError(_("No data to generate"))


		
		return sale_data


	def generate_excel(self):

		result = self.sale_data()
		if self.service_product:
			header_rage ='A1:AA1'
			dataframe= pd.DataFrame(result,columns=["Invoice Date","Invoice Number","Sale Order","Customer Reference","Customer Code","Customer","Named/Un Named","Sales person","Product Code","Country of Origin","Brand","Distribution Channel","Product Segment","Product","Product Family","Line of Business","Local Currency","Year","Month","Quantity","Unit Price","Sales","Exchange Rate","Sales SAR","Invoice Value","5%","Rate","Dimension","Gross Weight"])
		elif self.factory_price:
			if self.separate_qty:
				header_rage ='A1:AF1'
				dataframe= pd.DataFrame(result,columns=["Invoice Date","Invoice Number","Sale Order","Customer Reference","Customer Code","Customer","Named/Un Named","Payment Terms","Sales person","Product Code","HS Code","Country of Origin","Transaction Type","Brand","Distribution Channel","Product Segment","Product","Product Family","Line of Business","Local Currency","Year","Month","Quantity","Free Quantity","Adjustment Quantity","Unit Price","Sales","COS","Margin%","Margin Control Reason","Exchange Rate","Sales SAR","COS SAR","Factory Price","Factory Price SAR"])
			else:
				header_rage ='A1:AD1'
				dataframe= pd.DataFrame(result,columns=["Invoice Date","Invoice Number","Sale Order","Customer Reference","Customer Code","Customer","Named/Un Named","Payment Terms","Sales person","Product Code","HS Code","Country of Origin","Transaction Type","Brand","Distribution Channel","Product Segment","Product","Product Family","Line of Business","Local Currency","Year","Month","Quantity","Unit Price","Sales","COS","Margin%","Margin Control Reason","Exchange Rate","Sales SAR","COS SAR","Factory Price","Factory Price SAR"])
		else:
			if self.separate_qty:
				header_rage ='A1:AD1'
				dataframe= pd.DataFrame(result,columns=["Invoice Date","Invoice Number","Sale Order","Customer Reference","Customer Code","Customer","Named/Un Named","Payment Terms","Sales person","Product Code","HS Code","Country of Origin","Transaction Type","Brand","Distribution Channel","Product Segment","Product","Product Family","Line of Business","Local Currency","Year","Month","Quantity","Free Quantity","Adjustment Quantity","Unit Price","Sales","COS","Margin%","Margin Control Reason","Exchange Rate","Sales SAR","COS SAR"])
			else:
				header_rage ='A1:AB1'
				dataframe= pd.DataFrame(result,columns=["Invoice Date","Invoice Number","Sale Order","Customer Reference","Customer Code","Customer","Named/Un Named","Payment Terms","Sales person","Product Code","HS Code","Country of Origin","Transaction Type","Brand","Distribution Channel","Product Segment","Product","Product Family","Line of Business","Local Currency","Year","Month","Quantity","Unit Price","Sales","COS","Margin%","Margin Control Reason","Exchange Rate","Sales SAR","COS SAR"])

		dataframe.style.set_properties(subset=["Unit Price","Sales", "COS","Exchange Rate","Sales SAR","COS SAR"], **{'text-align': 'right'})
		dataframe.sort_values(by='Invoice Number')
		filename ='SalesRegister.xlsx'
		from_date =datetime.strptime(str(self.from_date),'%Y-%m-%d').strftime('%d-%m-%Y')
		to_date =datetime.strptime(str(self.to_date),'%Y-%m-%d').strftime('%d-%m-%Y')
		title="Sales Register- "+ from_date + " "+"to " +to_date
		# header_rage ='A1:S1'

		writer = pd.ExcelWriter(filename, engine='xlsxwriter')
		fp = BytesIO()
		writer.book.filename = fp
		dataframe.to_excel(writer, sheet_name='Sheet1',startrow=3,index=False,header=False)
		workbook  = writer.book
		worksheet = writer.sheets['Sheet1']
		title_format = workbook.add_format({
			'bold': True,
			'align': 'center',
			'fg_color': '#D7E4BC',
			'border': 0}) 
		header_style = workbook.add_format({
			'bold': True,
			'align': 'center',
			'border':0})
		tot_format = workbook.add_format({
			'bold': True,
			'align': 'left',
			'border': 0})
		tot_format1 = workbook.add_format({
			'bold': True,
			'align': 'right',
			'num_format': '#,##0.00',
			'border': 0})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'})	
		
		worksheet.merge_range(header_rage,title, title_format)	
		for col_num, value in enumerate(dataframe.columns.values):
			worksheet.write(2, col_num, value, header_style)
			size=len(value)+8
			worksheet.set_column(col_num,col_num,size)
		worksheet.set_column('F:F',50)
		# worksheet.set_column('I:I',45)
		# worksheet.set_column('J:J',45)
		worksheet.set_column('L:L',45)
		# worksheet.set_column('N:N',20,row_num_style)
		# worksheet.set_column('O:O',20,row_num_style)
		# worksheet.set_column('P:P',20,row_num_style)
		# worksheet.set_column('Q:Q',20,row_num_style)
		# worksheet.set_column('R:R',20,row_num_style)
		
		worksheet.set_column('V:V',20,row_num_style)
		worksheet.set_column('W:W',20,row_num_style)
		worksheet.set_column('X:X',20,row_num_style)
		worksheet.set_column('Y:Y',20,row_num_style)
		worksheet.set_column('Z:Z',20,row_num_style)
		worksheet.set_column('AA:AA',20,row_num_style)
		worksheet.set_column('AB:AB',20,row_num_style)
		worksheet.set_column('AC:AC',20,row_num_style)
		worksheet.set_column('AD:AD',20,row_num_style)
		worksheet.set_column('AE:AE',20,row_num_style)
		worksheet.set_column('AF:AF',20,row_num_style)
		worksheet.set_column('AG:AG',20,row_num_style)

		row=len(dataframe.index)+3
		col = 0
		worksheet.write(row,col,"Total",tot_format)
		if self.service_product:
			col=col+20
		else:
			col= col+22
		if self.factory_price:
			if self.separate_qty:
				total_ls=['Quantity','Free Quantity','Adjustment Quantity', 'Unit Price','Sales','COS','Margin%','Margin Control Reason','Exchange Rate','Sales SAR','COS SAR','Factory Price','Factory Price SAR']
			else:
				total_ls=['Quantity','Unit Price','Sales','COS','Margin%','Margin Control Reason','Exchange Rate','Sales SAR','COS SAR','Factory Price','Factory Price SAR']
		else:
			if self.separate_qty:
				total_ls=['Quantity','Free Quantity','Adjustment Quantity', 'Unit Price','Sales','COS','Margin%','Margin Control Reason','Exchange Rate','Sales SAR','COS SAR']
			else:
				if self.service_product:
					total_ls=['Quantity','Unit Price','Sales','Exchange Rate','Sales SAR','Invoice Value','5%']
				else:
					total_ls=['Quantity','Unit Price','Sales','COS','Margin%','Exchange Rate','Sales SAR','COS SAR']

		for column in dataframe[total_ls]:
			total=dataframe[column].sum()
			worksheet.write(row,col,total,tot_format1)
			print("column",column,row,col)
			if column =='Exchange Rate' or column =='Margin%' or column=='Margin Control Reason':
				print("yessss")
				exch_tot = ""
				worksheet.write(row,col,exch_tot,tot_format1)
			print("collllll",row,col)
			col=col+1

		

		writer.close()
		excel_file = base64.encodebytes(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'orchid.sale.register.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }

	def generate_view(self):
		
		date_from = self.from_date
		date_to = self.to_date
		user_id = self.user_id.id
		domain=[('company_id','=',self.company_id.id),('invoice_date','>=',date_from),('invoice_date','<=',date_to),('invoice_type','=','out_invoice'),('state','=','posted')]
		if self.credit_note:
			domain=[('company_id','=',self.company_id.id),('invoice_date','>=',date_from),('invoice_date','<=',date_to),('invoice_type','in',('out_refund','out_invoice')),('state','=','posted')]
		if self.stock_product:
			prd_domain = ('product_type','!=','service')
			domain.append(prd_domain)
		if self.warehouse_id=='dubai':
			ware_domain= ('warehouse_id','=',1)
			domain.append(ware_domain)
		if self.warehouse_id=='france':
			ware_domain= ('warehouse_id','=',2)
			domain.append(ware_domain)
		if self.user_id:
			user_domain = ('user_id','=',user_id)
			domain.append(user_domain)
		if self.partner_id:
			user_domain = ('cust_id','=',self.partner_id.id)
			domain.append(user_domain)
		if self.product_id:
			prdt_domain = ('product','=',self.product_id.id)
			domain.append(prdt_domain)
		if self.show_in_euro:
			action = self.env.ref('orchid_somfy_gulf.action_orchid_sales_register_euro_tree_view')
		else:
			action = self.env.ref('orchid_somfy_gulf.action_orchid_sales_register_tree_view')
		result = action.read()[0]
		result['domain'] = domain
		return result

	def sub_qry_select(self):
		select_str = """SELECT CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (sum(ail.price_subtotal)) * (-1)
						ELSE sum(ail.price_subtotal) END as subtotal,
						rp.name as partner,
						to_char(ai.invoice_date, 'Month-yyyy') as date,
						ai.currency_id as currency_id,
						tmpl.id as pdt_id
						-- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) * (-1)
						-- ELSE (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END as quantity

						-- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity * (-1))
						-- ELSE (ail.quantity) END as quantity,
						-- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.od_free_qty * (-1))
						-- ELSE (ail.od_free_qty) END as free_qty,
						-- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.od_adjustment_qty * (-1))
						-- ELSE (ail.od_adjustment_qty) END as adj_qty

						"""
		if self.separate_qty:
			select_str += ", CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity * (-1))\
						ELSE (ail.quantity) END as quantity,\
						CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.od_free_qty * (-1))\
						ELSE (ail.od_free_qty) END as free_qty,\
						CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.od_adjustment_qty * (-1))\
						ELSE (ail.od_adjustment_qty) END as adj_qty"
		else:
			select_str += ", CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) * (-1)\
						ELSE (ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END as quantity"
		return select_str

	def motor_qry_select(self):
		select_str = """SELECT 
							-- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN sum((ail.quantity + ail.od_free_qty)+ail.od_adjustment_qty) * (-1)
							-- ELSE sum(ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END as quantity,
							-- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN sum(ail.quantity )* (-1)
							-- ELSE sum(ail.quantity) END as quantity,
							-- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN sum(ail.od_free_qty) * (-1)
							-- ELSE sum(ail.od_free_qty) END as free_qty,
							-- CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN sum(ail.od_adjustment_qty) * (-1)
							-- ELSE sum(ail.od_adjustment_qty) END as adj_qty,
							rp.name as partner, 
							to_char(ai.invoice_date, 'Month-yyyy') as date"""
		if self.separate_qty:
			select_str += ", CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN sum(ail.quantity )* (-1)\
							ELSE sum(ail.quantity) END as quantity,\
							CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN sum(ail.od_free_qty) * (-1)\
							ELSE sum(ail.od_free_qty) END as free_qty,\
							CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN sum(ail.od_adjustment_qty) * (-1)\
							ELSE sum(ail.od_adjustment_qty) END as adj_qty"
		else:
			select_str += ", CASE WHEN ((ai.move_type)::text = 'out_refund'::text) THEN sum((ail.quantity + ail.od_free_qty)+ail.od_adjustment_qty) * (-1)\
							ELSE sum(ail.quantity + ail.od_free_qty+ail.od_adjustment_qty) END as quantity"
		return select_str

	def generate_motor(self):

		sub_where_qry = " ai.move_type IN ('out_invoice') AND  ai.state IN ('posted') "
		motor_where_qry = " ai.move_type IN ('out_invoice') AND  ai.state IN ('posted') "
		if self.credit_note:
			sub_where_qry = " ai.move_type IN ('out_invoice','out_refund') AND  ai.state IN ('posted') "
			motor_where_qry = " ai.move_type IN ('out_invoice','out_refund') AND  ai.state IN ('posted') "
		if self.stock_product:
			sub_where_qry = sub_where_qry + " AND tmpl.type <> 'service' "
		if self.warehouse_id=='dubai':
			sub_where_qry = sub_where_qry+ "AND ai.od_warehouse_id = 1"
			motor_where_qry = motor_where_qry+ "AND ai.od_warehouse_id = 1"
		if self.warehouse_id=='france':
			sub_where_qry = sub_where_qry+ "AND ai.od_warehouse_id = 2"
			motor_where_qry = motor_where_qry+ "AND ai.od_warehouse_id = 2"
		if self.user_id:
			sub_where_qry = sub_where_qry+ "AND ai.invoice_user_id =" + str(self.user_id.id)
			motor_where_qry = motor_where_qry+"AND ai.invoice_user_id =" + str(self.user_id.id)
		if self.partner_id:
			sub_where_qry = sub_where_qry+ "AND ai.partner_id =" + str(self.partner_id.id)
			motor_where_qry = motor_where_qry+"AND ai.partner_id =" + str(self.partner_id.id)
		if self.product_id:
			sub_where_qry = sub_where_qry+ "AND ail.product_id =" + str(self.product_id.id)
			motor_where_qry = motor_where_qry+"AND ail.product_id =" + str(self.product_id.id)


		subtotal_qry = []
		sub_qry = (''' %s

						from account_move_line ail,account_move ai,res_partner rp,product_template tmpl,product_product pp
						-- , orchid_account_invoice_cost cst
					where ail.product_id=pp.id and tmpl.id = pp.product_tmpl_id and ai.id=ail.move_id and rp.id=ai.partner_id and ai.invoice_date between '%s' and '%s'
					and  ''' + sub_where_qry +'''
					group by rp.name,to_char(ai.invoice_date, 'Month-yyyy'), ai.move_type,ai.currency_id,tmpl.id,ail.quantity , ail.od_free_qty,ail.od_adjustment_qty
					order by rp.name''')%(self.sub_qry_select(),self.from_date,self.to_date)
		# print(sub_qry)			
		self.env.cr.execute(sub_qry)
		sub_data_result = self.env.cr.dictfetchall()
		if not sub_data_result:
			raise UserError('There is no data to generate')
		for data in sub_data_result:
			# print("ddddddddffff",data)
			sales=data['subtotal'] or 0
			pdt_id = self.env['product.template'].browse(data['pdt_id'])
			cos=pdt_id and pdt_id.standard_price or 0
			# cos=cos*data['quantity']
			if self.separate_qty:
				cos = cos * (data['quantity']+data['free_qty']+data['adj_qty'])
			else:
				cos=cos*data['quantity']
			# cos=data[3] or 0
			if data['currency_id']!=1 and self.show_in_euro:
				sales=sales*self.exchange_rate_id.rate
				cos=cos*self.exchange_rate_id.rate

			vals ={ 'Sales':sales,
					'Partner Name':data['partner'],
					'Date':data['date'],
					'Cost':cos,
					'Quantity':0,
					}
			if self.separate_qty:
				vals.update({
					'Free Quantity':0,
					'Adjustment Quantity':0,
					})
			subtotal_qry.append(vals)

		partner_names = [z['partner'] for z in sub_data_result]
		partner_names = sorted(list(set(partner_names)))
		# partner_names = sorted(partner_names)
		
		motor_qty_data = []
		motor_qry = (''' %s
							from account_move_line ail,account_move ai,res_partner rp,product_product pp,
							product_template pt
						where ai.id=ail.move_id and rp.id=ai.partner_id and pp.id=ail.product_id
						and pp.product_tmpl_id=pt.id
						and pt.orchid_group_id=2 and ai.invoice_date between '%s' and '%s'
						and  ''' + motor_where_qry +'''
						group by rp.name,to_char(ai.invoice_date, 'Month-yyyy'),ai.move_type
						order by rp.name ''')%(self.motor_qry_select(),self.from_date,self.to_date)
						
		self.env.cr.execute(motor_qry)
		motor_data_result = self.env.cr.dictfetchall()
		if not motor_data_result:
			raise UserError('There is no data to generate')
		months = []
		for data in motor_data_result:
			vals ={ 'Quantity':data['quantity'],
					'Partner Name':data['partner'],
					'Date':data['date'],
					}
			if self.separate_qty:
				vals.update({
					'Free Quantity':data['free_qty'],
					'Adjustment Quantity':data['adj_qty'],
					})
			motor_qty_data.append(vals)
			months.append(data['date'])

		for sub_dict in subtotal_qry:
			for motor_dict in motor_qty_data:
				if sub_dict['Partner Name'] == motor_dict['Partner Name'] and sub_dict['Date']==motor_dict['Date']:
					sub_dict.update(motor_dict)
		if self.separate_qty:
			exceldata= pd.DataFrame(subtotal_qry,columns=["Partner Name","Quantity","Free Quantity","Adjustment Quantity","Sales","Date","Cost"])
		else:
			exceldata= pd.DataFrame(subtotal_qry,columns=["Partner Name","Quantity","Sales","Date","Cost"])
		exceldata = exceldata.sort_values(by='Partner Name')
		exceldata = exceldata.fillna(0) 
		exceldata.style.set_properties(subset=["Sales"], **{'text-align': 'right'})
		exceldata.sort_values(by='Partner Name')
		filename ='SalesRegister.xlsx'
		title="Sales Register- "+ str(self.from_date) + " "+"to " +str(self.to_date)
		header_rage ='A1:C1'
		writer = pd.ExcelWriter(filename, engine='xlsxwriter')
		fp = BytesIO()
		writer.book.filename = fp
		exceldata.columns = exceldata.columns.str.title().str.replace(r"[\"\',]", '')
		workbook  = writer.book
		worksheet= workbook.add_worksheet('Motor Analysis Report')
		title_format = workbook.add_format({
			'bold': True,
			'align': 'center',
			'fg_color': '#D7E4BC',
			'border': 0}) 
		header_style = workbook.add_format({
			'bold': True,
			'align': 'center',
			'fg_color': '#ECF2E9',
			'border':0})
		tot_format = workbook.add_format({
			'bold': True,
			'align': 'left',
			'border': 0})
		tot_format1 = workbook.add_format({
			'bold': True,
			'align': 'right',
			'border': 0})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'}) 
		row_num_style_total = workbook.add_format({'bold':True,'num_format': '#,##0.00'})
		worksheet.set_column('A:A',40)
		col =0
		row =2
		worksheet.write(row,col,"Partner",header_style)
		col=col+1
		startcol=0
		months_order = ['January  ','February ','March    ','April    ','May      ','June     ','July     ','August   ','September','October  ','November ','December ']
		date_via_sum=exceldata.groupby('Date').sum()
		months=list(set(months))
		months.sort(key=lambda x: months_order.index(x.split('-')[0]))
		month_dict = {}
		i = 1
		for m in months:
			month_dict[m] = i
			# i = i+2
			if self.separate_qty:
				i = i+6
			else:
				i = i+4

		for month in months:
			row_merge=row
			if self.separate_qty:
				col_merge = col+5
			else:
				col_merge = col+3
			worksheet.merge_range(row,col,row_merge,col_merge,month,header_style)
			row=row+1
			worksheet.write(row,col,"Quantity",header_style)
			col=col+1
			if self.separate_qty:
				worksheet.write(row,col,"Free Quantity",header_style)
				col=col+1
				worksheet.write(row,col,"Adjustment Quantity",header_style)
				col=col+1
			worksheet.write(row,col,"Sales",header_style)
			col=col+1
			worksheet.write(row,col,"Cost",header_style)
			col=col+1
			worksheet.write(row,col,"Margin",header_style)
			col=col+1
			row = row - 1
		row = row+2
		for Date,value in date_via_sum.iterrows():
			margin_tot = 0
			col = month_dict[Date]
			worksheet.write(row, col, date_via_sum.at[Date,'Quantity'],row_num_style_total)
			col=col+1
			if self.separate_qty:
				worksheet.write(row, col, date_via_sum.at[Date,'Free Quantity'],row_num_style_total)
				col=col+1
				worksheet.write(row, col, date_via_sum.at[Date,'Adjustment Quantity'],row_num_style_total)
				col=col+1
			worksheet.write(row, col, date_via_sum.at[Date,'Sales'],row_num_style_total)
			col=col+1
			worksheet.write(row, col, date_via_sum.at[Date,'Cost'],row_num_style_total)
			col=col+1
			margin_tot = margin_tot+(date_via_sum.at[Date,'Sales'] - date_via_sum.at[Date,'Cost'])
			worksheet.write(row, col, margin_tot,row_num_style_total)
		# col=i
		# quantity_sum = exceldata["Quantity"].sum()
		# price_sum = exceldata["Sales"].sum()
		# col_merge = col+1
		# row=row-2
		# row_merge=row
		# worksheet.merge_range(row,col,row_merge,col_merge,"Total",header_style)
		# row = row+1
		# worksheet.write(row,col,"Quantity", header_style)
		# col=col+1
		# worksheet.write(row, col,"Sales", header_style)
		# row = row+1
		# worksheet.write(row, col, price_sum, row_num_style_total)
		# col = col-1
		# worksheet.write(row, col, quantity_sum, row_num_style_total)
		
		col_merge = i-1
		row = 0
		col = 0
		row_merge = row
		worksheet.merge_range(row,col,row_merge,col_merge,title, title_format)
		if self.separate_qty:
			len_names = (len(months)*6)+1
		else:
			len_names = (len(months)*4)+1
		row = row+5
		for partner in partner_names:
			col =0
			worksheet.write(row, col, partner)
			for l in range(1,len_names):
				worksheet.set_column(row,l,15)
				worksheet.write(row, l, 0,row_num_style)
			for col_num, value in enumerate(exceldata.values):
				if value[0]==partner:
					if self.separate_qty:
						col = month_dict[value[5]]
					else:
						col = month_dict[value[3]]
					worksheet.write(row, col, value[1],row_num_style)
					col = col +1
					worksheet.write(row, col, value[2],row_num_style)
					col = col +1
					if self.separate_qty:
						worksheet.write(row, col, value[3],row_num_style)
						col = col +1
					worksheet.write(row, col, value[4],row_num_style)
					col = col +1
					if self.separate_qty:
						worksheet.write(row, col, value[6],row_num_style)
						col = col +1
						margin = value[4] - value[6]
					else:
						margin = value[2] - value[4]
					worksheet.write(row, col, margin,row_num_style)

			row = row + 1
		
		#total commented
		# partner_via_sum=exceldata.groupby('Partner Name').sum()
		# row = 5
		# for partner in partner_names:
		# 	for name,value in partner_via_sum.iterrows():
		# 		if name == partner:
		# 			col = len_names
		# 			worksheet.set_column(row,col,15)
		# 			worksheet.write(row, col, partner_via_sum.at[name,'Quantity'],row_num_style)
		# 			col = col + 1
		# 			worksheet.set_column(row,col,15)
		# 			worksheet.write(row, col, partner_via_sum.at[name,'Sales'],row_num_style)
		# 	row = row + 1

		writer.save()
		excel_file = base64.encodestring(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'orchid.sale.register.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }