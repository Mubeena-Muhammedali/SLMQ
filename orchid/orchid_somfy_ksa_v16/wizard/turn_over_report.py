from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError
from io import BytesIO
import base64
import pandas as pd

class OrchidCustomerTurReport(models.TransientModel):
	
	_name = 'orchid.customer.info.report.wiz'
	_description = 'Customer Info Report'

	partner_id = fields.Many2one('res.partner', string="Customer")
	od_name_unamed = fields.Selection([('named', 'Named'),('un_named', 'UnNamed'),('out_of_scope', 'Out of Scope')], string='Named/Un Named')
	od_lne_buss_id = fields.Many2one('orchid.line.of.business',string='Line Of Business')

	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)


	def get_data(self):

		where_qry=""" WHERE res.active is true AND res.parent_id is null AND res.customer_rank>=1 """
		if self.partner_id:
			where_qry+=""" AND res.id="""+str(self.partner_id.id)
		if self.od_name_unamed:
			where_qry+=""" AND res.od_name_unamed='"""+str(self.od_name_unamed)+"'"
		if self.od_lne_buss_id:
			where_qry+=""" AND lne.id="""+str(self.od_lne_buss_id.id)