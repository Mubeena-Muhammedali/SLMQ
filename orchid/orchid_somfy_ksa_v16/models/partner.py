from datetime import datetime

from odoo import api, fields, models, _

# Modification in Partner Master
class Partner(models.Model):
	_inherit = 'res.partner' 

	od_bus_type = fields.Many2one('orchid.buss.type',string='Business Entity Type')
	od_license_no = fields.Char(string='Trade License Number')
	od_lic_expiry_date = fields.Date(string='License Expiry Date')
	od_cc_no = fields.Char(string='Chamber of Commerce Number')
	od_cc_expiry_date = fields.Date(string='CoC Expiry Date')
	od_issue_authority = fields.Char(string='License Issuing Authority')
	od_owner_name = fields.Char(string='Name of The Owner')
	od_owner_national = fields.Char(string='Owner Nationality')
	od_spons_name = fields.Char(string='Name of the Sponsor')
	od_spons_national = fields.Char(string='Sponsor Nationality')

	# od_lne_buss = fields.Char(string='Line Of Business')
	# od_distr_chanel = fields.Char(string='Distribution Channel')
	od_lne_buss_id = fields.Many2one('orchid.line.of.business',string='Line Of Business')
	od_distr_chanel_id = fields.Many2one('orchid.distribution.channel',string='Distribution Channel')
	od_branch = fields.Boolean(string='Branch', default=False)
	od_man_assem = fields.Boolean(string='Manufacturing/Assembly', default=False)
	od_ttl_empl = fields.Integer(string='Total employees')
	od_ttl_mgt_staff = fields.Integer(string='Total Management Staff')
	od_tover_prd_1 = fields.Date(string="Turnover Declaration From")
	od_tover_prd_2 = fields.Date(string="Turnover Declaration To")
	potential_tover_1 = fields.Date(string="Potential / Expected Turnover with Somfy From")
	potential_tover_2 = fields.Date(string="Potential / Expected Turnover with Somfy To")
	od_m_segment = fields.Selection([('ICC','ICC'),('IWC','IWC'),('REA','REA'),('REC','REC'),('CBS','CBS'),('OTH','OTH'),('ESP','ESP')], string="Market Segment", tracking=True)
	od_ksa_partner = fields.Boolean(string="KSA Partner", default=False)
	od_margin_control = fields.Boolean(string="Margin Control", default=False)
	 
	
	od_arabic_name=fields.Char(string="Name in Arabic")
	od_arabic_street = fields.Char(string="Arabic Street")
	od_arabic_street2 = fields.Char(string="Arabic Street2")
	od_arabic_city = fields.Char(string="Arabic City")
	od_arabic_state_id = fields.Char(related='state_id.od_arabic_name', string='Arabic State', ondelete='restrict', store=True)
	od_arabic_country_id = fields.Char(related='country_id.od_arabic_name', string='Arabic Country', ondelete='restrict', store=True)
	
	# od_arabic_property_supplier_payment_term_id = fields.Char(related='property_supplier_payment_term_id.od_arabic_name',string="Vendor Payment Terms in Arabic", store=True)
	# od_arabic_property_payment_term_id = fields.Char(related='property_payment_term_id.od_arabic_name',string="Customer Payment Terms in Arabic", store=True)
	od_commercial_identification =fields.Char(string="Commercial Identification")
	od_ban_bp =fields.Char(string="BAN BP Code")
	od_insured_credit_limit =fields.Float(string='Insured Credit Limit')
	od_payment_behaviour = fields.Selection([('regular', 'Regular'),('doubt', 'Doubtful'),('unsatisfied', 'Unsatisfactory')], string='Payment Behaviour',default='regular')
	
	od_credit_insurance_ref =fields.Char(string="Credit Insurance Reference")
	od_name_unamed = fields.Selection([('named', 'Named'),('un_named', 'UnNamed'),('out_of_scope', 'Out of Scope')], string='Named/Un Named')
	# od_coverage_type =fields.Selection([('named','Named Coverage'),('unnamed','Unnamed Coverage')],string='Credit Insurance Coverage Type', default="unnamed")
	od_coverage_value =fields.Float(string='Credit Insurance Coverage Value')
	od_user_id = fields.Many2one('res.users', string="Somfy Salesperson")

	od_credit_euro = fields.Float(compute='_credit_debit_get',
		string='Total Receivable in euro', help="Total amount this customer owes you.",
		groups='account.group_account_invoice,account.group_account_readonly')
	od_over_due = fields.Boolean(string="Is Overdue", default=False, compute="od_get_overdue")
	od_somfy_credit_limit = fields.Float(string="Somfy credit limit")
	# od_exclude_dso = fields.Boolean(string="Exclude from DSO report", default=False)

	od_customer_segment = fields.Selection([('B2B','B2B'),('B2C','B2C'),('Service','Service')], string="Customer Segment", tracking=True)
	od_product_segment_id = fields.Many2many('od.product.segment', string="Product Segment", tracking=True)


	
	@api.depends_context('company')
	def _credit_debit_get(self):
		res = super(Partner, self)._credit_debit_get()
		tables, where_clause, where_params = self.env['account.move.line']._where_calc([
			('parent_state', '=', 'posted'),
			('company_id', '=', self.env.company.id)
		]).get_sql()

		where_params = [tuple(self.ids)] + where_params
		if where_clause:
			where_clause = 'AND ' + where_clause
		self._cr.execute("""SELECT account_move_line.partner_id, a.account_type, SUM(account_move_line.amount_residual_currency)
					  FROM """ + tables + """
					  LEFT JOIN account_account a ON (account_move_line.account_id=a.id)
					  WHERE a.account_type IN ('asset_receivable','liability_payable')
					  AND account_move_line.partner_id IN %s
					  AND account_move_line.reconciled IS NOT TRUE
					  AND account_move_line.currency_id=1
					  """ + where_clause + """
					  GROUP BY account_move_line.partner_id, a.account_type
					  """, where_params)
		treated = self.browse()
		for pid, type, val in self._cr.fetchall():
			partner = self.browse(pid)
			if type == 'asset_receivable':
				partner.od_credit_euro = val
				if partner not in treated:
					# partner.debit = False
					treated |= partner
			elif type == 'liability_payable':
				# partner.debit = -val
				if partner not in treated:
					partner.od_credit_euro = False
					treated |= partner
		euro_remaining = (self - treated)
		euro_remaining.od_credit_euro = False

		return res

	@api.depends_context('company')
	def od_get_overdue(self):
		for partner in self:
			today = fields.Date.context_today(self)
			# overdue qry
			over_due_qry = '''SELECT COALESCE(mv.invoice_date_due,Null) FROM account_move mv 
							  WHERE mv.invoice_date_due<'%s' AND mv.partner_id=%s AND mv.state='posted' AND mv.payment_state in ('not_paid','partial') AND mv.move_type='out_invoice' '''%(today, partner.id)

			# print("overrrrrrr",over_due_qry)
			self._cr.execute(over_due_qry)
			result = self._cr.fetchall()
			# print("prrrr",result)
			if result:
				partner.od_over_due=True
			else:
				partner.od_over_due=False









	@api.onchange('od_user_id')
	def od_update_user_id(self):
		for res in self:
			if res.od_user_id:
				res.user_id = res.od_user_id.id

	@api.model_create_multi
	def create(self, vals_list):
		# for vals in vals_list:
			# if vals.get('is_company') == True:
			# 	seq_obj = self.env['ir.sequence']
			# 	ref_num = seq_obj.next_by_code('res.partner')
			# 	partner = vals.get('name')
			# 	start = 0
			# 	limit = 4
			# 	if len(partner) > 3:
			# 		while True:
			# 			partner_name = partner.find(" ",start,limit)
			# 			if partner_name == -1 :
			# 				partner = partner[start:limit]
			# 				break
			# 			else:
			# 				start = partner_name + 1
			# 				limit = start + 4
			# 	vals['ref'] =str(partner) + ref_num
		res = super(Partner, self).create(vals_list)
		res.od_generate_ref_seq()
		return res

	def od_generate_ref_seq(self):
		if self.is_company == True:
			partner = self.name
			# print("ppppp",partner)
			if len(partner.split()) > 1:
				partner_split = partner.split()
				# code_name = partner_split[0][0]+partner_split[0][1]+partner_split[1][0]+partner_split[1][1]
				code_name=""
				# print("jjjjjjjj",partner_split)
				partner_split_name=[]

				for i in partner_split:
					print("iiii",i)
					if len(i)>=3:
						if i[0:3]=='AL-':
							i = i[3:]
					else:
						string=""
						for ele in i:
							string += ele
						if string == 'AL':
							continue

					# print("lass",i)
					partner_split_name.append(i)
				# print("kkkk",partner_split_name)

				for i in partner_split_name:
					second_len=0
					for j in i:
						if j.isalpha():
							code_name+=j
							second_len+=1
							if second_len==2:
								break;
					if len(code_name)==4:
						break;
			else:
				code_name = partner[0]+partner[1]
			# print("code_namecode_namecode_name",code_name)
			code_name = code_name.upper()
			sequence_id = self.sudo().env['ir.sequence'].search([('code','=',code_name)])
			if sequence_id:
				self.ref = self.sudo().env['ir.sequence'].next_by_code(code_name)
			else:
				seq_vals = {
				'name':"Orchid Partner Reference Sequence "+str(code_name),
				'code':code_name,
				'prefix':code_name,
				'padding':4,
				}
				sequence_id = self.sudo().env['ir.sequence'].create(seq_vals)
				self.ref = self.sudo().env['ir.sequence'].next_by_code(code_name)
			# print("kkkkkkkkk",self.ref)





class CountrySateInher(models.Model):
	_inherit = "res.country.state"

	od_arabic_name = fields.Char(string='Arabic Name')


class CountryInher(models.Model):
	_inherit = "res.country"

	od_arabic_name = fields.Char(string='Arabic Name')
	od_business_unit = fields.Selection([('GCC-B2K','GCC-B2K'),('GCC-UQO','GCC-UQO'),('GCC-KSA','GCC-KSA')], string="Business Unit", tracking=True)


# class AccountPaymentTermInher(models.Model):
# 	_inherit = "account.payment.term"

# 	od_arabic_name = fields.Char(string='Arabic Name')
# 	od_arabic_note = fields.Text(string='Arabic Description on the Invoice')

