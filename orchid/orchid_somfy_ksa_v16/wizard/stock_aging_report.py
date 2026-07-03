# -*- coding: utf-8 -*-

from odoo import models, fields, api, _,tools
from datetime import datetime
from odoo.exceptions import UserError, Warning
from io import BytesIO
import base64
import pandas as pd
import xlsxwriter
from dateutil.relativedelta import relativedelta

class OrchidStockAgingReport(models.TransientModel):
	_name = 'od.stock.aging.report'
	_description = 'Stock Aging Report'

	date_from = fields.Date(string='Start Date',required=True)
	company_id = fields.Many2one('res.company', string="Company",  default=lambda self: self.env.user.company_id.id)
	period_length = fields.Integer(string='Period Length (days)', required=True, default=30)
	location_ids = fields.Many2many('stock.location',string='Locations',required=True,check_company=True)
	excel_file = fields.Binary(string='Excel Report',readonly="1")
	file_name = fields.Char(string='Excel File',readonly="1")
	category = fields.Boolean(string="Category")
	summary = fields.Boolean(string="Summary")


	def _fifo_balance_ageing(self, values):
		"""
		Convert movement-based ageing into balance-based FIFO ageing
		and calculate values so that they exactly match the system.
		"""
		fifo = {str(i): 0.0 for i in range(5)}
		fifo.update({'v_' + str(i): 0.0 for i in range(5)})

		remaining_qty = values['total']
		remaining_val = values['v_total']

		# Work from newest (0-30) → oldest (+120)
		for i in reversed(range(5)):
			# if values['categ_id']==149:
			# 	print("remmm",remaining_qty, remaining_val)
			if remaining_qty <= 0:
				break

			qty = max(values[str(i)], 0.0)
			val = max(values['v_' + str(i)], 0.0)

			take_qty = min(qty, remaining_qty)

			if take_qty == qty:
				# Take full value if full qty is taken
				take_val = val
			else:
				# If only part of the qty is taken, take proportional value from remaining_val
				take_val = min(val, remaining_val)

			fifo[str(i)] = take_qty
			fifo['v_' + str(i)] = take_val

			remaining_qty -= take_qty
			remaining_val -= take_val

		fifo['total'] = sum(fifo[str(i)] for i in range(5))
		fifo['v_total'] = sum(fifo['v_' + str(i)] for i in range(5))
		fifo['categ_id'] = values['categ_id']
		fifo['categ'] = values['categ']
		# if values['categ_id']==149:
		# 	print("fifff",fifo)
		# 	print("valuess",values)

		return fifo



	def generate_excel(self):
		print("excellllllllllllllllllllllllllll")

		output = BytesIO()
		workbook = xlsxwriter.Workbook(output)
		filename='Stockagingreport.xlsx'
		data = {}
		cr = self._cr
		if self.period_length<=0:
			raise Warning(_('You must set a period length greater than 0.'))
		if not self.date_from:
			raise Warning(_('You must set a start date.'))

		start = datetime.strptime(str(self.date_from), "%Y-%m-%d")
		periods = {}
		period_length = self.period_length
		date_from = self.date_from
		start = datetime.strptime(str(self.date_from), "%Y-%m-%d")
		start = datetime.strptime(str(date_from), "%Y-%m-%d")
		for i in range(5)[::-1]:
			stop = start - relativedelta(days=period_length)
			periods[str(i)] = {
				'name': (i!=0 and (str((5-(i+1)) * period_length) + '-' + str((5-i) * period_length)) or ('+'+str(4 * period_length))),
				'stop': start.strftime('%Y-%m-%d'),
				'start': (i!=0 and stop.strftime('%Y-%m-%d') or False),
			}
			start = stop - relativedelta(days=1)
		data['form']=periods
		for i in range(5):
			if periods[str(i)]['start']:
				periods[str(i)]['start'] = datetime.strptime(
					periods[str(i)]['start'], "%Y-%m-%d"
				).date()
			if periods[str(i)]['stop']:
				periods[str(i)]['stop'] = datetime.strptime(
					periods[str(i)]['stop'], "%Y-%m-%d"
				).date()

		header=self.get_header_details(data)
		style1=workbook.add_format({'bold':True,'font_name':'Arial','font_size':11,'align':'center','valign':'vcenter'})
		style2=workbook.add_format({'bold':True,'font_name':'Arial','font_size':11,'bg_color':'#D7E4BC','align':'center','valign':'vcenter','border':1,'border_color':'#000000'})
		style3=workbook.add_format({'bold':True,'font_name':'Arial','font_size':11,'bg_color':'#ecf2e9'})
		style4=workbook.add_format({'bold':True,'font_name':'Arial','font_size':11,'bg_color':'#ecf2e9','align':'center'})
		row_num_style = workbook.add_format({'num_format': '#,##0.00'})
		row =0
		col =0
		sheet= workbook.add_worksheet('Stock Aging Report')
		head='Stock Aging Report - '+str(date_from)
		row_merge = row+1
		if self.category:
			col_merge =col+12
		else:
			# col_merge =col+14
			col_merge =col+16
		sheet.merge_range(row,col,row_merge,col_merge,head,style2)
		row = row+2
		col= 0
		for index,data in enumerate(header):
			if data in ('Products','Product Code','Product Category','Product Group', 'Date of Last Purchase', 'Date of Last Sales'):
				sheet.write(row,col,data,style1)
				col=col+1
			else:
				row_merge = row
				col_merge =col+1
				sheet.merge_range(row,col,row_merge,col_merge,data,style1)
				sheet.write(row+1,col,'Quantity',style4)
				sheet.write(row+1,col+1,'Value',style4)
				col=col+2
		location_ids = []
		if self.location_ids:
			for l in self.location_ids:
				location_ids.append(l.id)
		else:
			locations = self.env['stock.location'].search([('usage','=','internal'),('company_id','=',self.company_id.id)])
			for l in locations:
				location_ids.append(l.id)
		location_where = " "
		if len(location_ids)==1:
			location_where=" AND sl.id = " + str(location_ids[0])
		if len(location_ids) >1:
			location_where=" AND sl.id in " + str(tuple(location_ids))

		if not self.summary:
			print("hlooooooooooooooooooooooooo")
			query = ('''
				SELECT DISTINCT sl.id, UPPER(sl.name), UPPER(pl.name)
				FROM stock_valuation_layer AS sq
				left join stock_move sm on sm.id=sq.stock_move_id                                   
				left join stock_location  sl on sl.id = sm.location_id
				left join stock_location pl on pl.id=sl.location_id
				WHERE 
					(sq.create_date :: Date <= '%s' )
					 '''+location_where+'''
				ORDER BY UPPER(sl.name)''')%(date_from)
			cr.execute(query)
			locations_results = cr.fetchall()
			locations=[]
			for l in locations_results:
				loc_name=str(l[2])+"/"+str(l[1])
				y = list(l)
				y[1] = loc_name
				l = tuple(y)
				locations.append(l)
			query = ('''
				SELECT DISTINCT sl.id, UPPER(sl.name), UPPER(pl.name)
				FROM stock_valuation_layer AS sq
				left join stock_move sm on sm.id=sq.stock_move_id                                   
				left join stock_location  sl on sl.id = sm.location_dest_id
				left join stock_location pl on pl.id=sl.location_id
				WHERE 
					(sq.create_date :: Date <= '%s' )
					 '''+location_where+'''
				ORDER BY UPPER(sl.name)''')%(date_from)
			cr.execute(query)
			locations_results = cr.fetchall()
			# locations=[]
			for l in locations_results:
				loc_name=str(l[2])+"/"+str(l[1])
				y = list(l)
				y[1] = loc_name
				l = tuple(y)
				locations.append(l)
			locations = list(set(locations))
			total = []
			for i in range(7):
				total.append(0)
			v_total = []
			for i in range(7):
				v_total.append(0)
			if self.category:
				print("no summmmmmmmmmmmmmmm and categoryyyyyyyyyyyyyyy")
				sheet.set_column('A:A',30)
				sheet.set_column('B:B',15)
				sheet.set_column('C:C',15)
				sheet.set_column('D:D',15)
				sheet.set_column('E:E',15)
				sheet.set_column('F:F',15)
				sheet.set_column('G:G',15)
				sheet.set_column('H:H',15)
				sheet.set_column('I:I',15)
				sheet.set_column('J:J',15)
				sheet.set_column('K:K',15)
				sheet.set_column('L:L',15)
				sheet.set_column('M:M',15)
				for loc in locations:
					row=row+1
					col=0
					row_merge = row
					col_merge =col
					sheet.write(row,col,loc[1],style3)
					# location_where=" and ((sm.location_id = " + str(loc[0])+" or sm.location_dest_id = " + str(loc[0])+") or (sm.id is null and sq.account_move_id is not null))"
					location_where=" and ((sm.location_id = " + str(loc[0])+" or sm.location_dest_id = " + str(loc[0])+"))"
					if loc[0]==8:
						location_where=" and ((sm.location_id = " + str(loc[0])+" or sm.location_dest_id = " + str(loc[0])+") or (sm.id is null and sq.account_move_id is not null))"
					query = ('''
						SELECT DISTINCT pc.name as categ,pt.categ_id 
						FROM stock_valuation_layer AS sq
						left join product_product  pp on pp.id = sq.product_id
						left join product_template pt on pt.id=pp.product_tmpl_id
						left join product_category pc on pc.id=pt.categ_id
						left join stock_move sm on sm.id=sq.stock_move_id                                    
						WHERE 
							(sq.create_date :: Date <= '%s' ) and pt.type='product' 
							 '''+location_where+'''
						ORDER BY (pc.name)''')%(date_from)
					cr.execute(query)
					categorys = cr.dictfetchall()
					# put a total of 0
					for i in range(7):
						total.append(0)
					product_ids = [category['categ_id'] for category in categorys if category['categ_id']]
					lines = dict((category['categ_id'] or False, []) for category in categorys)
					history = []
					value_history = []
					for i in range(5):
						dates_query = 'sq.create_date :: Date'
						if periods[str(i)]['start'] and periods[str(i)]['stop']:
							dates_query += ' BETWEEN %s AND %s '
							args_list = (periods[str(i)]['start'], periods[str(i)]['stop'])
						elif periods[str(i)]['start']:
							dates_query += ' >= %s'
							args_list = (periods[str(i)]['start'],)
						else:
							dates_query += ' <= %s '
							args_list = (periods[str(i)]['stop'],)
						query = '''SELECT COALESCE(sum(sq.quantity),0),COALESCE(sum(sq.value),0),pc.name,pt.categ_id
									FROM stock_valuation_layer AS sq
									left join product_product pp on pp.id=sq.product_id
									left join product_template pt on pt.id=pp.product_tmpl_id   
									left join product_category pc on pc.id=pt.categ_id
									left join stock_move sm on sm.id=sq.stock_move_id                                   
									WHERE 
									''' + dates_query +" and pt.type='product'" + location_where+ ''' group by pc.name,pt.categ_id''' 
						cr.execute(query, args_list)
						category_qty = {}
						category_value = {}
						stock_data = cr.fetchall()
						for line in stock_data:
							categ_id = line[3] or False
							# if categ_id==149:
							# 	print("stock_data",line)
							# 	print(query,args_list)
							category_qty[categ_id] = 0.0
							category_qty[categ_id] += line[0]
							category_value[categ_id] = 0.0
							category_value[categ_id] += line[1]
							lines[categ_id].append({
									'line': line[2],
									'qty': line[0],
									'period': i + 1,
									'value':line[1]
									# 'cat':line[5]
									})
						history.append(category_qty)
						value_history.append(category_value)
					res = []
					for category in categorys:
						if category['categ_id'] is None:
							category['categ_id'] = False
						at_least_one_amount = False
						values = {}
						undue_amt = 0.0
						for i in range(5):
							during = False
							v_during = False
							if category['categ_id'] in history[i]:
								during = [history[i][category['categ_id']]]
							# Adding counter
							total[(i)] = total[(i)] + (during and during[0] or 0)
							values[str(i)] = during and during[0] or 0.0
							######## Value#####################
							if category['categ_id'] in value_history[i]:
								v_during = [value_history[i][category['categ_id']]]
							# Adding counter
							v_total[(i)] = v_total[(i)] + (v_during and v_during[0] or 0)
							values['v_'+str(i)] = v_during and v_during[0] or 0.0
						values['total'] = sum([values[str(i)] for i in range(5)])
						values['v_total'] = sum([values['v_'+str(i)] for i in range(5)])
						## Add for total
						total[(i + 1)] += values['total']
						values['categ_id'] = category['categ_id']
						if category['categ_id']:
							# browsed_product = self.env['product.product'].browse(product['product_id'])
							# values['name'] = product['upper'] 
							# values['code'] = product['default_code']
							values['categ'] = category['categ']
						else:
							# values['name'] = _('Unknown Product')
							# values['code'] = _('Unknown Product code')
							values['categ'] = _('Unknown Product Category')
							
						# if lines[category['categ_id']]:
						# 	res.append(values)
						fifo_values = self._fifo_balance_ageing(values)

						if lines[category['categ_id']]:
							res.append(fifo_values)
					for line in res:
						col=0
						row=row+1
						# sheet.write(row,col,line['name'])
						# col=col+1
						# sheet.write(row,col,line['code'])
						# col=col+1
						sheet.write(row,col,line['categ'])
						col=col+1
						sheet.write(row,col,line['4'])
						col=col+1
						sheet.write(row,col,line['v_4'],row_num_style)
						col=col+1
						sheet.write(row,col,line['3'])
						col=col+1
						sheet.write(row,col,line['v_3'],row_num_style)
						col=col+1
						sheet.write(row,col,line['2'])
						col=col+1
						sheet.write(row,col,line['v_2'],row_num_style)
						col=col+1
						sheet.write(row,col,line['1'])
						col=col+1
						sheet.write(row,col,line['v_1'],row_num_style)
						col=col+1
						sheet.write(row,col,line['0'])
						col=col+1
						sheet.write(row,col,line['v_0'],row_num_style)
						col=col+1
						sheet.write(row,col,line['total'])
						col=col+1
						sheet.write(row,col,line['v_total'],row_num_style)
					row=row+1
			else:
				print("elseeee not summaryyy not categoryy")
				sheet.set_column('A:A',60)
				sheet.set_column('B:B',30)
				sheet.set_column('C:C',30)
				sheet.set_column('D:D',30)
				sheet.set_column('E:E',30)

				for loc in locations:
					row += 1
					col = 0
					sheet.merge_range(row, col, row, col+4, loc[1], style3)

					# ------------------------------------------------------------------
					# 1️⃣ Get BALANCE qty & value per product for this location
					# ------------------------------------------------------------------
					balance_query = """
						SELECT
							sq.product_id,
							SUM(sq.quantity) AS qty,
							SUM(sq.value) AS value
						FROM stock_valuation_layer sq
						LEFT JOIN stock_move sm ON sm.id = sq.stock_move_id
						WHERE
							sq.create_date::date <= %s
							AND (
								sm.location_id = %s
								OR sm.location_dest_id = %s
								OR (
									%s = 8
									AND sm.id IS NULL
									AND sq.account_move_id IS NOT NULL
								)
							)
						GROUP BY sq.product_id
						HAVING
							SUM(sq.quantity) != 0
							OR (
								%s = 8
								AND SUM(sq.quantity) = 0
								AND SUM(sq.value) != 0
							)
					"""
					cr.execute(balance_query, (date_from, loc[0], loc[0], loc[0], loc[0]))

					balances = {
						r[0]: {'qty': r[1], 'value': r[2]}
						for r in cr.fetchall()
					}

					if not balances:
						continue

					# ------------------------------------------------------------------
					# 2️⃣ Fetch product master data
					# ------------------------------------------------------------------
					product_ids = tuple(balances.keys())
					product_query = """
						SELECT
							pp.id,
							UPPER(pt.name->>'en_US'),
							pp.default_code,
							pc.name
						FROM product_product pp
						JOIN product_template pt ON pt.id = pp.product_tmpl_id
						LEFT JOIN product_category pc ON pc.id = pt.categ_id
						WHERE pp.id IN %s
						ORDER BY pp.default_code
					"""
					cr.execute(product_query, (product_ids,))
					products = cr.fetchall()

					# ------------------------------------------------------------------
					# 3️⃣ FIFO AGEING ON BALANCE (incoming layers only)
					# ------------------------------------------------------------------
					for p in products:
						product_id, name, code, categ = p
						# ---------------------------------------------------
						# Last Purchase Date
						# ---------------------------------------------------
						last_po_date_qry = """
							SELECT svl.create_date
							FROM stock_valuation_layer svl
							JOIN stock_move sm ON sm.id = svl.stock_move_id
							JOIN stock_location dest ON dest.id = sm.location_dest_id
							WHERE sm.state = 'done'
							  AND svl.product_id = %s
							  AND svl.company_id = %s
							  AND svl.quantity > 0
							  AND dest.usage = 'internal'
							  AND sm.location_dest_id = %s
							  AND svl.create_date::date <= %s
							ORDER BY svl.create_date DESC
							LIMIT 1
						"""
						self._cr.execute(
							last_po_date_qry,
							(product_id, self.company_id.id, loc[0], date_from)
						)

						po_row = self._cr.fetchone()
						last_po = po_row[0] if po_row and po_row[0] else False




						# ---------------------------------------------------
						# Last Sale Date
						# ---------------------------------------------------
						last_so_query = """
							SELECT so.date_order
							FROM stock_move sm
							JOIN stock_location src ON src.id = sm.location_id
							JOIN stock_location dest ON dest.id = sm.location_dest_id
							JOIN sale_order_line sol ON sol.id = sm.sale_line_id
							JOIN sale_order so ON so.id = sol.order_id
							WHERE sm.state = 'done'
							  AND sm.product_id = %s
							  AND sm.location_id = %s
							  AND dest.usage = 'customer'
							  AND so.date_order::date <= %s
							ORDER BY so.date_order DESC
							LIMIT 1
						"""
						cr.execute(last_so_query, (product_id, loc[0], date_from))
						so_row = cr.fetchone()
						last_so = so_row[0] if so_row and so_row[0] else False


						balance_qty = balances[product_id]['qty']
						balance_val = balances[product_id]['value']

						values = {str(i): 0.0 for i in range(5)}
						values.update({'v_' + str(i): 0.0 for i in range(5)})

						# Incoming layers for FIFO
						in_query = """
							SELECT
								sq.create_date::date,
								sq.quantity,
								sq.value
							FROM stock_valuation_layer sq
							LEFT JOIN stock_move sm ON sm.id = sq.stock_move_id
							WHERE
								sq.quantity > 0
								AND sq.product_id = %s
								AND sq.create_date::date <= %s
								AND sm.location_dest_id = %s
							ORDER BY sq.create_date DESC
						"""
						cr.execute(in_query, (product_id, date_from, loc[0]))
						in_layers = cr.fetchall()

						remaining_qty = balance_qty

						for layer_date, layer_qty, layer_val in in_layers:
							if remaining_qty <= 0:
								break

							take_qty = min(layer_qty, remaining_qty)
							take_val = (take_qty / layer_qty) * layer_val if layer_qty else 0

							for i in range(5):
								p_start = periods[str(i)]['start']
								p_stop = periods[str(i)]['stop']
								if (not p_start and layer_date <= p_stop) or \
								   (p_start and p_start <= layer_date <= p_stop):
									values[str(i)] += take_qty
									values['v_' + str(i)] += take_val
									break

							remaining_qty -= take_qty


						# Recalculate total quantity and value
						values['total'] = sum(values[str(i)] for i in range(5))
						values['v_total'] = sum(values['v_' + str(i)] for i in range(5))

						# # ----- Location 8: Adjust total value to match x_studio_actualvalue -----
						# if loc[0] == 8:
						# 	product_obj = self.env['product.product'].browse(product_id)
						# 	actual_val = product_obj.x_studio_actualvalue or values['v_total']  # fallback to existing total if empty
						# 	diff = actual_val - values['v_total']
						# 	if abs(diff) > 0.0001 and values['total'] > 0:  # only adjust if difference exists
						# 		# Find bucket with max quantity
						# 		# max_bucket = max(range(5), key=lambda i: values[str(i)])
						# 		# Add difference proportionally to that bucket's value
						# 		values['v_' + str(max_bucket)] += diff
						# 		# Recalculate total value
						# 		values['v_total'] = sum(values['v_' + str(i)] for i in range(5))

						# ----- Location 8: Adjust total value to match x_studio_actualvalue -----
						if loc[0] == 8:
							product_obj = self.env['product.product'].browse(product_id)
							actual_val = product_obj.x_studio_actualvalue or values['v_total']
							diff = actual_val - values['v_total']

							if abs(diff) > 0.0001 and values['total'] > 0:
								# Find non-zero quantity buckets
								non_zero_buckets = [i for i in range(5) if values[str(i)] > 0]

								if non_zero_buckets:
									# Minimum non-zero quantity bucket
									min_bucket = min(non_zero_buckets, key=lambda i: values[str(i)])

									# Apply adjustment to that bucket
									values['v_' + str(min_bucket)] += diff

									# Recalculate total value
									values['v_total'] = sum(values['v_' + str(i)] for i in range(5))
						# ------------------------------------------------------------------------

						# Write to Excel
						row += 1
						col = 0
						sheet.write(row, col, name)
						col += 1
						sheet.write(row, col, code)
						col += 1
						sheet.write(row, col, categ)
						# col += 3  # skip extra columns
						col +=1
						# Last Purchase Date
						sheet.write(
							row, col,
							last_po.strftime('%Y-%m-%d') if last_po else ''
						)
						col += 1
						# Last Sale Date
						sheet.write(
							row, col,
							last_so.strftime('%Y-%m-%d') if last_so else ''
						)
						col += 1

						

						for i in reversed(range(5)):
							sheet.write(row, col, values[str(i)])
							col += 1
							sheet.write(row, col, values['v_' + str(i)], row_num_style)
							col += 1

						sheet.write(row, col, values['total'])
						col += 1
						sheet.write(row, col, values['v_total'], row_num_style)


					row += 1

		else:
			print("big elseeeeeeeeeeeeee")
			total = []
			for i in range(7):
				total.append(0)
			v_total = []
			for i in range(7):
				v_total.append(0)
			if self.category:
				sheet.set_column('A:A',30)
				sheet.set_column('B:B',15)
				sheet.set_column('C:C',15)
				sheet.set_column('D:D',15)
				sheet.set_column('E:E',15)
				sheet.set_column('F:F',15)
				sheet.set_column('G:G',15)
				sheet.set_column('H:H',15)
				sheet.set_column('I:I',15)
				sheet.set_column('J:J',15)
				sheet.set_column('K:K',15)
				sheet.set_column('L:L',15)
				sheet.set_column('M:M',15)
				# for loc in locations:
				row=row+1
				col=0
				# row_merge = row
				# col_merge =col
				# sheet.write(row,col,loc[1],style3)
				# location_where=" and sq.location_id = " + str(loc[0])
				if len(location_ids)==1:
					location_where=" and ((sm.location_id = " + str(loc[0])+" or sm.location_dest_id = " + str(loc[0])+") or (sm.id is null and sq.account_move_id is not null))"
				if len(location_ids) >1:
					location_where=" and ((sm.location_id in " + str(tuple(location_ids))+" or sm.location_dest_id in " + str(tuple(location_ids))+") or (sm.id is null and sq.account_move_id is not null))"
				# print("fgtttt",location_where)
				query = ('''
					SELECT DISTINCT pc.name as categ,pt.categ_id 
					FROM stock_valuation_layer AS sq
					left join product_product  pp on pp.id = sq.product_id
					left join product_template pt on pt.id=pp.product_tmpl_id
					left join product_category pc on pc.id=pt.categ_id   
					left join stock_move sm on sm.id=sq.stock_move_id                                 
					WHERE 
						(sq.create_date :: Date <= '%s' )
						 '''+location_where+'''
					ORDER BY (pc.name)''')%(date_from)
				cr.execute(query)
				categorys = cr.dictfetchall()
				# put a total of 0
				for i in range(7):
					total.append(0)
				product_ids = [category['categ_id'] for category in categorys if category['categ_id']]
				lines = dict((category['categ_id'] or False, []) for category in categorys)
				history = []
				value_history = []
				for i in range(5):
					dates_query = 'sq.create_date :: Date'
					if periods[str(i)]['start'] and periods[str(i)]['stop']:
						dates_query += ' BETWEEN %s AND %s '
						args_list = (periods[str(i)]['start'], periods[str(i)]['stop'])
					elif periods[str(i)]['start']:
						dates_query += ' >= %s'
						args_list = (periods[str(i)]['start'],)
					else:
						dates_query += ' <= %s '
						args_list = (periods[str(i)]['stop'],)
					query = '''SELECT COALESCE(sum(sq.quantity),0),COALESCE(sum(sq.value),0),pc.name,pt.categ_id
								FROM stock_valuation_layer AS sq
								left join product_product pp on pp.id=sq.product_id
								left join product_template pt on pt.id=pp.product_tmpl_id   
								left join product_category pc on pc.id=pt.categ_id     
								left join stock_move sm on sm.id=sq.stock_move_id                                   
								WHERE 
								''' + dates_query +" and pt.type='product'" + location_where+ ''' group by pc.name,pt.categ_id''' 
					cr.execute(query, args_list)
					category_qty = {}
					category_value = {}
					stock_data = cr.fetchall()
					for line in stock_data:
						categ_id = line[3] or False
						category_qty[categ_id] = 0.0
						category_qty[categ_id] += line[0]
						category_value[categ_id] = 0.0
						category_value[categ_id] += line[1]
						lines[categ_id].append({
								'line': line[2],
								'qty': line[0],
								'period': i + 1,
								'value':line[1]
								# 'cat':line[5]
								})
					history.append(category_qty)
					value_history.append(category_value)
				res = []
				for category in categorys:
					if category['categ_id'] is None:
						category['categ_id'] = False
					at_least_one_amount = False
					values = {}
					undue_amt = 0.0
					for i in range(5):
						during = False
						v_during = False
						if category['categ_id'] in history[i]:
							during = [history[i][category['categ_id']]]
						# Adding counter
						total[(i)] = total[(i)] + (during and during[0] or 0)
						values[str(i)] = during and during[0] or 0.0
						######## Value#####################
						if category['categ_id'] in value_history[i]:
							v_during = [value_history[i][category['categ_id']]]
						# Adding counter
						v_total[(i)] = v_total[(i)] + (v_during and v_during[0] or 0)
						values['v_'+str(i)] = v_during and v_during[0] or 0.0
					values['total'] = sum([values[str(i)] for i in range(5)])
					values['v_total'] = sum([values['v_'+str(i)] for i in range(5)])
					## Add for total
					total[(i + 1)] += values['total']
					values['categ_id'] = category['categ_id']
					if category['categ_id']:
						# browsed_product = self.env['product.product'].browse(product['product_id'])
						# values['name'] = product['upper'] 
						# values['code'] = product['default_code']
						values['categ'] = category['categ']
					else:
						# values['name'] = _('Unknown Product')
						# values['code'] = _('Unknown Product code')
						values['categ'] = _('Unknown Product Category')
						
					if lines[category['categ_id']]:
						res.append(values)
				for line in res:
					col=0
					row=row+1
					# sheet.write(row,col,line['name'])
					# col=col+1
					# sheet.write(row,col,line['code'])
					# col=col+1
					sheet.write(row,col,line['categ'])
					col=col+1
					sheet.write(row,col,line['4'])
					col=col+1
					sheet.write(row,col,line['v_4'],row_num_style)
					col=col+1
					sheet.write(row,col,line['3'])
					col=col+1
					sheet.write(row,col,line['v_3'],row_num_style)
					col=col+1
					sheet.write(row,col,line['2'])
					col=col+1
					sheet.write(row,col,line['v_2'],row_num_style)
					col=col+1
					sheet.write(row,col,line['1'])
					col=col+1
					sheet.write(row,col,line['v_1'],row_num_style)
					col=col+1
					sheet.write(row,col,line['0'])
					col=col+1
					sheet.write(row,col,line['v_0'],row_num_style)
					col=col+1
					sheet.write(row,col,line['total'])
					col=col+1
					sheet.write(row,col,line['v_total'],row_num_style)
				row=row+1
			else:
				print("summary not catgeryyyyyyyy")
				sheet.set_column('A:A',60)
				sheet.set_column('B:B',30)
				sheet.set_column('C:C',30)
				sheet.set_column('D:D',30)
				sheet.set_column('E:E',30)
				row=row+1
				col=0
				if len(location_ids)==1:
					location_where=" and ((sm.location_id = " + str(loc[0])+" or sm.location_dest_id = " + str(loc[0])+") or (sm.id is null and sq.account_move_id is not null))"
				if len(location_ids) >1:
					location_where=" and ((sm.location_id in " + str(tuple(location_ids))+" or sm.location_dest_id in " + str(tuple(location_ids))+") or (sm.id is null and sq.account_move_id is not null))"
				# print("fgtttt",location_where)
				query = ('''
					SELECT DISTINCT sq.product_id, UPPER(pt.name ->> 'en_US'),pp.default_code,pc.name as categ
					FROM stock_valuation_layer AS sq
					left join product_product  pp on pp.id = sq.product_id
					left join product_template pt on pt.id=pp.product_tmpl_id
					left join product_category pc on pc.id=pt.categ_id 
					left join stock_move sm on sm.id=sq.stock_move_id                                   
					WHERE 
						(sq.create_date :: Date<= '%s' ) and pt.type='product' 
						 '''+location_where+'''
					ORDER BY UPPER(pt.name ->> 'en_US')''')%(date_from)
				cr.execute(query)
				products = cr.dictfetchall()
				# put a total of 0
				for i in range(7):
					total.append(0)
				product_ids = [product['product_id'] for product in products if product['product_id']]
				lines = dict((product['product_id'] or False, []) for product in products)
				history = []
				value_history = []
				for i in range(5):
					dates_query = 'sq.create_date :: Date'
					if periods[str(i)]['start'] and periods[str(i)]['stop']:
						dates_query += ' BETWEEN %s AND %s '
						args_list = (periods[str(i)]['start'], periods[str(i)]['stop'])
					elif periods[str(i)]['start']:
						dates_query += ' >= %s'
						args_list = (periods[str(i)]['start'],)
					else:
						dates_query += ' <= %s '
						args_list = (periods[str(i)]['stop'],)
					query = '''SELECT sq.product_id,pt.name,COALESCE(sum(sq.quantity),0),pp.default_code,COALESCE(sum(sq.value),0)
								FROM stock_valuation_layer AS sq
								left join product_product pp on pp.id=sq.product_id
								left join product_template pt on pt.id=pp.product_tmpl_id  
								left join stock_move sm on sm.id=sq.stock_move_id    
								WHERE 
								''' + dates_query +" and pt.type='product' "+ location_where+ ''' group by sq.product_id,pt.name,pp.default_code'''   
					cr.execute(query, args_list)
					product_qty = {}
					product_value = {}
					stock_data = cr.fetchall()
					for line in stock_data:
						product_id = line[0] or False
						product_qty[product_id] = 0.0
						product_qty[product_id] += line[2]
						product_value[product_id] = 0.0
						product_value[product_id] += line[4]
						lines[product_id].append({
								'line': line[1],
								'qty': line[2],
								'period': i + 1,
								'code':line[3],
								'value':line[4]
								# 'cat':line[5]
								})
					history.append(product_qty)
					value_history.append(product_value)
				res = []
				for product in products:
					if product['product_id'] is None:
						product['product_id'] = False
					at_least_one_amount = False
					values = {}
					undue_amt = 0.0
					for i in range(5):
						during = False
						v_during = False
						if product['product_id'] in history[i]:
							during = [history[i][product['product_id']]]
						# Adding counter
						total[(i)] = total[(i)] + (during and during[0] or 0)
						values[str(i)] = during and during[0] or 0.0
						######## Value#####################
						if product['product_id'] in value_history[i]:
							v_during = [value_history[i][product['product_id']]]
						# Adding counter
						v_total[(i)] = v_total[(i)] + (v_during and v_during[0] or 0)
						values['v_'+str(i)] = v_during and v_during[0] or 0.0
					values['total'] = sum([values[str(i)] for i in range(5)])
					values['v_total'] = sum([values['v_'+str(i)] for i in range(5)])
					## Add for total
					total[(i + 1)] += values['total']
					values['product_id'] = product['product_id']
					if product['product_id']:
						# browsed_product = self.env['product.product'].browse(product['product_id'])
						last_po_query = """SELECT po.date_approve FROM purchase_order po 
											LEFT JOIN purchase_order_line pl ON pl.order_id = po.id
											WHERE pl.product_id=%s
											ORDER BY po.date_approve DESC
											limit 1 """%(product['product_id'])
						self._cr.execute(last_po_query)
						po_date = self._cr.fetchall()
						po_date = [p[0] for p in po_date if p[0]!=None]
						last_po = ''
						if po_date:
							last_po = po_date[0]

						last_so_query = """SELECT so.date_order FROM sale_order so 
											LEFT JOIN sale_order_line sl ON sl.order_id = so.id
											WHERE sl.product_id=%s
											ORDER BY so.date_order DESC
											limit 1 """%(product['product_id'])
						self._cr.execute(last_so_query)
						so_date = self._cr.fetchall()
						so_date = [p[0] for p in so_date if p[0]!=None]
						last_so = ''
						if so_date:
							last_so = so_date[0]

						values['name'] = product['upper'] 
						values['code'] = product['default_code']
						values['categ'] = product['categ']
						values['last_po'] = last_po
						values['last_so'] = last_so
					else:
						values['name'] = _('Unknown Product')
						values['code'] = _('Unknown Product code')
						values['categ'] = _('Unknown Product Category')
						values['last_po'] = _('Unknown Date')
						values['last_so'] = _('Unknown Date')
						
					if lines[product['product_id']]:
						res.append(values)
				for line in res:
					col=0
					row=row+1
					sheet.write(row,col,line['name'])
					col=col+1
					sheet.write(row,col,line['code'])
					col=col+1
					sheet.write(row,col,line['categ'])
					col=col+1
					last_po = ""
					if line['last_po']:
						last_po = line['last_po'].date()
					sheet.write(row,col,str(last_po))
					col=col+1
					last_so = ""
					if line['last_so']:
						last_so = line['last_so'].date()
					sheet.write(row,col,str(last_so))
					col=col+1
					sheet.write(row,col,line['4'])
					col=col+1
					sheet.write(row,col,line['v_4'],row_num_style)
					col=col+1
					sheet.write(row,col,line['3'])
					col=col+1
					sheet.write(row,col,line['v_3'],row_num_style)
					col=col+1
					sheet.write(row,col,line['2'])
					col=col+1
					sheet.write(row,col,line['v_2'],row_num_style)
					col=col+1
					sheet.write(row,col,line['1'])
					col=col+1
					sheet.write(row,col,line['v_1'],row_num_style)
					col=col+1
					sheet.write(row,col,line['0'])
					col=col+1
					sheet.write(row,col,line['v_0'],row_num_style)
					col=col+1
					sheet.write(row,col,line['total'])
					col=col+1
					sheet.write(row,col,line['v_total'],row_num_style)
				row=row+1




		# writer = pd.ExcelWriter(filename, engine='xlsxwriter')
		# writer.save()
		workbook.close()
		output.seek(0)
		excel_file = base64.encodebytes(output.getvalue())
		self.write({'excel_file':excel_file,'file_name':filename})
		output.close()
		return {
			  'view_type': 'form',
			  "view_mode": 'form',
			  'res_model': 'od.stock.aging.report',
			  'res_id': self.id,
			  'type':'ir.actions.act_window',
			  'target': 'new'
			  }

	def get_header_details(self,data):
		period1 = str(data['form']['4']['name'])
		period2 = str(data['form']['3']['name'])
		period3 = str(data['form']['2']['name'])
		period4 = str(data['form']['1']['name'])
		period5 = str(data['form']['0']['name'])
		if self.category:
			header = ['Product Category',period1,period2,period3,period4,period5,'Total']
		else:
			header = ['Products','Product Code','Product Category','Date of Last Purchase', 'Date of Last Sales',period1,period2,period3,period4,period5,'Total']
		return header