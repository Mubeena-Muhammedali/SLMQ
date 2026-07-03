# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
import base64
import csv
import io
from io import BytesIO
import pandas as pd
import xlrd

class OrchidProductPriceChange(models.Model):
	_name = "od.product.price.change"
	# _inherit = ['mail.thread']
	_description="Product Price Change"

	state = fields.Selection([('draft','Draft'),('validate','Validated'),('confirm','Confirmed')],default="draft",copy=False)
	price_type = fields.Selection([('base','Base Price'),('customer','Customer Price')],copy=False)
	base_pricing_line_ids = fields.One2many('od.product.price.change.line','price_change_id', string="Lines", copy=False)
	customer_pricing_line_ids = fields.One2many('od.customer.price.change.line','price_change_id', string="Lines", copy=False)
	date_from = fields.Date(string="Date From")
	date_to = fields.Date(string="Date to")
	data_file = fields.Binary(string='Data', default=False)
	excel_file = fields.Binary(string='Template File')
	name = fields.Char(string="Name", default="New", copy=False)

	@api.onchange('price_type','date_from','date_to')
	def onchange_name(self):
		for rec in self:
			if rec.price_type and rec.date_from and rec.date_to:
				price_type = dict(rec._fields['price_type'].selection).get(rec.price_type)
				name=str(price_type)+"-"+str(rec.date_from)+" to "+str(rec.date_to)
				rec.name=name

	def button_search(self):
		if self.data_file:
			raise Warning(_('Remove the data file before searching!!.'))
		if self.price_type=='customer':
			if self.customer_pricing_line_ids:
				self.customer_pricing_line_ids.unlink()
			if self.base_pricing_line_ids:
				self.base_pricing_line_ids.unlink()
			get_data = '''SELECT foo.line_id as line_id, foo.pricelist_id as pricelist_id, foo.product_id as product_id,
							foo.price as current_price From
							(select prl.id as line_id,pr.id as pricelist_id,pp.id as product_id,prl.fixed_price as price
							FROM product_pricelist_item prl
							LEFT JOIN product_pricelist pr ON pr.id=prl.pricelist_id
							LEFT JOIN product_product pp ON pp.id = prl.product_id
							LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
							where compute_price='fixed' and applied_on='0_product_variant'
							 UNION ALL
							select prl.id  as line_id,pr.id as pricelist_id,pp.id as product_id,prl.fixed_price as price
							FROM product_pricelist_item prl
							LEFT JOIN product_pricelist pr ON pr.id=prl.pricelist_id
							LEFT JOIN product_template pt ON pt.id = prl.product_tmpl_id
							 LEFT JOIN product_product pp ON pp.product_tmpl_id = pt.id
							where compute_price='fixed' and applied_on='1_product') as foo order by foo.pricelist_id'''
			self._cr.execute(get_data)
			customer_price_data = self._cr.dictfetchall()
			for customer_data in customer_price_data:
				vals={
				'price_change_id':self.id,
				'date_from':self.date_from,
				'date_to':self.date_to,
				'pricelist_id':customer_data['pricelist_id'],
				'product_id':customer_data['product_id'],
				'line_id':customer_data['line_id'],
				'current_price':customer_data['current_price'],
				'new_price':customer_data['current_price'],
				}
				self.env['od.customer.price.change.line'].create(vals)

		if self.price_type=='base':
			if self.customer_pricing_line_ids:
				self.customer_pricing_line_ids.unlink()
			if self.base_pricing_line_ids:
				self.base_pricing_line_ids.unlink()
			for product in self.env['product.product'].search([]):
				vals={
				'price_change_id':self.id,
				'date_from':self.date_from,
				'date_to':self.date_to,
				'product_id':product.id,
				'current_price':product.od_sale_price,
				'new_price':product.od_sale_price,
				}
				self.env['od.product.price.change.line'].create(vals)

	def read_xl_file(self):
		book = xlrd.open_workbook(file_contents=base64.b64decode(self.data_file))
		sheet = book.sheet_by_index(0)
		values_sheet = []
		for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
			values = []
			for colx, cell in enumerate(row, 1):
				if cell.ctype is xlrd.XL_CELL_NUMBER:
					is_float = cell.value % 1 != 0.0
					values.append(
						str(cell.value) if is_float else str(int(cell.value)))
				elif cell.ctype is xlrd.XL_CELL_DATE:
					is_datetime = cell.value % 1 != 0.0
					dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(
						cell.value, book.datemode))
					values.append(
						dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT
									) if is_datetime else dt.
						strftime(DEFAULT_SERVER_DATE_FORMAT))
				elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
					values.append(u'True' if cell.value else u'False')
				elif cell.ctype is xlrd.XL_CELL_ERROR:
					raise ValueError(
						_("Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s"
						  ) % {
							  'row':
							  rowx,
							  'col':
							  colx,
							  'cell_value':
							  xlrd.error_text_from_code.get(
								  cell.value,
								  _("unknown error code %s") % cell.value)
						  })
				else:
					values.append(cell.value)
			values_sheet.append(values)
		del values_sheet[0]
		return values_sheet

	def button_download_template(self):
		print("herreeewddsds")
		if self.price_type == 'base':
			get_data = '''SELECT pl.id as line_id, pt.default_code as product_code,
						  pt.name as product_name, pl.current_price as current_price, pl.new_price as new_price
						  FROM od_product_price_change_line pl
						  LEFT JOIN product_product pp ON pp.id = pl.product_id
						  LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
						   WHERE price_change_id=%s
						  ORDER BY pl.id'''%(self.id)
			self._cr.execute(get_data)
			product_data = self._cr.dictfetchall()
			data_ls = []
			for data in product_data:
				vals={
				'Line':data['line_id'],
				'Product Code':data['product_code'],
				'Product':data['product_name'],
				'Current Price':data['current_price'],
				'New Price':data['new_price'],
				}
				data_ls.append(vals)
			dataframe= pd.DataFrame(data_ls,columns=["Line","Product Code","Product","Current Price","New Price"])

		if self.price_type == 'customer':
			get_data = '''SELECT pl.id as line_id, pr.name as pricelist,pt.default_code as product_code,
						  pt.name as product_name, pl.current_price as current_price, pl.new_price as new_price
						  FROM od_customer_price_change_line pl
						  LEFT JOIN product_product pp ON pp.id = pl.product_id
						  LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
						  LEFT JOIN product_pricelist pr ON pr.id = pl.pricelist_id
						  WHERE price_change_id=%s
						  ORDER BY pl.id'''%(self.id)
			self._cr.execute(get_data)
			product_data = self._cr.dictfetchall()
			data_ls = []
			for data in product_data:
				vals={
				'Line':data['line_id'],
				'Pricelist':data['pricelist'],
				'Product Code':data['product_code'],
				'Product':data['product_name'],
				'Current Price':data['current_price'],
				'New Price':data['new_price'],
				}
				data_ls.append(vals)
			dataframe= pd.DataFrame(data_ls,columns=["Line","Pricelist","Product Code","Product","Current Price","New Price"])
		filename =self.name+'.xlsx'
		writer = pd.ExcelWriter(filename, engine='xlsxwriter')
		fp = BytesIO()
		writer.book.filename = fp
		dataframe.to_excel(writer, sheet_name='Sheet1',startrow=1,index=False,header=False)
		workbook  = writer.book
		worksheet = writer.sheets['Sheet1']
		header_style = workbook.add_format({
			'bold': True,
			'align': 'center',
			'border':0})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'})	
		for col_num, value in enumerate(dataframe.columns.values):
			worksheet.write(0, col_num, value, header_style)
		if self.price_type=='base':
			worksheet.set_column('D:D',20,row_num_style)
			worksheet.set_column('E:E',20,row_num_style)
		if self.price_type=='customer':
			worksheet.set_column('E:E',20,row_num_style)
			worksheet.set_column('F:F',20,row_num_style)
		writer.close()
		excel_file = base64.encodebytes(fp.getvalue())
		self.write({'excel_file':excel_file})
		fp.close()
		return {
		'type': 'ir.actions.act_url',
		'name': 'pricetemplate',
		'url': '/web/content/od.product.price.change/%s/excel_file/%s?download=true' %(self.id,filename),
		}

	def button_upload(self):
		value_data = self.read_xl_file()
		print("value",value_data)
		if not value_data:
			raise Warning(_('Nothing to Upload.'))
		for value in value_data:
			line_id = value[0]
			if self.price_type=='base':
				new_price = value[4] or 0
				update_line = '''UPDATE od_product_price_change_line set new_price=%s WHERE id=%s'''%(new_price,line_id)
			if self.price_type=='customer':
				new_price = value[5] or 0
				update_line = '''UPDATE od_customer_price_change_line set new_price=%s WHERE id=%s'''%(new_price,line_id)

			self._cr.execute(update_line)
		self.state='validate'
				
	def reset_to_draft(self):
		self.state='draft'		

	def button_update(self):
		print("hereeee")
		if not self.data_file:
			raise Warning(_('Date file is not found.'))

		if self.price_type=='base' and not self.base_pricing_line_ids:
			raise Warning(_('Nothing to update.'))
		if self.price_type=='customer' and not self.customer_pricing_line_ids:
			raise Warning(_('Nothing to update.'))
		for line in self.base_pricing_line_ids:
			line.product_id.product_tmpl_id.od_sale_price = line.new_price
			line.product_id.product_tmpl_id.od_onchange_sale_price()
		for line in self.customer_pricing_line_ids:
			line.line_id.fixed_price = line.new_price

		self.state='confirm'

	def unlink(self):
		if self.state!='draft':
			raise Warning(_('Confirmed Entry cannot be deleted.'))
		return super(OrchidProductPriceChange,self).unlink()

	# @api.model
	# def create(self, vals):
	# 	print("valsss",vals)
	# 	return super(OrchidProductPriceChange, self).create(vals)

class OrchidProductPriceChangeLine(models.Model):
	_name = "od.product.price.change.line"
	_description="Product Price Change Line"

	date_from = fields.Date(string="Date From")
	date_to = fields.Date(string="Date to")
	price_change_id = fields.Many2one('od.product.price.change', string="Price Change", ondelete='cascade', copy=False)
	product_id = fields.Many2one('product.product', string="Product")
	current_price = fields.Float(string="Current Sale Price")
	new_price = fields.Float(string="New Sale Price")

class OrchidCustomerPriceChangeLine(models.Model):
	_name = "od.customer.price.change.line"
	_description="Customer Price Change Line"

	date_from = fields.Date(string="Date From")
	date_to = fields.Date(string="Date to")
	price_change_id = fields.Many2one('od.product.price.change', string="Price Change", ondelete='cascade', copy=False)
	line_id = fields.Many2one('product.pricelist.item', string="Pricelist Item", copy=False)
	pricelist_id = fields.Many2one('product.pricelist', string="Pricelist", copy=False)
	product_id = fields.Many2one('product.product', string="Product")
	current_price = fields.Float(string="Current Sale Price")
	new_price = fields.Float(string="New Sale Price")

