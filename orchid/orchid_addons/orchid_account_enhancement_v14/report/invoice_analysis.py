# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo import tools




# OrchidAccountInvoiceCost
class OrchidAccountInvoiceCost(models.Model):
	_name = "orchid.account.invoice.cost"
	_description = "Orchid Account Invoice Cost"
	_auto = False
	_order = "id ASC"

	inv_id = fields.Many2one('account.move',string="Invoice")
	product_id = fields.Many2one('product.product',string="Product")
	quantity = fields.Float(string="Quantity")
	cost = fields.Float(string="Cost")
   
	def init(self):
		cr = self.env.cr   
		tools.drop_view_if_exists(cr, 'orchid_account_invoice_cost')
		cr.execute("""
			create or replace view orchid_account_invoice_cost as (
				SELECT row_number() OVER (ORDER BY move.id) AS id,
					move.id AS inv_id,
					mvl.product_id,
					mvl.quantity,
					CASE
						WHEN (((move.move_type)::text = 'out_invoice'::text) AND mvl.quantity<>0) THEN (sum(mvl.debit)/sum(mvl.quantity))
						WHEN (((move.move_type)::text = 'out_invoice'::text) AND mvl.quantity=0) THEN (sum(mvl.debit)/1)
						WHEN (((move.move_type)::text = 'out_refund'::text) AND mvl.quantity<>0) THEN ((sum(mvl.credit)/sum(mvl.quantity) )* ('-1'::integer)::numeric)
						WHEN (((move.move_type)::text = 'out_refund'::text) AND mvl.quantity=0) THEN ((sum(mvl.credit)/1 )* ('-1'::integer)::numeric)
						ELSE (0)::numeric
					END AS cost
				FROM (((account_move_line mvl
				 JOIN account_account acc ON ((mvl.account_id = acc.id)))
				 JOIN account_account_type typ ON ((acc.user_type_id = typ.id)))
				 JOIN account_move move ON ((move.id = mvl.move_id)))
				WHERE (((typ.name)::text = 'Cost of Revenue'::text) AND ((move.move_type)::text = ANY ((ARRAY['out_invoice'::character varying, 'out_refund'::character varying])::text[])))
				GROUP BY move.move_type, move.id, mvl.product_id,mvl.quantity
			)
		""")


class AccountInvoiceReport(models.Model):
	_inherit = 'account.invoice.report'

	payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', readonly=True)
	currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
	state_id = fields.Many2one('res.country.state',string='Emirates')
	origin = fields.Char(string="Origin")
	cost = fields.Float(string='Cost', readonly=True)
	tax_amount = fields.Float(string="Tax Amount")
	net_amount = fields.Float(string="Total Amount")
	residual = fields.Float(string='Un Paid', readonly=True)
	paid_amount = fields.Float(string="Paid")
	profit = fields.Float(string='Profit', readonly=True)
	accounting_date = fields.Date(string="Date")

	@property
	def _table_query(self):
		return '%s %s %s %s' % (self._select(), self._from(), self._where(), self._groupby())
	
	def _select(self):
		return super(AccountInvoiceReport, self)._select() + ",\
		move.invoice_origin as origin,\
		move.invoice_payment_term_id as payment_term_id,\
		move.currency_id,\
		partner.state_id,\
		((sum(COALESCE(tax.amount,0))*(-line.balance * currency_table.rate))/100) as tax_amount,\
		(-line.balance * currency_table.rate) + ((sum(COALESCE(tax.amount,0))*(-line.balance * currency_table.rate))/100) as net_amount,\
		case when cst.cost is not null\
		 then cst.cost * line.quantity \
		 else 0 end AS cost,\
		case when cst.cost is not null\
		then ((-line.balance * currency_table.rate)) - (cst.cost * line.quantity) \
		else ((-line.balance * currency_table.rate)) - (0 * line.quantity) end AS profit,\
		case when abs(move.amount_total_signed)<>0\
		then ((-line.balance * currency_table.rate) + ((sum(COALESCE(tax.amount,0))*(-line.balance * currency_table.rate))/100))  *  ((((abs(move.amount_total_signed) - abs(move.amount_residual_signed))/abs(move.amount_total_signed)) * 100)/100)\
		else ((-line.balance * currency_table.rate) + ((sum(COALESCE(tax.amount,0))*(-line.balance * currency_table.rate))/100))  *  ((((abs(move.amount_total_signed) - abs(move.amount_residual_signed))/1) * 100)/100) end as paid_amount,\
		case when abs(move.amount_total_signed)<>0\
		then ((-line.balance * currency_table.rate) + ((sum(COALESCE(tax.amount,0))*(-line.balance * currency_table.rate))/100)) *  (1-((((abs(move.amount_total_signed) - abs(move.amount_residual_signed))/abs(move.amount_total_signed)) * 100)/100))\
		else ((-line.balance * currency_table.rate) + ((sum(COALESCE(tax.amount,0))*(-line.balance * currency_table.rate))/100)) *  (1-((((abs(move.amount_total_signed) - abs(move.amount_residual_signed))/1) * 100)/100)) end as residual,\
		line.date as accounting_date\
		"

	@api.model
	def _from(self):
		return '''
			FROM account_move_line line
				LEFT JOIN res_partner partner ON partner.id = line.partner_id
				LEFT JOIN product_product product ON product.id = line.product_id
				LEFT JOIN account_account account ON account.id = line.account_id
				LEFT JOIN account_account_type user_type ON user_type.id = account.user_type_id
				LEFT JOIN product_template template ON template.id = product.product_tmpl_id
				LEFT JOIN uom_uom uom_line ON uom_line.id = line.product_uom_id
				LEFT JOIN uom_uom uom_template ON uom_template.id = template.uom_id
				INNER JOIN account_move move ON move.id = line.move_id
				LEFT JOIN res_partner commercial_partner ON commercial_partner.id = move.commercial_partner_id

				LEFT JOIN orchid_account_invoice_cost cst ON line.move_id = cst.inv_id 
					and line.product_id = cst.product_id 
					and line.quantity = cst.quantity
				LEFT JOIN account_move_line_account_tax_rel lt ON lt.account_move_line_id = line.id
				LEFT JOIN account_tax tax ON tax.id = lt.account_tax_id

				JOIN {currency_table} ON currency_table.company_id = line.company_id
		'''.format(
			currency_table=self.env['res.currency']._get_query_currency_table({'multi_company': True, 'date': {'date_to': fields.Date.today()}}),
		)

	@api.model
	def _groupby(self):
		return '''
			GROUP BY
			line.id,
			line.move_id,
			line.product_id,
			line.account_id,
			line.analytic_account_id,
			line.journal_id,
			line.company_id,
			line.company_currency_id,
			line.partner_id,
			move.state,
			move.move_type,
			move.partner_id,
			move.invoice_user_id,
			move.fiscal_position_id,
			move.payment_state,
			move.invoice_date,
			move.invoice_date_due,
			uom_template.id,
			template.categ_id,
			line.quantity,
			uom_line.factor,
			currency_table.rate,
			partner.country_id,
			commercial_partner.country_id,
			move.team_id,
			move.currency_id,
			move.invoice_payment_term_id,
			move.amount_total_signed,
			move.amount_residual_signed,
			cst.cost,
			partner.state_id,
			move.invoice_origin,
			line.date
		'''