# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from collections import defaultdict

class SaleOrderLine(models.Model):
	_inherit = "sale.order.line"

	od_create_mo = fields.Boolean(string="Create MO", default=True)
	od_last_price = fields.Char("Last Price")
	od_customer_order = fields.Float(string="Customer Order")
	od_customer_uom_id = fields.Many2one('uom.uom', string="Customer UOM")
	od_mrp_ids = fields.One2many(
		'mrp.production', 
		'od_sale_order_line_id', 
		string="Production", 
		readonly=True, 
		copy=False
	)
	od_proof_request_ids = fields.One2many('od.proof.request','od_sale_line_id', string="Proof Request")
	od_cost = fields.Float(string="Cost", copy=False)
	od_total_cost = fields.Float(string="Total Cost", copy=False)

	od_margin = fields.Float(
		string="Margin %", compute="od_compute_margin", store=True)

	od_qty_on_hand = fields.Float(
        string="Qty On Hand",
        related="product_id.qty_available",
        readonly=True,
    )

	def _prepare_invoice_line(self, **optional_values):
		values = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
		if not values.get('od_customer_uom_id'):
			values['od_customer_uom_id'] = self.od_customer_uom_id and self.od_customer_uom_id.id
		if not values.get('od_customer_order'):
			values['od_customer_order'] = self.od_customer_order
		return values

	@api.depends('price_unit','od_cost')
	def od_compute_margin(self):
		for line in self:
			margin = 0
			margin = ((line.price_unit-line.od_cost)/line.price_unit if line.price_unit else 1)*100
			line.od_margin = margin

	@api.onchange('od_customer_order')
	def onchange_customer_order(self):
		for line in self:
			line.product_uom_qty = line.od_customer_order

	@api.onchange('product_id')
	def od_onchange_product(self):
		for line in self:
			if line.product_id:
				query = """
					SELECT price_unit 
					FROM sale_order_line line
					LEFT JOIN sale_order so ON line.order_id = so.id
					WHERE so.partner_id = %s AND line.product_id = %s
					ORDER BY so.date_order DESC 
					LIMIT 1
				"""
				self._cr.execute(query, (line.order_id.partner_id.id, line.product_id.id))
				result = self._cr.fetchone()
				if result:
					line.od_last_price = result[0]

				if not line.od_create_mo:
					line.od_cost = line.product_id.standard_price

	@api.onchange('product_id','od_create_mo')
	def od_onchange_cost(self):
		for line in self:
			if line.product_id and (not line.od_create_mo):
				line.od_cost = line.product_id.standard_price


	def od_create_proof_request(self):
		"""Open the proof request form with default values from this sale order line."""
		self.ensure_one()
		existing = self.env['od.proof.request'].search([('product_id','=',self.product_id.id)], limit=1)
		context = {
			'default_od_sale_line_id': self.id,
		}
		if existing:
			for field_name, field in existing._fields.items():
				if field.type not in ('one2many', 'many2many') and field.store:
					value = existing[field_name]
					if value not in (False, None, '', 0):
						context[f'default_{field_name}'] = value
			# print("acccc",context,existing.uom_id,existing.product_id.uom_id)
			context['default_partner_id']=self.order_id.partner_id.id
			context['default_product_id']=existing.product_id.id
			context['default_raw_mat_id']=existing.raw_mat_id.id
			context['default_uom_id']=existing.product_id.uom_id.id
			context['default_name']='/'
			context['default_state']='draft'
			context['no_create_pdt']=True
			context['default_od_sale_line_id']=self.id
		return {
			'name': _('Create Proof Request'),
			'type': 'ir.actions.act_window',
			'res_model': 'od.proof.request',
			'view_mode': 'form',
			'view_id': False,
			'target': 'current',
			'context': context,
		}

	def od_view_proof_request(self):
		"""Open the proof request form with default values from this sale order line."""
		self.ensure_one()
		request = self.od_proof_request_ids
		action = self.env['ir.actions.actions']._for_xml_id('orchid_radiant_house_v18.action_od_proof_request')
		if request:
			form_view = [(self.env.ref('orchid_radiant_house_v18.od_proof_request_form_view').id, 'form')]
			if 'views' in action:
				action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				action['views'] = form_view
			action['res_id'] = request.id
		else:
			action = {'type': 'ir.actions.act_window_close'}
		action['context'] = {'create':0}
		return action


