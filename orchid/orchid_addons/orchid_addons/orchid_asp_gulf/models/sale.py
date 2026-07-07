# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
	_inherit = 'sale.order'

	@api.model
	def default_get(self, fields):
		result = super(SaleOrder, self).default_get(fields)
		result['od_sale_terms'] = "<div style='background-color:#B0C4DE;'><b><span>Terms &amp; Conditions</span></b></div><div>Validity : 15 days<br/>Payment Terms : In Advance<br/>Delivery : Within 2-3 days from Confirmation</div>"
		result['od_service_commitments'] = "<div style='background-color:#B0C4DE;'><b><span>SERVICE COMMITMENTS &amp; EXCLUSIONS</span></b></div><br/><br/>"
		return result

	od_contact_id = fields.Many2one('res.partner', string="Contact Person", ondelete='restrict', domain="[('parent_id','=',partner_id)]", help="Partner contact person")
	od_exchange_rate = fields.Float(digits=0, default=1.0,string="Exchange Rate")
	od_sale_terms = fields.Html(string="Terms and Conditions")
	od_service_commitments = fields.Html(string="Service Commitments & Exclusions")
	od_incl_service_commitments = fields.Boolean(string="Incl. Service Commitments", help="Include Service Commitments and Exclusions in the print", default=False)
	print_options = fields.Selection([('sale','Order'),('proforma','Proforma Invoice')],string="Print Option", default='proforma')
	od_contract_id=fields.Many2one('od.asp.contract', string="Contract", domain="[('partner_id','=',partner_id)]", copy=False)
	od_primary_quotation = fields.Boolean(string="Primary Quotation", default=False)

	
	@api.onchange('partner_id')
	def od_onchange_exchange_rate(self):
		for order in self:
			order.od_exchange_rate=order.partner_id and order.partner_id.od_exchange_rate
			
	@api.onchange('pricelist_id')
	def od_onchange_pricelist(self):
		for order in self:
			if order.pricelist_id:
				if order.pricelist_id.currency_id.id==2:
					order.od_exchange_rate=3.68
				else:
					order.od_exchange_rate=1
					

	def od_open_contracts(self):
		contract_id = self.mapped('od_contract_id')
		get_qry = '''SELECT od_asp_contract_id FROM od_asp_contract_sale_order_rel WHERE sale_order_id=%s'''%(self.id)
		self._cr.execute(get_qry)
		contract_ids = []
		contract_ids = self._cr.fetchall()
		if contract_ids:
			contract_ids = [z[0] for z in contract_ids]
		contract_ids.append(contract_id.id)
		contract_ids = list(set(contract_ids))

		action = self.env["ir.actions.actions"]._for_xml_id("orchid_asp_gulf.action_od_asp_contract_view")
		if len(contract_ids) == 1:
			form_view = [(self.env.ref('orchid_asp_gulf.od_asp_contract_form_view').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
			action['res_id'] = contract_id.id

			# checking if sale_line_ids is present in the contract ,if not link
			line_ids=[line.order_line_id.id for line in contract_id.contract_line_ids]
			order_ids = [o.id for o in contract_id.sale_order_ids]
			if contract_id.state not in ('inactive','terminate'):
				for line in self.order_line.filtered(lambda r: r.display_type==False and r.product_uom_qty>0):
					if line.id not in line_ids:
						tax_ls=[]
						for t in line.tax_id:
							tax_ls.append(t.id)

						vals={
						'sequence':line.sequence,
						'effective_date':fields.date.today(),
						'billing_from':fields.date.today(),
						'acculde':False if line.od_frequency==1 else True,
						'billing_to':contract_id.date_to,
						'billing_cycle':'one_time' if line.od_frequency==1 else False,
						'product_id':line.product_id.id,
						'name':line.name,
						'price_unit':line.price_unit,
						'price_subtotal':line.price_subtotal,
						'price_total':line.price_total,
						'price_tax':line.price_tax,
						'tax_id':[(6,0,tax_ls)],
						'discount':line.discount,
						'product_uom_qty':line.product_uom_qty,
						'product_uom':line.product_uom.id,
						'order_line_id':line.id,
						'frequency':line.od_frequency,
						'order_id':contract_id.id,
						}
						self.env['od.asp.contract.line'].create(vals)
				if self.id not in order_ids:
					order_ids.append(self.id)
					contract_id.sale_order_ids=[(6,0,order_ids)]

		elif len(contract_ids)>1:

			action['domain'] = [('id', 'in', contract_ids)]

			# create lines in progress contract
			# checking if sale_line_ids is present in the contract ,if not link
			line_ids=[line.order_line_id.id for line in contract_id.contract_line_ids]
			order_ids = [o.id for o in contract_id.sale_order_ids]
			if contract_id.state not in ('inactive','terminate'):
				for line in self.order_line.filtered(lambda r: r.display_type==False and r.product_uom_qty>0):
					if line.id not in line_ids:
						tax_ls=[]
						for t in line.tax_id:
							tax_ls.append(t.id)

						vals={
						'sequence':line.sequence,
						'effective_date':fields.date.today(),
						'billing_from':fields.date.today(),
						'acculde':False if line.od_frequency==1 else True,
						'billing_to':contract_id.date_to,
						'billing_cycle':'one_time' if line.od_frequency==1 else False,
						'product_id':line.product_id.id,
						'name':line.name,
						'price_unit':line.price_unit,
						'price_subtotal':line.price_subtotal,
						'price_total':line.price_total,
						'price_tax':line.price_tax,
						'tax_id':[(6,0,tax_ls)],
						'discount':line.discount,
						'product_uom_qty':line.product_uom_qty,
						'product_uom':line.product_uom.id,
						'order_line_id':line.id,
						'frequency':line.od_frequency,
						'order_id':contract_id.id,
						}
						self.env['od.asp.contract.line'].create(vals)
				if self.id not in order_ids:
					order_ids.append(self.id)
					contract_id.sale_order_ids=[(6,0,order_ids)]
		else:
			form_view = [(self.env.ref('orchid_asp_gulf.od_asp_contract_form_view').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
		print("kkkcc",len(self))
		if len(self) == 1:
			print("hereeeee?????")
			line_ids=[]
			for line in self.order_line.filtered(lambda r: r.display_type==False and r.product_uom_qty>0):
				tax_ls=[]
				for t in line.tax_id:
					tax_ls.append(t.id)

				vals={
				'sequence':line.sequence,
				'product_id':line.product_id.id,
				'name':line.name,
				'price_unit':line.price_unit,
				'price_subtotal':line.price_subtotal,
				'price_total':line.price_total,
				'price_tax':line.price_tax,
				'tax_id':[(6,0,tax_ls)],
				'discount':line.discount,
				'product_uom_qty':line.product_uom_qty,
				'product_uom':line.product_uom.id,
				'order_line_id':line.id,
				'frequency':line.od_frequency,
				'billing_cycle':'one_time' if line.od_frequency==1 else False,
				'acculde':False if line.od_frequency==1 else True,
				}
				line_ids.append((0,0,vals))

			context={
				'default_partner_id':self.partner_id.id,
				'default_contact_id':self.od_contact_id.id,
				'default_currency_id':self.currency_id.id,
				'default_client_order_ref':self.client_order_ref,
				'default_sam_id':self.user_id.id,
				'default_sale_order_ids':[(6,0,[self.id])],
				'default_contract_line_ids':line_ids,
				'default_od_exchange_rate':self.od_exchange_rate,
				'default_analytic_account_id':self.analytic_account_id.id,
			}

		action['context'] = context
		return action





	def action_cancel(self):
		result=super(SaleOrder, self).action_cancel()
		if self.opportunity_id:
			if self.opportunity_id.stage_id.id==4:
				raise UserError(_("The lead has already been confirmed."))
			# unlinking contractline from the contract if not invoiced
			if self.od_contract_id:
				contract_lines_ids=self.od_contract_id.contract_line_ids.filtered(lambda r: r.order_line_id.order_id==self.id)
				contract_lines_ids.unlink()
				sale_order_ids = [self.od_contract_id.sale_order_ids.filtered(lambda r: r.id==self.id)]
				self.od_contract_id.sale_order_ids=[(6,0,sale_order_ids)]
				self.od_contract_id=False
		return result

	def action_draft(self):
		result=super(SaleOrder, self).action_draft()
		if self.opportunity_id:
			if self.opportunity_id.stage_id.id==4:
				raise UserError(_("The lead has already been confirmed."))
			# unlinking contractline from the contract if not invoiced
			if self.od_contract_id:
				contract_lines_ids=self.od_contract_id.contract_line_ids.filtered(lambda r: r.order_line_id.order_id==self.id)
				contract_lines_ids.unlink()
				sale_order_ids = [self.od_contract_id.sale_order_ids.filtered(lambda r: r.id==self.id)]
				self.od_contract_id.sale_order_ids=[(6,0,sale_order_ids)]
				self.od_contract_id=False
		return result
		
	def action_confirm(self):
		# currency rate validation
		if self.currency_id.id==131 and self.od_exchange_rate!=1:
			raise UserError(_("Exchange rate should be 1 for AED currency!!!!"))
		if self.currency_id.id!=131 and self.od_exchange_rate==1:
			raise UserError(_("Currency is '%s'!!! Exchange rate should not be 1!!!")%(self.currency_id.name))
		'''upon confrirming a order the oppurtunity moves to won stage and all other so of the opportunity gets cancelled'''
		result=super(SaleOrder, self).action_confirm()
		if self.opportunity_id:
			self.opportunity_id.od_deal_closing_date = fields.Date.today()
			order_ids=self.opportunity_id.order_ids.filtered(lambda r:r.id!=self.id)
			if order_ids:
				order_ids.action_cancel()
			if self.currency_id.id==2:
				'''updating expected revenue of the opportunity if the so is usd so'''
				self.opportunity_id.expected_revenue = self.amount_total
			self.opportunity_id.action_set_won_rainbowman()
		# create analyrtic account
		if not self.analytic_account_id:
			analytic_id = self._create_analytic_account()
			self.analytic_account_id.update({'code':self.name})
		return result

	#fto correct discount	
	@api.depends('order_line.price_total')
	def _amount_all(self):
		"""
		Compute the total amounts of the SO.
		"""
		for order in self:
			amount_untaxed = amount_tax = amount_discount = 0.0
			for line in order.order_line:
				# print("line-------------",line.name,line.price_subtotal)
				amount_untaxed += line.price_subtotal
				amount_tax += line.price_tax
				amount_discount += (line.product_uom_qty * line.price_unit * line.od_frequency * line.discount) / 100
			# print("amountall****************",amount_untaxed,amount_tax)
			order.update({
				'amount_untaxed': amount_untaxed,
				'amount_tax': amount_tax,
				'amount_discount': amount_discount,
				'amount_total': amount_untaxed + amount_tax,
			})
			
	#fto correct discount	
	def supply_rate(self):

		for order in self:
			if order.discount_type == 'percent':
				for line in order.order_line:
					line.od_disc_amount = 0
					line.discount = order.discount_rate
			else:
				total = discount = 0.0
				for line in order.order_line:
					line.od_disc_amount = 0
					# total += round((line.product_uom_qty * line.price_unit))
					total += (line.product_uom_qty * line.price_unit * line.od_frequency)
				if order.discount_rate != 0:
					discount = (order.discount_rate / total) * 100
				else:
					discount = order.discount_rate
				for line in order.order_line:
					print("kkkkkkkkkkkkk",discount,total)
					line.discount = discount
					# line.onchange_disc_percent()

class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	od_description_sale = fields.Html(string="Description")
	od_frequency = fields.Integer(string="Frequency", default=1)
	od_disc_amount = fields.Float(string="Disc. Amount", digits='Discount')

	@api.onchange('od_disc_amount','price_unit','product_uom_qty')
	def onchange_disc_amt(self):
		for line in self:
			if line.order_id.discount_rate==0:
				price_unit = line.price_unit if line.price_unit !=0 else 1
				product_uom_qty = line.product_uom_qty if line.product_uom_qty !=0 else 1
				line.discount = ((line.od_disc_amount/(price_unit*product_uom_qty))*100)


	@api.onchange('product_id')
	def product_id_change(self):
		res= super(SaleOrderLine, self).product_id_change()
		if self.product_id:
			self.od_description_sale=self.name.replace(' ', "&nbsp;")
			self.od_description_sale=self.od_description_sale.replace('\n', "<br/>")
		return res

	@api.onchange('name')
	def od_description_change(self):
		if self.name and (not self.display_type):
			self.od_description_sale=self.name.replace(' ', "&nbsp;")
			self.od_description_sale=self.od_description_sale.replace('\n', "<br/>")


	@api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id','od_frequency')
	def _compute_amount(self):
		"""
		Compute the amounts of the SO line.override to include frequency
		"""
		for line in self:
			price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
			price = price*line.od_frequency if line.od_frequency else price #new line added
			# print("ppppppooooossssssssssssssss",price)
			taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
			line.update({
				'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
				'price_total': taxes['total_included'],
				'price_subtotal': taxes['total_excluded'],
			})
			if self.env.context.get('import_file', False) and not self.env.user.user_has_groups('account.group_account_manager'):
				line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])

	def _amount_by_group(self):
		"""
		override to include frequency
		"""
		print("newwwwwwwww amount byyyy")
		print("newwwwwwwww amount byyyy")
		print("newwwwwwwww amount byyyy")
		print("newwwwwwwww amount byyyy")
		for order in self:
			currency = order.currency_id or order.company_id.currency_id
			fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
			res = {}
			for line in order.order_line:
				price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
				price_reduce = price_reduce*line.od_frequency if line.od_frequency else price_reduce #new line added
				taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)['taxes']
				for tax in line.tax_id:
					group = tax.tax_group_id
					res.setdefault(group, {'amount': 0.0, 'base': 0.0})
					for t in taxes:
						if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
							res[group]['amount'] += t['amount']
							res[group]['base'] += t['base']
			res = sorted(res.items(), key=lambda l: l[0].sequence)
			order.amount_by_group = [(
				l[0].name, l[1]['amount'], l[1]['base'],
				fmt(l[1]['amount']), fmt(l[1]['base']),
				len(res),
			) for l in res]


	def _prepare_invoice_line(self, **optional_values):
		res = super(SaleOrderLine,self)._prepare_invoice_line(**optional_values)
		print("resssssssss",res)
		res['od_frequency'] = self.od_frequency
		print("affffresssssssss",res)
		return res

class Product(models.Model):
	_inherit='product.product'

	def get_product_multiline_description_sale(self):
		""" overidden to remove the product code from description
		"""
		# name = self.display_name
		name = self.name
		if self.description_sale:
			name += '\n' + self.description_sale

		return name