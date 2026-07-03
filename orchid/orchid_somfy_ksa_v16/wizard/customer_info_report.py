from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd

class OrchidCustomerInfoReport(models.TransientModel):
	
	_name = 'orchid.customer.info.report.wiz'
	_description = 'Customer Info Report'

	partner_id = fields.Many2one('res.partner', string="Customer")
	od_name_unamed = fields.Selection([('named', 'Named'),('un_named', 'UnNamed'),('out_of_scope', 'Out of Scope')], string='Named/Un Named')
	od_lne_buss_id = fields.Many2one('orchid.line.of.business',string='Line Of Business')

	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)
	report_type = fields.Selection([('customer_info','Customer Info Report'),('turn_over','Turnover Report')], string="Report", default="customer_info")
	date_from = fields.Date(string="Date From")
	date_to = fields.Date(string="Date To")

	def get_data(self):

		where_qry=""" WHERE res.active is true AND res.parent_id is null AND res.customer_rank>=1 """
		if self.partner_id:
			where_qry+=""" AND res.id="""+str(self.partner_id.id)
		if self.od_name_unamed:
			where_qry+=""" AND res.od_name_unamed='"""+str(self.od_name_unamed)+"'"
		if self.od_lne_buss_id:
			where_qry+=""" AND lne.id="""+str(self.od_lne_buss_id.id)

		data_qry = """SELECT 
						res.id as partner_id,
						res.ref as bp_code,
						res.name as partner,
						res.od_name_unamed as unnamed,
						lne.name as line_of_bsns,
						dst.name as dist_channel,
						-- res.od_m_segment as segment,
						-- res.od_insured_credit_limit as cred_lmt,
						res.od_coverage_value as cvrg_value,

						res.street as street,
						res.street2 as street2,
						res.city as city,
						state.name as state,
						rc.name->>'en_US' as country,
						res.zip as zip,
						res.od_somfy_credit_limit as somfy_cred_lmt,
						date_part('year',res.create_date) AS creation_year
						FROM res_partner res
						LEFT JOIN orchid_line_of_business lne ON lne.id=res.od_lne_buss_id
						LEFT JOIN orchid_distribution_channel dst ON dst.id=res.od_distr_chanel_id
						LEFT JOIN res_country rc ON rc.id=res.country_id
						LEFT JOIN res_country_state state ON state.id=res.state_id
						"""+where_qry
		print(data_qry)
		self._cr.execute(data_qry)
		results = self._cr.dictfetchall()

		data_ls= []
		for data in results:
			named = ''
			address=''
			if data['street']:
				address+=data['street']
			if data['street2']:
				if address:
					address+=","+data['street2']
				else:
					address+=data['street2']
			if data['city']:
				if address:
					address+=","+data['city']
				else:
					address+=data['city']
			if data['state']:
				if address:
					address+=","+data['state']
				else:
					address+=data['state']
			if data['country']:
				if address:
					address+=","+data['country']
				else:
					address+=data['country']
			if data['zip']:
				if address:
					address+=","+data['zip']
				else:
					address+=data['zip']
			if data['unnamed']:
				if data['unnamed']=='named':
					named='Named'
				if data['unnamed']=='un_named':
					named='UnNamed'
				if data['unnamed']=='out_of_scope':
					named='Out of Scope'
			partner_id = self.env['res.partner'].browse(data['partner_id'])
			# turnover from account invoice report
			turnover_amount = 0
			if self.report_type=='turn_over':
				all_partners_and_children = {}
				all_partner_ids = []
				for partner in partner_id.filtered('id'):
					# price_total is in the company currency
					all_partners_and_children[partner] = self.env['res.partner'].with_context(active_test=False).search([('id', 'child_of', partner.id)]).ids
					all_partner_ids += all_partners_and_children[partner]

				domain = [
					('partner_id', 'in', all_partner_ids),
					('state', 'not in', ['draft', 'cancel']),
					('move_type', 'in', ('out_invoice', 'out_refund')),
					('invoice_date','>=',self.date_from),
					('invoice_date','<=',self.date_to),
				]
				price_totals = self.env['account.invoice.report'].read_group(domain, ['price_subtotal'], ['partner_id'])
				for partner, child_ids in all_partners_and_children.items():
					turnover_amount = sum(price['price_subtotal'] for price in price_totals if price['partner_id'][0] in child_ids)



			vals={
			'BP Code':data['bp_code'],
			'Customer':data['partner'],
			'Named/UnNamed':named,
			'Line Of Business':data['line_of_bsns'],
			'Distribution Channel':data['dist_channel'],
			# 'Insured Credit Limit':data['cred_lmt'],
			'Somfy Credit Limit':data['somfy_cred_lmt'],
			'Credit Insurance Coverage Value':data['cvrg_value'],
			'Address':address,
			'Payment Terms':partner_id.property_payment_term_id and partner_id.property_payment_term_id.name or "",
			"Business Unit description":"KSA",
			"Country":data['country'],
			'BP Number':data['bp_code'],
			'BP Name':data['partner'],
			"Turnover":turnover_amount,
			"Year of Creation Date":data['creation_year'],
			}
			data_ls.append(vals)
		if not data_ls:
			raise UserError(_("No data!!"))
		return data_ls

	def generate_excel(self):
		result = self.get_data()
		if self.report_type=='customer_info':
			header_rage ='A1:I1'
			dataframe= pd.DataFrame(result,columns=["BP Code","Customer","Address","Payment Terms","Named/UnNamed","Line Of Business","Distribution Channel","Somfy Credit Limit","Credit Insurance Coverage Value"])
			dataframe.sort_values(by='Customer')
			filename ='CustomerInfo.xlsx'
			title="Customer Info Report"
		elif self.report_type=='turn_over':
			header_rage ='A1:H1'
			dataframe= pd.DataFrame(result,columns=["Business Unit description","Country","BP Number","BP Name","Line Of Business","Distribution Channel","Turnover","Year of Creation Date"])
			dataframe.sort_values(by='BP Name')
			filename ='CustomerTurnover.xlsx'
			title="Customer Turnover Report"
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
		worksheet.set_column('B:B',50)
		if self.report_type=='turn_over':
			worksheet.set_column('D:D',50)
			worksheet.set_column('G:G',20,row_num_style)
			row=len(dataframe.index)+3
			col = 0
			worksheet.write(row,col,"Total",tot_format)
			col= col+6
			total_ls=["Turnover"]
			for column in dataframe[total_ls]:
				total=dataframe[column].sum()
				worksheet.write(row,col,total,tot_format1)
				col = col + 1
		if self.report_type=='customer_info':
			worksheet.set_column('C:C',50)
			worksheet.set_column('H:H',20,row_num_style)
			worksheet.set_column('I:I',20,row_num_style)

		writer.close()
		excel_file = base64.encodebytes(fp.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		fp.close()
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'orchid.customer.info.report.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.act_window',
			  'target': 'new'
			  }