class SaleOrder(models.Model):
	_inherit = 'sale.order'

	od_mo_created = fields.Boolean(string="MO Created", copy=False, tracking=True, compute="od_compute_mo_create", store=True)
	od_analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", tracking=True, copy=False)
	od_lpo_date = fields.Date(string="LPO Date", tracking=True)
	od_print_without_price = fields.Boolean(string="Print without Price", default=False)
	od_production_status = fields.Selection([('Pending','Pending'),('Completed','Completed')], string="Production Status", compute="od_compute_production_status", store=True)
	od_margin = fields.Float(
		string="Margin %", compute="od_compute_margin", store=True)
	od_total_cost = fields.Float(string="Total Cost", compute="od_compute_margin", store=True)

	@api.depends('order_line.price_unit','order_line.od_cost','order_line')
	def od_compute_margin(self):
		for order in self:
			margin = 0
			total_cost = 0
			price_unit = sum(line.price_unit for line in order.order_line)
			cost = sum(line.od_cost for line in order.order_line)
			total_cost = sum(line.od_total_cost for line in order.order_line)
			margin = ((price_unit-cost)/price_unit if price_unit else 1)*100
			order.od_margin = margin
			order.od_total_cost = total_cost

	
	@api.depends('order_line','order_line.od_create_mo','order_line.od_mrp_ids','state')
	def od_compute_mo_create(self):
		for sale in self:
			od_mo_created = False
			od_mo_created = all(l.od_mrp_ids.filtered(lambda mp:mp.state!='cancel') for l in sale.order_line.filtered(lambda x:x.od_create_mo))
			sale.od_mo_created = od_mo_created

	@api.depends('mrp_production_ids','mrp_production_ids.state')
	def od_compute_production_status(self):
		for sale in self:
			if sale.mrp_production_ids:
				if all(mp.state=='done' for mp in sale.mrp_production_ids.filtered(lambda x:x.state != 'cancel')):
					sale.od_production_status = 'Completed'
				else:
					sale.od_production_status = 'Pending'

	def od_find_cost(self):
		# find the cost
		for sale in self:
			for line in sale.order_line.filtered(lambda x:x.od_create_mo):
				unit_cost = 0
				total_cost = 0
				for mp in line.od_mrp_ids:
					if mp.state=='done' and mp.od_sale_order_line_id.id==line.id:
						for fp in mp.cost_sheet_lines_fp:
							unit_cost+=fp.unit_cost
							total_cost+=fp.amount
				line.od_cost = unit_cost
				line.od_total_cost = total_cost



	def _prepare_invoice(self):
		values = super(SaleOrder, self)._prepare_invoice()

		if self.picking_ids:
			# Filter outgoing & done pickings
			outgoing_done = self.picking_ids.filtered(
				lambda p: p.picking_type_code == 'outgoing' and p.state == 'done'
			)

			if outgoing_done:
				# Concatenate picking names as string
				picking_names = ", ".join(outgoing_done.mapped('name'))
				values['od_picking_name'] = picking_names

		return values



	def od_create_analytic_account(self, prefix=None):
		for order in self:
			analytic_account_obj = self.env['account.analytic.account']
			name = self.name
			if prefix:
				name = prefix + ": " + self.name
			vals = {
				'name': name,
				'code': self.client_order_ref,
				'company_id': self.company_id.id,
				'partner_id': self.partner_id.id,
				'plan_id':1,
			}
			analytic_account = analytic_account_obj.sudo().create(vals)
			order.od_analytic_account_id = analytic_account.id
			return analytic_account

	def action_confirm(self):
		result = super(SaleOrder, self).action_confirm()
		if not self.od_analytic_account_id:
			analytic_id = self.od_create_analytic_account()
			analytic_id.code = self.name
		return result

	def od_action_create_mo(self):
		if not self.od_analytic_account_id:
			analytic_id = self.od_create_analytic_account()
			analytic_id.code = self.name
		self.od_create_mo()
		# self.write({'od_mo_created': True}) may be more lines be added after once done

	def od_create_mo(self):
		MrpProduction = self.env['mrp.production']
		MrpBOM = self.env['mrp.bom']

		for sale in self:
			mrp_defaults = MrpProduction.default_get([
				'location_src_id', 'location_dest_id'
			])

			for line in sale.order_line.filtered(lambda x:x.od_create_mo and ((not x.od_mrp_ids) or (all(mp.state=='cancel' for mp in x.od_mrp_ids)))):
				if line.product_id and line.product_id.od_product_type == 'finished_product' and line.od_create_mo:
					# if not line.product_id.od_die_id:
					# 	raise UserError(_("No Die Product selected for the product %s") % line.product_id.name)

					product_template_id = line.product_id.product_tmpl_id.id
					bom = MrpBOM.search([('product_tmpl_id', '=', product_template_id)], limit=1)
					proof_req_id = line.od_proof_request_ids or line.product_id.od_proof_request_id
					if not proof_req_id:
						raise UserError(_("No proof request for the product '%s'!! Create one from sale order line!!")%(line.product_id.display_name))
					mrp_vals = {
						**mrp_defaults,
						'product_id': line.product_id.id,
						'product_qty': line.product_uom_qty,
						# 'od_actual_qty': line.product_uom_qty,
						# 'od_opening_qty': line.product_id.qty_available,
						'product_uom_id': line.product_uom.id,
						'od_analytic_id': sale.od_analytic_account_id.id,
						'user_id': self.env.user.id,
						'origin': sale.name,
						'bom_id': bom.id if bom else False,
						'od_sale_order_line_id': line.id,
						'od_price_unit': line.price_unit,
						'od_validity_date': sale.date_order,
						'od_remarks': sale.note,
						'name': 'New',
						'od_customer_order':line.od_customer_order,
						'od_customer_uom_id':line.od_customer_uom_id and line.od_customer_uom_id.id,
						'od_cylinder':proof_req_id.od_cylinder_teeth_1 and proof_req_id.od_cylinder_teeth_1.id,
					}

					mrp_id = MrpProduction.create(mrp_vals)

	@api.depends('procurement_group_id.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids','order_line.od_mrp_ids')
	def _compute_mrp_production_ids(self):
		data = self.env['procurement.group']._read_group([('sale_id', 'in', self.ids)], ['sale_id'], ['id:recordset'])
		production_order_by_sale_line = self.env['mrp.production']._read_group([('sale_line_id', 'in', self.order_line.ids)], ['sale_line_id'], ['id:recordset'])
		mrp_productions = defaultdict(self.env['mrp.production'].browse)
		for sale, procurement_groups in data:
			mrp_productions[sale.id] |= procurement_groups.stock_move_ids.created_production_id.procurement_group_id.mrp_production_ids | procurement_groups.mrp_production_ids
		for sale_line, production_id in production_order_by_sale_line:
			mrp_productions[sale_line.order_id.id] |= production_id
		for sale in self:

			# CUSTOM: Add custom MRP records from order_line.od_mrp_ids
			custom_od_mrp_ids = sale.order_line.mapped('od_mrp_ids')  # CUSTOM
			mrp_productions[sale.id] |= custom_od_mrp_ids             # CUSTOM

			mrp_production_ids = mrp_productions[sale.id]
			sale.mrp_production_count = len(mrp_production_ids)
			sale.mrp_production_ids = mrp_production_ids


	@api.onchange('client_order_ref', 'partner_id')
	def od_onchange_client_order_ref_warning(self):
		for record in self:
			if not record.client_order_ref or not record.partner_id:
				return

			domain = [
				('client_order_ref', '=', record.client_order_ref),
				('partner_id', '=', record.partner_id.id),
				('id', '!=', record.id),
				('state', 'in', ['sale', 'done', 'draft']),
			]

			existing_orders = record.env['sale.order'].search(domain, limit=3)

			if existing_orders:
				order_names = ', '.join(existing_orders.mapped('name'))
				return {
					'warning': {
						'title': 'Duplicate Client Order Reference',
						'message': (
							f'This Client Order Reference is already used in: '
							f'{order_names}.\n\n'
							'You may continue if this is intentional.'
						),
					}
				}

	def action_cancel(self):
		for sale in self:
			mrp_ids = sale.order_line.od_mrp_ids
			if any(mrp_id.state=='done' for mrp_id in mrp_ids):
				raise UserError(_("Cannot cancel, production already done!!!"))
			mrp_ids.action_cancel()
		return super(SaleOrder, self).action_cancel()