# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo import tools

# OrchidAccountInvoiceReport
class OrchidAccountEntryAnalysis(models.Model):
    _name = "orchid.account.entry.analysis"
    _description = "Orchid Account Entry Analysis"
    _auto = False
    _rec_name = 'date'
    _order = 'date desc'

    name = fields.Char(string='Voucher Number')
    date = fields.Date(string="Date")
    state = fields.Selection([('draft', 'Unposted'), ('posted', 'Posted')], string='Status')
    quantity = fields.Float(digits=(16, 2),string="Quantity")
    product_id = fields.Many2one('product.product', string='Product')
    debit = fields.Monetary(default=0.0, string='Debit')
    credit = fields.Monetary(default=0.0, string='Credit')
    balance = fields.Monetary(string='Balance')
    currency_id = fields.Many2one('res.currency', string='Currency')
    amount_residual = fields.Monetary( string='Residual Amount')
    amount_residual_currency = fields.Monetary(string='Residual Amount in Currency')
    account_id = fields.Many2one('account.account', string='Account')
    ref = fields.Char( string='Reference')
    payment_id = fields.Many2one('account.payment', string="Originator Payment")
    reconciled = fields.Boolean(string="Reconciled")
    full_reconcile_id = fields.Many2one('account.full.reconcile', string="Matching Number")
    journal_id = fields.Many2one('account.journal',  string='Journal')
    blocked = fields.Boolean(string='No Follow-up')
    date_maturity = fields.Date(string='Due date')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    company_id = fields.Many2one('res.company', related='account_id.company_id', string='Company', store=True)
    # invoice_id = fields.Many2one('account.invoice', oldname="invoice")
    partner_id = fields.Many2one('res.partner',string='Partner', ondelete='restrict')
    user_type_id = fields.Many2one('account.account.type', string="Account Type")
    cost_center_id = fields.Many2one('orchid.account.cost.center',string='Cost Center')
    move_id = fields.Many2one('account.move',string="Move")
    categ_id = fields.Many2one('product.category',string="Product Category")
    div_id = fields.Many2one('orchid.account.division',string='Division')
    branch_id = fields.Many2one('orchid.account.branch',string='Branch')
    country_id = fields.Many2one('res.country',string='Country')
    state_id = fields.Many2one('res.country.state',string='State')

    # @api.model_cr
    def init(self):
        cr = self.env.cr   
        tools.drop_view_if_exists(cr, 'orchid_account_entry_analysis')
        cr.execute("""
            create or replace view orchid_account_entry_analysis as (
                SELECT
                	mvl.id,
					--mvl.balance_cash_basis,replaced with balance
					mvl.balance,
					--mvl.debit_cash_basis, replaced with debit and it is already there in the view
					mvl.account_id, 
					mvl.orchid_cc_id, 
					mvl.create_uid, 
					(mvl.credit * -1) AS credit, 
					mvl.blocked, 
					mvl.company_id, 
					--mvl.credit_cash_basis, replaced with credit and it is already there in the view
					mvl.amount_currency, 
					mvl.date_maturity, 
					mvl.orchid_cc_id as cost_center_id,
					mvl.amount_residual, 
					mvl.write_date, 
					mvl.move_id,
					mvl.payment_id,  
					mvl.create_date, 
					mvl.reconciled, 
					mvl.amount_residual_currency, 
					--mvl.invoice_id, replaced with move_id already move id is there
					--mvl.move_id as invoice_id
					mvl.statement_id, 
					mvl.quantity, 
					mvl.product_id, 
					mvl.debit, 
					mvl.journal_id,
					--mvl.user_type_id, replaced with acc.user_type_id
					acc.user_type_id,
					mvl.ref, 
					mvl.currency_id,  
					mvl.full_reconcile_id, 
					mvl.write_uid, 
					mvl.analytic_account_id, 
					---(mvl.debit)-(mvl.credit) as balance,already balance field is there
					mve.state,
					mve.name,
					mve.date,
					prdc.id as categ_id,
					cc.branch_id,
					cc.div_id,
					mvl.partner_id,
					ptnr.country_id as country_id,
					ptnr.state_id as state_id

				FROM account_move_line mvl
				LEFT JOIN account_move mve ON mvl.move_id = mve.id
				LEFT JOIN res_partner ptnr ON mvl.partner_id = ptnr.id
				LEFT JOIN product_product prd ON mvl.product_id = prd.id
				LEFT JOIN product_template tmpl ON prd.product_tmpl_id = tmpl.id
				LEFT JOIN product_category prdc ON tmpl.categ_id = prdc.id
				LEFT JOIN account_account acc ON mvl.account_id = acc.id
				LEFT JOIN orchid_account_cost_center cc on mvl.orchid_cc_id = cc.id
				
            )
        """)
