from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd
import calendar
from dateutil.relativedelta import relativedelta
import xlsxwriter

class OrchidStockReportWiz(models.TransientModel):
	_name = 'od.stock.report.wiz'
	_description = 'Stock Report'

	date_to = fields.Date(string="Date")
	location_id = fields.Many2one('stock.location', string="Location", default=lambda self:self.env.ref('stock.stock_location_stock'))
	excel_file = fields.Binary(string='Excel Report',readonly=True)
	file_name = fields.Char(string='Excel File',readonly=True)
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)

	def get_data(self):

		qry = """SELECT
					tmpl.default_code as item_code,
					tmpl.name ->> 'en_US' as description,
					pp.id as product_id,
					-- opg.name as pdt_group,
					-- opt.name as pdt_type,
					pp.create_date as create_date
				FROM product_product pp 
				LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
				-- LEFT JOIN orchid_product_group opg ON opg.id = tmpl.orchid_group_id
				-- LEFT JOIN orchid_product_type opt ON opt.id = tmpl.orchid_type_id
				WHERE tmpl.detailed_type='product'
			"""

		self._cr.execute(qry)
		results = self._cr.dictfetchall()
		data_ls = []
		for data in results:
			product_id  = self.env['product.product'].browse(data['product_id'])
			inv_value_qry = """SELECT COALESCE(sum(svl.value),0) as value
							  FROM stock_valuation_layer svl 
							  LEFT JOIN stock_move sm ON sm.id=svl.stock_move_id
							  WHERE svl.product_id=%s AND svl.create_date::Date<='%s'AND svl.company_id=%s AND (sm.location_id=%s or sm.location_dest_id=%s)
							"""%(product_id.id, self.date_to,self.company_id.id, self.location_id.id, self.location_id.id)

			# print(inv_value_qry)
			self._cr.execute(inv_value_qry)
			inv_value_data = self._cr.fetchall()
			inv_value_data = [p[0] for p in inv_value_data if p[0]!=None]
			inv_value = 0
			if inv_value_data:
				inv_value = inv_value_data[0]

			# qty_available = product_id.qty_available
			qty_available_qry = """SELECT COALESCE(sum(svl.quantity),0) as quantity
							  FROM stock_valuation_layer svl 
							  LEFT JOIN stock_move sm ON sm.id=svl.stock_move_id
							  WHERE svl.product_id=%s AND svl.create_date::Date<='%s' AND svl.company_id=%s AND (sm.location_id=%s or sm.location_dest_id=%s)
							"""%(product_id.id, self.date_to,self.company_id.id, self.location_id.id, self.location_id.id)

			self._cr.execute(qty_available_qry)
			qty_available_data = self._cr.fetchall()
			qty_available_data = [p[0] for p in qty_available_data if p[0]!=None]
			qty_available = 0
			if qty_available_data:
				qty_available = qty_available_data[0]

			

			if inv_value:
				data_vals = {
				"Item Code":data['item_code'],
				"Product":data['description'],
				"Inventory On Hand":qty_available,
				"Value":inv_value,
				}
				data_ls.append(data_vals)
		return data_ls

	def generate_excel(self):
		data_ls = self.get_data()
		dataframe = pd.DataFrame(data_ls,columns=["Item Code","Product","Inventory On Hand","Value"])

		filename ='stockreport.xlsx'
		date_to =datetime.strptime(str(self.date_to),'%Y-%m-%d').strftime('%d-%m-%Y')
		title="Stock Report of "+self.location_id.display_name+" as on "+date_to
		header_rage ='A1:D1'

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
		row_num_style_int = workbook.add_format({'num_format': '0'})	
		
		worksheet.merge_range(header_rage,title, title_format)
		for col_num, value in enumerate(dataframe.columns.values):
			worksheet.write(3, col_num, value, header_style)
			size=len(value)+8
			worksheet.set_column(col_num,col_num,size)

		worksheet.set_column('A:A',30)
		worksheet.set_column('B:B',45)
		worksheet.set_column('C:C',30)
		worksheet.set_column('D:D',30)
		worksheet.set_column('E:E',30)
		worksheet.set_column('F:F',30)
		worksheet.set_column('G:G',20,row_num_style)
		worksheet.set_column('H:H',20,row_num_style)
		worksheet.set_column('I:I',20,row_num_style)
		worksheet.set_column('J:J',20,row_num_style)
		worksheet.set_column('K:K',20,row_num_style)
		worksheet.set_column('L:L',20,row_num_style)
		worksheet.set_column('N:N',20,row_num_style)

		writer.close()
		excel_file = base64.encodebytes(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()

		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.stock.report.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }
