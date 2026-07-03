# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError
from datetime import datetime, timedelta
import base64
import csv
import io
import xlrd
import datetime

class OdGulfSaleUpload(models.TransientModel):
	_name = 'od.gulf.sale.upload.wiz'
	_description = 'Gulf Sale Upload'

	data_file = fields.Binary(string='Data')

	def upload_data(self):
		if not self.data_file:
			raise Warning(_('Nothing to import.'))
			
		# read excel
		try:
			data_file=base64.b64decode(self.data_file)
			book = xlrd.open_workbook(file_contents=data_file)
		except FileNotFoundError:
			raise UserError('No such file or directory found. \n%s.' % self.data_file)
		except xlrd.biffh.XLRDError:
			raise UserError('Only excel files are supported.')

		for sheet in book.sheets():
			try:
				line_vals = []
				if sheet.name == 'Sheet1':
					for row in range(sheet.nrows):
						if row >= 1:
							sale_header_info = sheet.row_values(row)
							name = sale_header_info[0]
							customer_code = sale_header_info[1]
							validity_date = sale_header_info[2]
							date_order = sale_header_info[3]
							payment_term_code = sale_header_info[4]
							if_service = sale_header_info[5]
							user_login = sale_header_info[6]
							customer_ref = sale_header_info[7]
							transaction_type = sale_header_info[8]
							warehouse_code = sale_header_info[9]
							incoterm_code = sale_header_info[10]
							shipping_policy = sale_header_info[11]
							transportation = sale_header_info[12]

							partner_id = self.env['res.partner'].search([('od_ban_bp','=',customer_code)])
							if not partner_id:
								raise UserError(_("Partner with BP code '%s' is not found!!")%(customer_code))
							# pricelist_id = partner_id.property_product_pricelist.id

							# user_id = self.env['res.users'].search([('login','=',user_login)])
							user_id = partner_id.user_id
							print ("??????????????/",user_id)
							if not user_id:
								raise UserError(_("User with Login '%s' is not found!!")%(user_login))

							# warehouse_id = self.env['stock.warehouse'].search([('od_code','=',warehouse_code)])
							# if not warehouse_id:
							# 	raise UserError(_("warehouse with code '%s' is not found!!")%(warehouse_code))
							date_order = datetime.datetime(*xlrd.xldate_as_tuple(date_order, book.datemode))
							print("dateeeee",date_order)
							# mandatory
							header_vals={
							'name':name,
							'partner_id':partner_id.id,
							# 'pricelist_id':pricelist_id,
							'pricelist_id':2,
							# 'warehouse_id':warehouse_id.id,
							'picking_policy':shipping_policy,
							'date_order':date_order,
							'od_service':if_service,
							# 'fiscal_position_id':3
							}

							# optional
							if validity_date:
								validity_date = datetime.datetime(*xlrd.xldate_as_tuple(validity_date, book.datemode))

								header_vals['validity_date'] = validity_date
							if user_id:
								header_vals['user_id'] = user_id.id
							if customer_ref:
								header_vals['client_order_ref'] = customer_ref
							if transaction_type:
								header_vals['od_transaction_type'] = transaction_type
							if incoterm_code:
								incoterm_id = self.env['stock.incoterms'].search([('code','=',incoterm_code)])
								if not incoterm_id:
									raise UserError(_("Incoterm with code '%s' is not found!!")%(incoterm_code))
								header_vals['incoterm'] = incoterm_id.id
							if payment_term_code:
								payment_term_id = self.env['account.payment.term'].search([('od_code','=',payment_term_code)])
								if not payment_term_id:
									# payment_term_id = self.env['account.payment.term'].browse(110)
									payment_term_id = partner_id.property_payment_term_id
								header_vals['payment_term_id'] = payment_term_id.id
							if transportation:
								header_vals['od_transportation'] = transportation
							sale_id = self.env['sale.order'].create(header_vals)
				if sheet.name == 'Sheet2':
					for row in range(sheet.nrows):
						if row >= 1:
							info = sheet.row_values(row)
							# sale_line
							internal_reference = info[0]
							product_uom_qty = info[1]
							name = info[2]
							od_free_qty = info[3]
							od_adjustment_qty = info[4]
							price_unit = info[5]

							product_id = self.env['product.product'].search([('default_code','=',internal_reference)])
							if not product_id:
								raise UserError(_("Product not found for Ref '%s' ")%(internal_reference))
							product_id = product_id.id
							line_vals={
							'order_id':sale_id.id,
							'product_id':product_id,
							'name':name,
							'product_uom_qty':product_uom_qty,
							'od_free_qty':od_free_qty,
							'od_adjustment_qty':od_adjustment_qty,
							'price_unit':price_unit,
							}
							self.env['sale.order.line'].create(line_vals)

			except IndexError:
				pass
		# sale_id.action_confirm()
		
		# data = base64.b64decode(self.data_file)
		# data= data.decode('ascii')
		# file_input = io.StringIO(data)
		# file_input.seek(0)
		# reader_info = []
		# sale_header_info = []
		# sale_line_info = []
		# delimeter = ','
		# reader = csv.reader(file_input, delimiter=delimeter,
		# 					lineterminator='\r\n')
		# try:
		# 	reader_info.extend(reader)
		# except Exception:
		# 	raise Warning("Not a valid file!")
		# del reader_info[0] #deleting header columns
		# sale_header_info = reader_info[0]
		# del reader_info[0] #deleting header column values
		# del reader_info[0] #deleting line columns
		# sale_line_info = reader_info
		# name = sale_header_info[0]
		# customer_code = sale_header_info[1]
		# validity_date = sale_header_info[2]
		# date_order = sale_header_info[3]
		# payment_term_code = sale_header_info[4]
		# if_service = sale_header_info[5]
		# user_login = sale_header_info[6]
		# customer_ref = sale_header_info[7]
		# transaction_type = sale_header_info[8]
		# warehouse_code = sale_header_info[9]
		# incoterm_code = sale_header_info[10]
		# shipping_policy = sale_header_info[11]
		# transportation = sale_header_info[12]

		# partner_id = self.env['res.partner'].search([('od_ban_bp','=',customer_code)])
		# if not partner_id:
		# 	raise UserError(_("Partner with BP code '%s' is not found!!")%(customer_code))
		# pricelist_id = partner_id.property_product_pricelist.id

		# user_id = self.env['res.users'].search([('login','=',user_login)])
		# if not user_id:
		# 	raise UserError(_("User with Login '%s' is not found!!")%(user_login))

		# warehouse_id = self.env['stock.warehouse'].search([('od_code','=',warehouse_code)])
		# if not warehouse_id:
		# 	raise UserError(_("warehouse with code '%s' is not found!!")%(warehouse_code))

		# # mandatory
		# header_vals={
		# 'name':name,
		# 'partner_id':partner_id.id,
		# 'pricelist_id':pricelist_id,
		# 'warehouse_id':warehouse_id.id,
		# 'picking_policy':shipping_policy,
		# 'date_order':date_order,
		# 'od_service':if_service,
		# }

		# # optional
		# if validity_date:
		# 	header_vals['validity_date'] = validity_date
		# if user_id:
		# 	header_vals['user_id'] = user_id.id
		# if customer_ref:
		# 	header_vals['client_order_ref'] = customer_ref
		# if transaction_type:
		# 	header_vals['od_transaction_type'] = transaction_type
		# if incoterm_code:
		# 	incoterm_id = self.env['stock.incoterms'].search([('code','=',incoterm_code)])
		# 	if not incoterm_id:
		# 		raise UserError(_("Incoterm with code '%s' is not found!!")%(incoterm_code))
		# 	header_vals['incoterm'] = incoterm_id.id
		# if payment_term_code:
		# 	payment_term_id = self.env['account.payment.term'].search([('od_code','=',payment_term_code)])
		# 	if not payment_term_id:
		# 		payment_term_id = self.env['account.payment.term'].browse(110)
		# 	header_vals['payment_term_id'] = payment_term_id.id
		# if transportation:
		# 	header_vals['od_transportation'] = transportation
		# sale_id = self.env['sale.order'].create(header_vals)

		# # sale_line
		# for info in sale_line_info:
		# 	internal_reference = info[0]
		# 	product_uom_qty = info[1]
		# 	name = info[2]
		# 	od_free_qty = info[3]
		# 	od_adjustment_qty = info[4]
		# 	price_unit = info[5]

		# 	product_id = self.env['product.product'].search([('default_code','=',internal_reference)])
		# 	if not product_id:
		# 		raise UserError(_("Product not found for Ref '%s' ")%(internal_reference))
		# 	product_id = product_id.id
		# 	line_vals={
		# 	'order_id':sale_id.id,
		# 	'product_id':product_id,
		# 	'name':name,
		# 	'product_uom_qty':product_uom_qty,
		# 	'od_free_qty':od_free_qty,
		# 	'od_adjustment_qty':od_adjustment_qty,
		# 	'price_unit':price_unit,
		# 	}
		# 	self.env['sale.order.line'].create(line_vals)
