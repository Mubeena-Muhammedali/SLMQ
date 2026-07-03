from odoo import api, fields, models, _

class AccountInvoice(models.Model):
	_inherit = 'account.move'

	def od_get_exchange_rate(self):
		exchange_rate=1
		exchange_rate_id = self.env['res.currency.rate'].search([('currency_id','=',self.currency_id.id),('name','<=',self.invoice_date)],limit=1, order='name desc')
		if exchange_rate_id:
			exchange_rate=exchange_rate_id.inverse_company_rate
		return exchange_rate
		
	def get_hscode_data(self):
		data_ls = []
		cr = self.env.cr
		data_qry = (''' SELECT pt.orchid_hscode_id,ail.orchid_country_id
						--,ph.description,SUM(quantity + od_free_qty) AS qty
						--SUM(price_total) as total 
						FROM account_move_line ail
							LEFT JOIN product_product pp ON pp.id = ail.product_id
							LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
							--LEFT JOIN orchid_product_hscode ph ON ph.id = pt.orchid_hscode_id
						WHERE move_id = %s and pt.orchid_hscode_id is not null
						GROUP BY pt.orchid_hscode_id,ail.orchid_country_id ''')%(self.id)
		qry_rslt = cr.execute(data_qry)
		qry_rslt = cr.fetchall()
		line_ids = self.env['account.move.line'].search([('move_id','=',self.id)])
		for res in qry_rslt:
			dat_ls = []
			qty = 0
			total = 0
			wt = 0
			qty_service_l = 0
			total_service_l = 0
			wt_service_l = 0
			for line in line_ids:
				if line.product_id.orchid_hscode_id.id == res[0] and line.orchid_country_id.id == res[1] and line.product_id.type in ('product','consu'):
					hscode = line.product_id.orchid_hscode_id.name or ' '
					country = line.orchid_country_id.name or ' '
					description = line.product_id.orchid_hscode_id.description
					# qty = qty+line.quantity + line.od_free_qty
					qty = qty+line.quantity + line.od_free_qty+line.od_adjustment_qty
					# total = total + line.price_total
					# added this coe on 26jun
					if (line.quantity==0 and (line.od_free_qty!=0 or line.od_adjustment_qty!=0)):
						print("yepssssssssssssss")
						t_qty=line.od_free_qty+line.od_adjustment_qty
						total = total + (line.price_unit*t_qty)
					else:
						total = total + line.price_total
					wt = wt + line.od_gross_weight

				elif line.product_id.type == 'service':
					# qty_service_l = qty_service_l+line.quantity + line.od_free_qty
					qty_service_l = qty_service_l+line.quantity + line.od_free_qty + line.od_adjustment_qty
					total_service_l = total_service_l + line.price_total
					wt_service_l = wt_service_l + line.od_gross_weight
			dat_ls.append(hscode)
			dat_ls.append(country)
			dat_ls.append(description)
			dat_ls.append(qty)
			dat_ls.append(total)
			dat_ls.append(wt)
			data_ls.append(dat_ls)
		len_ls = len(data_ls)
		len_ls = len_ls -1
		# data_ls[len_ls][3] = data_ls[len_ls][3] + qty_service_l
		data_ls[len_ls][4] = data_ls[len_ls][4]	+ total_service_l
		data_ls[len_ls][5] = data_ls[len_ls][5]	+ wt_service_l
		return data_ls


	def get_discount_data(self):
		data_ls = []
		cr = self.env.cr
		data_qry = (''' SELECT pt.orchid_hscode_id,ail.orchid_country_id
						--,ph.description,SUM(quantity + od_free_qty) AS qty
						--SUM(price_total) as total 
						FROM account_move_line ail
							LEFT JOIN product_product pp ON pp.id = ail.product_id
							LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
							--LEFT JOIN orchid_product_hscode ph ON ph.id = pt.orchid_hscode_id
						WHERE move_id = %s and pt.orchid_hscode_id is not null
						GROUP BY pt.orchid_hscode_id,ail.orchid_country_id ''')%(self.id)
		qry_rslt = cr.execute(data_qry)
		qry_rslt = cr.fetchall()
		line_ids = self.env['account.move.line'].search([('move_id','=',self.id)])
		less_discount=0
		for res in qry_rslt:
			for line in line_ids:
				if line.product_id.orchid_hscode_id.id == res[0] and line.orchid_country_id.id == res[1] and line.product_id.type in ('product','consu'):
					if (line.quantity==0 and (line.od_free_qty!=0 or line.od_adjustment_qty!=0)):
						t_qty=line.od_free_qty+line.od_adjustment_qty
						less_discount=less_discount+(line.price_unit*t_qty)
		return less_discount

