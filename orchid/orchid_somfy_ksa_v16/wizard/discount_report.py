from odoo import fields, models,_
import xlsxwriter
from io import BytesIO
import base64
from odoo.exceptions import UserError

class OrchidDiscountReportWiz(models.TransientModel):
	_name = 'orchid.discount.report.wiz'
	_description = 'Discount Report'

	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	partner_id = fields.Many2one('res.partner', string="Customer")
	categ_id = fields.Many2one('product.category', string="Category")
	report_type = fields.Selection([('price','Pricelist'),('vbr','Volume Rebate'),('net','Net Price')], string="Type")

	def get_data(self):
		if self.report_type=='price':
			where_qry = "WHERE pl.partner_id is not null AND pl.active is not false AND plne.categ_id is not null AND plne.compute_price='percentage' "
			partner_where_qry=where_qry
			categ_where_qry=where_qry
			all_product_qry = "WHERE pl.partner_id is not null AND pl.active is not false AND plne.applied_on='3_global' AND plne.compute_price='percentage' "
			if self.partner_id:
				partner_where_qry=where_qry+" AND pl.partner_id="+str(self.partner_id.id)
				all_product_qry=all_product_qry+" AND pl.partner_id="+str(self.partner_id.id)
			if self.categ_id:
				categ_where_qry=where_qry+" AND plne.categ_id="+str(self.categ_id.id)
			
			categ_qry = """SELECT plne.categ_id as categ_id,
							pc.name as categ_name,
							SUM(pc.od_sale_qty) as sold_qty
						FROM product_pricelist_item plne
						LEFT JOIN product_pricelist pl ON (plne.pricelist_id=pl.id)
						LEFT JOIN product_category pc ON (pc.id=plne.categ_id) 
						"""+categ_where_qry+""" GROUP BY pc.id,plne.categ_id,pc.name ORDER BY pc.od_sale_qty desc"""
			self._cr.execute(categ_qry)
			print(categ_qry)
			categ_ls = self._cr.dictfetchall()
			categ_dict_ls=categ_ls
			if not categ_ls:
				raise UserError(_("No Data!!!"))

			partner_data=False
			print(categ_dict_ls)
			for categ_dict in categ_dict_ls:
				print("jhhhhhhhhhhhh",categ_dict)
				partner_qry=partner_where_qry+" AND plne.categ_id ="+str(categ_dict['categ_id'])
				partner_qry+=" AND plne.date_start is null AND plne.date_end is null "

				print("kkkkkkkk",partner_where_qry)
				qry = """SELECT 
						 res.id as partner_id,
						 res.name as partner,
						 res.od_ban_bp as bp_code,
						 rc.code as country,
						 ds.name as dist_channel,
						 lne.name as line_of_bsns,
						 sum(plne.percent_price) as discount
						 FROM product_pricelist pl
						 LEFT JOIN product_pricelist_item plne ON (plne.pricelist_id=pl.id) 
						 LEFT JOIN res_partner res ON (res.id=pl.partner_id) 
						 LEFT JOIN orchid_distribution_channel ds ON (ds.id=res.od_distr_chanel_id) 
						 LEFT JOIN orchid_line_of_business lne ON (lne.id=res.od_lne_buss_id) 
						 LEFT JOIN res_country rc ON (rc.id=res.country_id) 
						 
					"""+partner_qry+""" GROUP BY res.id,res.name,
						 res.od_ban_bp,
						 rc.code,
						 ds.name,
						 lne.name,
						 pl.id"""
				self._cr.execute(qry)
				# print("nnnn",qry)
				partner_ls = self._cr.dictfetchall()
				# print("partner_ls",partner_ls)
				if partner_ls:
					partner_data=True
				categ_dict['partner']=partner_ls

			# all productqry
			all_product_dict = {}
			all_product_qry+=" AND plne.date_start is null AND plne.date_end is null "
			qry = """SELECT 
						 res.id as partner_id,
						 res.name as partner,
						 res.od_ban_bp as bp_code,
						 rc.code as country,
						 ds.name as dist_channel,
						 lne.name as line_of_bsns,
						 sum(plne.percent_price) as discount
						 FROM product_pricelist pl
						 LEFT JOIN product_pricelist_item plne ON (plne.pricelist_id=pl.id) 
						 LEFT JOIN res_partner res ON (res.id=pl.partner_id) 
						 LEFT JOIN orchid_distribution_channel ds ON (ds.id=res.od_distr_chanel_id) 
						 LEFT JOIN orchid_line_of_business lne ON (lne.id=res.od_lne_buss_id) 
						 LEFT JOIN res_country rc ON (rc.id=res.country_id) 
						 
					"""+all_product_qry+""" GROUP BY res.id,res.name,
						 res.od_ban_bp,
						 rc.code,
						 ds.name,
						 lne.name,
						 pl.id"""
			self._cr.execute(qry)
			# print("nnnn",qry)
			partner_ls = self._cr.dictfetchall()
			# print("partner_ls",partner_ls)
			if partner_ls:
				partner_data=True
			all_product_dict['partner']=partner_ls
			
			if not partner_data:
				raise UserError(_("No Data!!!"))
			categ_data_dict_ls = [d_dict for d_dict in categ_dict_ls if d_dict['partner']]
			return categ_data_dict_ls,categ_ls,all_product_dict


		elif self.report_type=='vbr':
			where_qry = "WHERE pl.partner_id is not null AND pl.active is not false AND plne.categ_id is not null"
			all_product_qry = "WHERE pl.partner_id is not null AND pl.active is not false AND plne.applied_on ='3_global'"
			partner_where_qry=where_qry
			categ_where_qry=where_qry
			if self.partner_id:
				partner_where_qry=where_qry+" AND pl.partner_id="+str(self.partner_id.id)
				all_product_qry = all_product_qry+ "AND pl.partner_id="+str(self.partner_id.id)
			if self.categ_id:
				categ_where_qry=where_qry+" AND plne.categ_id="+str(self.categ_id.id)
			
			categ_qry = """SELECT plne.categ_id as categ_id,
							pc.name as categ_name
						FROM orchid_volume_rebate_line plne
						LEFT JOIN orchid_volume_rebate pl ON (plne.rebate_id=pl.id)
						LEFT JOIN product_category pc ON (pc.id=plne.categ_id) 
						"""+categ_where_qry+""" GROUP BY plne.categ_id,pc.name"""
			self._cr.execute(categ_qry)
			# print(categ_qry)
			categ_ls = self._cr.dictfetchall()
			categ_dict_ls=categ_ls
			if not categ_ls:
				raise UserError(_("No Data!!!"))

			partner_data=False
			# print(categ_dict_ls)
			for categ_dict in categ_dict_ls:
				# print("jhhhhhhhhhhhh",categ_dict)
				partner_qry=partner_where_qry+" AND plne.categ_id ="+str(categ_dict['categ_id'])
				# print("kkkkkkkk",partner_where_qry)
				qry = """SELECT 
						 res.id as partner_id,
						 res.name as partner,
						 res.od_ban_bp as bp_code,
						 rc.code as country,
						 ds.name as dist_channel,
						 lne.name as line_of_bsns,
						 sum(plne.rebate_volume_per) as discount
						 FROM orchid_volume_rebate pl
						 LEFT JOIN orchid_volume_rebate_line plne ON (plne.rebate_id=pl.id) 
						 LEFT JOIN res_partner res ON (res.id=pl.partner_id) 
						 LEFT JOIN orchid_distribution_channel ds ON (ds.id=res.od_distr_chanel_id) 
						 LEFT JOIN orchid_line_of_business lne ON (lne.id=res.od_lne_buss_id) 
						 LEFT JOIN res_country rc ON (rc.id=res.country_id) 
						 
					"""+partner_qry+""" GROUP BY res.id,res.name,
						 res.od_ban_bp,
						 rc.code,
						 ds.name,
						 lne.name,
						 pl.id"""
				self._cr.execute(qry)
				# print("nnnn",qry)
				partner_ls = self._cr.dictfetchall()
				# print("partner_ls",partner_ls)
				if partner_ls:
					partner_data=True
				categ_dict['partner']=partner_ls

			# all productqry
			all_product_dict = {}
			qry = """SELECT 
						 res.id as partner_id,
						 res.name as partner,
						 res.od_ban_bp as bp_code,
						 rc.code as country,
						 ds.name as dist_channel,
						 lne.name as line_of_bsns,
						 sum(plne.rebate_volume_per) as discount
						 FROM orchid_volume_rebate pl
						 LEFT JOIN orchid_volume_rebate_line plne ON (plne.rebate_id=pl.id) 
						 LEFT JOIN res_partner res ON (res.id=pl.partner_id) 
						 LEFT JOIN orchid_distribution_channel ds ON (ds.id=res.od_distr_chanel_id) 
						 LEFT JOIN orchid_line_of_business lne ON (lne.id=res.od_lne_buss_id) 
						 LEFT JOIN res_country rc ON (rc.id=res.country_id) 
						 
					"""+all_product_qry+""" GROUP BY res.id,res.name,
						 res.od_ban_bp,
						 rc.code,
						 ds.name,
						 lne.name,
						 pl.id"""
			self._cr.execute(qry)
			# print("nnnn",qry)
			partner_ls = self._cr.dictfetchall()
			# print("partner_ls",partner_ls)
			if partner_ls:
				partner_data=True
			all_product_dict['partner']=partner_ls

			
			if not partner_data:
				raise UserError(_("No Data!!!"))
			categ_data_dict_ls = [d_dict for d_dict in categ_dict_ls if d_dict['partner']]
			return categ_data_dict_ls,categ_ls,all_product_dict



		elif self.report_type=='net':
			# only1_product is considered
			where_qry = "WHERE pl.partner_id is not null AND pl.active is not false AND plne.product_tmpl_id is not null AND plne.compute_price='fixed' "
			partner_where_qry=where_qry
			categ_where_qry=where_qry
			if self.partner_id:
				partner_where_qry=where_qry+" AND pl.partner_id="+str(self.partner_id.id)
			# if self.categ_id:
			# 	categ_where_qry=where_qry+" AND plne.categ_id="+str(self.categ_id.id)
			
			categ_qry = """SELECT plne.product_tmpl_id as categ_id,
							pc.name as categ_name
						FROM product_pricelist_item plne
						LEFT JOIN product_pricelist pl ON (plne.pricelist_id=pl.id)
						LEFT JOIN product_template pc ON (pc.id=plne.product_tmpl_id) 
						"""+categ_where_qry+""" GROUP BY plne.product_tmpl_id,pc.name"""
			self._cr.execute(categ_qry)
			# print(categ_qry)
			categ_ls = self._cr.dictfetchall()
			categ_dict_ls=categ_ls
			if not categ_ls:
				raise UserError(_("No Data!!!"))

			partner_data=False
			# print(categ_dict_ls)
			for categ_dict in categ_dict_ls:
				# print("jhhhhhhhhhhhh",categ_dict)
				partner_qry=partner_where_qry+" AND plne.product_tmpl_id ="+str(categ_dict['categ_id'])
				partner_qry +=" AND plne.date_start is null AND plne.date_end is null"
				# print("kkkkkkkk",partner_where_qry)
				qry = """SELECT 
						 res.id as partner_id,
						 res.name as partner,
						 res.od_ban_bp as bp_code,
						 rc.code as country,
						 ds.name as dist_channel,
						 lne.name as line_of_bsns,
						 sum(plne.fixed_price) as discount
						 FROM product_pricelist pl
						 LEFT JOIN product_pricelist_item plne ON (plne.pricelist_id=pl.id) 
						 LEFT JOIN res_partner res ON (res.id=pl.partner_id) 
						 LEFT JOIN orchid_distribution_channel ds ON (ds.id=res.od_distr_chanel_id) 
						 LEFT JOIN orchid_line_of_business lne ON (lne.id=res.od_lne_buss_id) 
						 LEFT JOIN res_country rc ON (rc.id=res.country_id) 
						 
					"""+partner_qry+""" GROUP BY res.id,res.name,
						 res.od_ban_bp,
						 rc.code,
						 ds.name,
						 lne.name,
						 pl.id"""
				self._cr.execute(qry)
				# print("nnnn",qry)
				partner_ls = self._cr.dictfetchall()
				# print("partner_ls",partner_ls)
				if partner_ls:
					partner_data=True
				categ_dict['partner']=partner_ls
			categ_data_dict_ls = [d_dict for d_dict in categ_dict_ls if d_dict['partner']]
			return categ_data_dict_ls,categ_ls,{}

	def print_excel(self):
		print("hlooooooooooooooooooo")
		categ_dict_ls,categ_ls,all_product_dict = self.get_data()
		filename ='CustomerDiscountReport.xlsx'
		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		sheet_name = 'Customer Discount Report'
		sheet= workbook.add_worksheet(sheet_name)
		title_format = workbook.add_format({
			'bold': True,
			'align': 'center',
			'fg_color': '#D7E4BC',
			'border': 0,
			'font_size':14}) 
		header_style = workbook.add_format({
			'bold': True,
			'align': 'center',
			'fg_color':'#b2b2b2',
			'border':0})
		sub_header_style = workbook.add_format({
			'bold': True,
			'border':0})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'}) 
		col=bp_code_col=0
		bp_name_col=1
		country_col=2
		channel_col=3
		bsns_col=4
		row=2
		categ_row=2
		all_pdt_col = 5 if all_product_dict and all_product_dict.get('partner') else 4
		categ_col=all_pdt_col+1
		partner_dict={}
		categ_dict={}
		# print('hffffffffffffxxxxxxxxx',categ_dict_ls)
		sheet.write(categ_row,bp_code_col,"BP Code",header_style)
		sheet.write(categ_row,bp_name_col,"BP Name",header_style)
		sheet.write(categ_row,country_col,"Country",header_style)
		sheet.write(categ_row,channel_col,"Distribution Channel",header_style)
		sheet.write(categ_row,bsns_col,"Line of Business",header_style)
		if all_product_dict and all_product_dict.get('partner'):
			sheet.write(categ_row,all_pdt_col,"All Products",header_style)
		sheet.set_column('A:B',25)
		sheet.set_column('C:C',15)
		sheet.set_column('D:D',20)
		sheet.set_column('E:E',20)
		sheet.set_column('F:F',20)
		for data in categ_dict_ls:
			if isinstance(data['categ_name'], dict):
				categ_name = data['categ_name']['en_US']
			else:
				categ_name = data['categ_name']
			# print("categ_name",categ_name)
			sheet.write(categ_row,categ_col,categ_name,header_style)
			sheet.set_column(categ_col,categ_col,25,row_num_style)
			for partner_data in data['partner']:
				if partner_data['partner_id'] in partner_dict:
					partner_row = partner_dict[partner_data['partner_id']]
				else:
					row+=1
					partner_row = row
					partner_dict[partner_data['partner_id']]=partner_row
				sheet.write(partner_row,bp_code_col,partner_data['bp_code'])
				sheet.write(partner_row,bp_name_col,partner_data['partner'])
				sheet.write(partner_row,country_col,partner_data['country'])
				sheet.write(partner_row,channel_col,partner_data['dist_channel'])
				sheet.write(partner_row,bsns_col,partner_data['line_of_bsns'])
				sheet.write(partner_row,categ_col,partner_data['discount'], row_num_style)
			categ_col+=1
		print("jjjjjjjhhhhhhh",partner_dict)
		if all_product_dict and all_product_dict.get('partner'):
			for partner_data in all_product_dict['partner']:
					if partner_data['partner_id'] in partner_dict:
						partner_row = partner_dict[partner_data['partner_id']]
					else:
						row+=1
						partner_row = row
						partner_dict[partner_data['partner_id']]=partner_row
					sheet.write(partner_row,bp_code_col,partner_data['bp_code'])
					sheet.write(partner_row,bp_name_col,partner_data['partner'])
					sheet.write(partner_row,country_col,partner_data['country'])
					sheet.write(partner_row,channel_col,partner_data['dist_channel'])
					sheet.write(partner_row,bsns_col,partner_data['line_of_bsns'])
					sheet.write(partner_row,all_pdt_col,partner_data['discount'], row_num_style)
			# categ_col+=1


		filename= filename
		workbook.close()
		output.seek(0)
		excel_file = base64.encodebytes(output.read())
		self.excel_file = excel_file
		self.file_name =filename
		return {            
		'type': 'ir.actions.act_window',            
		'view_type': 'form',            
		'view_mode': 'form',            
		'res_model': 'orchid.discount.report.wiz',            
		'res_id': self.id,           
		'target': 'new',            
		}



























