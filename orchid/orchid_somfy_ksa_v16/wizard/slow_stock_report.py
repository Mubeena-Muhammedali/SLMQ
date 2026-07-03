from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd
import calendar
from dateutil.relativedelta import relativedelta
import xlsxwriter

class OrchidSlowStockReportWiz(models.TransientModel):
	_name = 'od.slow.stock.report.wiz'
	_description = 'Slow Moving Stock Report'

	date_from = fields.Date(string="Date From")
	date_to = fields.Date(string="Date")
	excel_file = fields.Binary(string='Excel Report',readonly=True)
	file_name = fields.Char(string='Excel File',readonly=True)
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)

	def get_data(self):
		location_id = self.env.ref('stock.stock_location_stock')
		qry = """SELECT
					tmpl.default_code as item_code,
					tmpl.name ->> 'en_US' as description,
					pp.id as product_id,
					opg.name as pdt_group,
					opt.name as pdt_type,
					pp.create_date as create_date
				FROM product_product pp 
				LEFT JOIN product_template tmpl ON tmpl.id = pp.product_tmpl_id
				LEFT JOIN orchid_product_group opg ON opg.id = tmpl.orchid_group_id
				LEFT JOIN orchid_product_type opt ON opt.id = tmpl.orchid_type_id
				WHERE tmpl.detailed_type='product' and pp.active is true
			"""

		self._cr.execute(qry)
		results = self._cr.dictfetchall()
		data_ls = []
		for data in results:
			product_id  = self.env['product.product'].browse(data['product_id'])
			# last_po_date_qry = """SELECT po.date_approve 
			# 					  FROM purchase_order po 
			# 					  LEFT JOIN purchase_order_line pol ON pol.order_id=po.id
			# 					  WHERE po.state IN ('purchase','done') AND pol.product_id=%s
			# 					  ORDER BY po.date_approve DESC
			# 					  limit 1 """%(product_id.id)
			last_po_date_qry = """SELECT svl.create_date 
								  FROM stock_valuation_layer svl
								  LEFT JOIN stock_move sm ON sm.id=svl.stock_move_id 
								  WHERE svl.product_id=%s AND svl.create_date::Date<='%s' AND svl.company_id=%s AND svl.quantity>0 AND sm.location_dest_id=%s
								  ORDER BY svl.create_date DESC
								  limit 1
							"""%(product_id.id, self.date_to,self.company_id.id, location_id.id)

			self._cr.execute(last_po_date_qry)
			po_date = self._cr.fetchall()
			po_date = [p[0] for p in po_date if p[0]!=None]
			last_po = ""
			if po_date:
				last_po = po_date[0] 
			
			# qty_available = product_id.qty_available
			qty_available_qry = """SELECT COALESCE(sum(svl.quantity),0) as quantity
							  FROM stock_valuation_layer svl 
							  LEFT JOIN stock_move sm ON sm.id=svl.stock_move_id
							  WHERE svl.product_id=%s AND svl.create_date::Date<='%s' AND svl.company_id=%s
							   -- AND (sm.location_id=s or sm.location_dest_id=s)
							"""%(product_id.id, self.date_to,self.company_id.id)
							# """%(product_id.id, self.date_to,self.company_id.id, location_id.id, location_id.id)

			self._cr.execute(qty_available_qry)
			qty_available_data = self._cr.fetchall()
			qty_available_data = [p[0] for p in qty_available_data if p[0]!=None]
			qty_available = 0
			if qty_available_data:
				qty_available = qty_available_data[0]

			sold_qty_qry = """SELECT COALESCE(sum(sol.product_uom_qty),0) as sold_qty
							  FROM sale_order_line sol 
							  LEFT JOIN sale_order so ON sol.order_id=so.id
							  LEFT JOIN stock_warehouse sw ON sw.id=so.warehouse_id
							  WHERE so.state IN ('sale','done') AND sol.product_id=%s AND so.date_order<='%s' AND so.company_id=%s AND sw.lot_stock_id=%s
							"""%(product_id.id, self.date_to, self.company_id.id, location_id.id)

			self._cr.execute(sold_qty_qry)
			sold_qty_data = self._cr.fetchall()
			sold_qty_data = [p[0] for p in sold_qty_data if p[0]!=None]
			sold_qty = 0
			if sold_qty_data:
				sold_qty = sold_qty_data[0] 
			stock_ratio =  0
			if qty_available and (not sold_qty):
				stock_ratio=9
			elif qty_available and sold_qty:
				stock_ratio =  (qty_available/sold_qty)


			depreciation_per =  0
			if 0<stock_ratio<=1:
				depreciation_per = 0
			if 1<stock_ratio<=2:
				depreciation_per = 15
			if 2<stock_ratio<=3:
				depreciation_per = 30
			if 3<stock_ratio<=4:
				depreciation_per = 45
			if 4<stock_ratio<=5:
				depreciation_per = 60
			if 5<stock_ratio<=6:
				depreciation_per = 75
			if 6<stock_ratio<=7:
				depreciation_per = 75
			if 7<stock_ratio<=8:
				depreciation_per = 95
			if 8<stock_ratio:
				depreciation_per = 95

			inv_value_qry = """SELECT COALESCE(sum(svl.value),0) as value
							  FROM stock_valuation_layer svl 
							  LEFT JOIN stock_move sm ON sm.id=svl.stock_move_id
							  WHERE svl.product_id=%s AND svl.create_date::Date<='%s'AND svl.company_id=%s 
							 -- AND (sm.location_id=S or sm.location_dest_id=s or sm.id is null)
							"""%(product_id.id, self.date_to,self.company_id.id)
							# """%(product_id.id, self.date_to,self.company_id.id, location_id.id, location_id.id)

			self._cr.execute(inv_value_qry)
			inv_value_data = self._cr.fetchall()
			inv_value_data = [p[0] for p in inv_value_data if p[0]!=None]
			inv_value = 0
			if inv_value_data:
				inv_value = inv_value_data[0]

			#FINAL ADJUSTMENT USING PRODUCT MASTER VALUE
			actual_value = product_id.x_studio_actualvalue or 0.0
			diff = actual_value - inv_value
			# if actual_value:
			# 	print("yessss",inv_value,actual_value,product_id.display_name)
			# 	inv_value = inv_value + diff

			# sms_provision = (inv_value/depreciation_per) if depreciation_per else 0
			sms_provision = inv_value*depreciation_per/100
			risk = ""
			last_po_diff_date = self.date_to+relativedelta(months=-12)
			# last_po_diff_date = last_po_diff_date.date()
			# print("jjjjjjjjj",last_po_diff_date,type(last_po_diff_date),last_po,type(last_po))
			
			# if sms_provision<=0:
			# 	if inv_value and last_po_diff_date and last_po and (not sold_qty) and (last_po_diff_date>last_po.date()):
			# 		risk="Risky"
			# 		provision_reworked=inv_value
			provision_reworked = 0
			if data.get('create_date'):
				if data.get('create_date').date()<=last_po_diff_date and stock_ratio>1:
					risk="Risky"
					provision_reworked = sms_provision

			# if inv_value and qty_available:
			if inv_value or qty_available:
				data_vals = {
				"Item Code":data['item_code'],
				"Description":data['description'],
				"Product Group":data['pdt_group'],
				"QSM Line":data['pdt_type'],
				"Creation Date":data['create_date'],
				"Last GRN Date":last_po,
				"Inventory On Hand":qty_available,
				"Annual Qty Sold in period":sold_qty,
				"Stock Rotation Ratio":stock_ratio,
				"Depreciation Rate":depreciation_per,
				"Inventory Value":inv_value,
				"Provision for SMS":sms_provision,
				"Under Risk":risk,
				"Provn Reworked":provision_reworked,
				}
				data_ls.append(data_vals)
		return data_ls


	
	def generate_excel(self):
		data_ls = self.get_data()
		dataframe = pd.DataFrame(data_ls,columns=["Item Code","Description","Product Group","QSM Line","Creation Date","Last GRN Date","Inventory On Hand","Annual Qty Sold in period","Stock Rotation Ratio","Depreciation Rate","Inventory Value","Provision for SMS","Under Risk","Provn Reworked"])

		filename ='Slowmovingstock.xlsx'
		# date_from =datetime.strptime(str(self.date_from),'%Y-%m-%d').strftime('%d-%m-%Y')
		date_to =datetime.strptime(str(self.date_to),'%Y-%m-%d').strftime('%d-%m-%Y')
		# title="Provision for Slow Moving Stock- "+ date_from + " "+"to " +date_to
		title="Provision for Slow Moving Stock as on "+date_to
		header_rage ='A1:N1'

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
			worksheet.write(2, col_num, value, header_style)
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
			  'res_model': 'od.slow.stock.report.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }



	