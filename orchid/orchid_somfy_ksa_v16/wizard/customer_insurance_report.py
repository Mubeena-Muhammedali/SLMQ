from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from collections import OrderedDict
from odoo.exceptions import UserError
from io import BytesIO
import base64
import xlsxwriter
import calendar

class OrchidCustomerInsurance(models.TransientModel):
	_name = 'orchid.customer.insurance.wiz'
	_description = 'Customer Insurance Details'
	
	
	from_date = fields.Date(string="Start Date",required=True)	
	to_date = fields.Date(string="End Date",required=True)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)


	@api.onchange('from_date')
	def last_day_of_month(self):
		if self.from_date:
			any_day=datetime.strptime(self.from_date,'%Y-%m-%d')
			next_month = any_day.replace(day=28) + timedelta(days=4)  # this will never fail
			to_date=next_month - timedelta(days=next_month.day)
			to_date=to_date.strftime('%Y-%m-%d')
			self.to_date=to_date

	def get_insurance_data(self):

		insurance_qry=("""SELECT
			   
			   COALESCE(sum(oir.sales),0) as amount,
			   to_char(oir.date_invoice, 'MM-YYYY') as month,
			   res.id as partner_id,
			   date_trunc('year',oir.date_invoice),
			   date_trunc('month',oir.date_invoice)

			   FROM orchid_account_invoice_reports_view oir 
			   LEFT JOIN res_partner res ON res.id = oir.cust_id
			   WHERE oir.company_id=%s AND oir.invoice_type IN ('out_invoice','out_refund') AND oir.date_invoice BETWEEN '%s' AND '%s'
			   -- AND res.id in (271,269)
			   GROUP BY 
			   to_char(oir.date_invoice, 'MM-YYYY'),
			   res.id,
			   date_trunc('year',oir.date_invoice),
			   date_trunc('month',oir.date_invoice)

			   ORDER BY date_trunc('year',oir.date_invoice),date_trunc('month',oir.date_invoice)

			   """)%(self.company_id.id, self.from_date,self.to_date)

		self.env.cr.execute(insurance_qry)
		insurance_data = self.env.cr.fetchall()
		if not insurance_data:
			raise UserError('There is no data to generate')
		else:
			result = []
			month_ls = []
			for data in insurance_data:
				vals={
				'partner_id':data[2],
				'amount':data[0] or 0
				}
				
				if data[1][0] == '0':
					month = int(data[1][1])
				else:
					month = int(data[1][:2])
				month = calendar.month_name[month]
				year = data[1][2:]
				vals['month'] = str(month)+str(year)
				if vals['month'] not in month_ls:
					month_ls.append(vals['month'])
				result.append(vals)
			partner_ls = [z['partner_id'] for z in result]
			partner_ls = sorted(list(set(partner_ls)))
			return month_ls,partner_ls,result


	def generate_excel(self):

		month_ls,partner_ls,insurance_data = self.get_insurance_data()
		
		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		worksheet= workbook.add_worksheet('Customer Insurance Details')
		filename ='CustomerInsuranceDetails.xlsx'
		title_month_start = fields.Date.from_string(self.from_date).strftime("%B-%Y")
		title_month_end = fields.Date.from_string(self.to_date).strftime("%B-%Y")
		title="SOMFY SAUDI ARABIA TURNOVER " +str(title_month_start).upper()+" - "+str(title_month_end).upper()
		header_range =8+len(month_ls)

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
			'fg_color': '#ECF2E9',
			'border': 0})
		tot_format1 = workbook.add_format({
			'bold': True,
			'align': 'right',
			'fg_color': '#ECF2E9',
			'num_format': '#,##0.00',
			'border': 0})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'})	

		col_merge = header_range
		row = 0
		col = 0
		row_merge = row
		worksheet.merge_range(row,col,row_merge,col_merge,title, title_format)

		header = ['BP Code','BP Name','Credit Limit Insured','Reference Credit Insurance','Named/Un Named','Terms of Payment Description','City','Country Code']
		month_sum = OrderedDict()
		row = row +2
		for i in header:
			worksheet.write(row, col,i, header_style)
			size=len(i)+8
			worksheet.set_column(col,col,size)
			col=col+1
		month_dict ={}
		for m in month_ls:
			month_dict[m] = col
			
			month_sum[m]={}
			month_sum[m]['total'] =0

			size=len(m)+8
			worksheet.set_column(col,col,size)
			worksheet.write(row, col,m, header_style)
			col=col+1

		worksheet.set_column('B:B',70)
		worksheet.set_column(col,col,20)
		worksheet.write(row, col,'Grand Total', header_style)
		grand_tot_col = col
		grand_total = 0
		for partner_id in partner_ls:
			partner_sum = 0
			partner_id = self.env['res.partner'].search([('id','=',partner_id)])
			code=partner_id.od_ban_bp or ""
			name=partner_id.name or ""
			cr_lim=partner_id.od_insured_credit_limit or 0
			ref=partner_id.od_credit_insurance_ref or ""
			named=partner_id.od_name_unamed or ""
			payment_term=partner_id.property_payment_term_id.note or ""
			city=partner_id.city or ""
			country=partner_id.country_id.code or ""
			row = row +1
			col=0
			worksheet.write(row, col,code)
			col=col+1
			worksheet.write(row, col,name)
			col=col+1
			worksheet.write(row, col,cr_lim,row_num_style)
			col=col+1
			worksheet.write(row, col,ref)
			col=col+1
			worksheet.write(row, col,named)
			col=col+1
			worksheet.write(row, col,payment_term)
			col=col+1
			worksheet.write(row, col,city)
			col=col+1
			worksheet.write(row, col,country)
			for i in month_ls:
				m_col = month_dict[i]
				worksheet.write(row, m_col,0,row_num_style)
			for data in insurance_data:
				if partner_id.id == data['partner_id']:
					for m in month_ls:
						if data['month'] ==m:
							col = month_dict[m]
							worksheet.write(row, col,data['amount'],row_num_style)
							partner_sum = partner_sum + data['amount']
							if m in month_sum:
								month_sum[m]['total'] = month_sum[m]['total'] + data['amount']
					worksheet.write(row, grand_tot_col,partner_sum,row_num_style)
			grand_total = grand_total + partner_sum

		row=row+1
		worksheet.merge_range(row,0,row,7,'Grand Total',tot_format)
		col=7
		for key, value in month_sum.items():
			col=col+1
			worksheet.write(row, col,value['total'],tot_format1)
		worksheet.write(row, grand_tot_col,grand_total,tot_format1)

		workbook.close()
		output.seek(0)
		excel_file = base64.encodestring(output.read())
		self.write({'excel_file':excel_file,'file_name':filename})
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'orchid.customer.insurance.wiz',
			  'res_id': self.id,
			  'type': 'ir.actions.do_nothing',
			  'target': 'new'
			  }



