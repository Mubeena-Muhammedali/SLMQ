# -*- coding: utf-8 -*-
from odoo import fields,models,api,_
from odoo import tools

# OrchidPrepaidReport


class OrchidPrepaidAnalysis(models.Model):
	_name = "orchid.prepaid.report"
	_description = "Orchid Prepaid Analysis "
	_auto = False
	

	prepayment_id=fields.Many2one('orchid.prepayment.lines', string='Prepayments', readonly=True)
	date = fields.Date(string='Date', readonly=True)
	allocation_date=fields.Date(string='Allocation Date', readonly=True)
	state= fields.Selection([('cancel', 'Cancel'),('running', 'Unposted'), ('closed', 'Posted')], string='State')
	debit = fields.Float(default=0.0, string='Value')
	account_id = fields.Many2one('account.account', string='Prepaid Account')
	analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
	expense_analytic_account_id = fields.Many2one('account.analytic.account', string='Expense Analytic Account')
	partner_id = fields.Many2one('res.partner', string='prepaid Partner', ondelete='restrict')
	cost_center= fields.Many2one('orchid.account.cost.center',string='Cost Center')
	expense_cost_center= fields.Many2one('orchid.account.cost.center',string='Expense Cost Center')
	move_id = fields.Many2one('account.move',string="Journal Entry")
	journal_id = fields.Many2one('account.journal',  string='Journal')
	date_start = fields.Date(readonly=True)
	date_end= fields.Date(readonly=True)
	linked_partner_id=fields.Many2one('res.partner', string='Expense Partner', ondelete='restrict')
	expense_account_id=fields.Many2one('account.account', string='Expense Account')
	posted_value = fields.Float(string='Posted Amount', readonly=True)
	unposted_value = fields.Float(string='Unposted Amount', readonly=True)
	remark=fields.Char(string='Remarks')



	# @api.model_cr
	def init(self):
		cr = self.env.cr   
		tools.drop_view_if_exists(cr, 'orchid_prepaid_report')
		cr.execute("""
			create or replace view orchid_prepaid_report as (
				SELECT
					a.date_start,
					a.date_end,
					min(dl.id) as id,
					dl.state as state,
					a.account_id ,
					a.analytic_account_id,
					a.partner_id,
					a.cost_center,
					a.move_id,
					a.journal_id,
					a.remark,
					a.expense_account_id,
					a.linked_partner_id,
					mve.date as date,
					(CASE WHEN dl.state='closed'
                      THEN dl.amount
                      ELSE 0
                      END) as posted_value,
                  	(CASE WHEN dl.state='running'
                  	  THEN dl.amount
                  	  ELSE 0
                  	  END) as unposted_value,
                  	(CASE WHEN dlmin.id = min(dl.id)
                      THEN a.debit
                      ELSE 0
                      END) as debit,
                    dl.cost_center as expense_cost_center,
                    dl.analytic_account_id as expense_analytic_account_id,
                    dl.date as allocation_date
					
					
					
		
				FROM orchid_prepayment_board_history dl

					LEFT JOIN orchid_prepayment_lines a on (dl.prepayment_id=a.id)
					LEFT JOIN account_move mve ON a.move_id = mve.id
					LEFT JOIN (select min(d.id) as id,ac.id as ac_id from orchid_prepayment_board_history as d inner join orchid_prepayment_lines as ac ON (ac.id=d.prepayment_id) group by ac_id) as dlmin on dlmin.ac_id=a.id
				GROUP BY
					dl.prepayment_id,mve.date,dl.amount,dlmin.id,dl.cost_center, dl.analytic_account_id,dl.date,a.debit,a.linked_partner_id,
					a.date_start,a.date_end,dl.state,a.account_id,a.analytic_account_id,a.partner_id,a.cost_center,a.move_id,a.journal_id,a.remark,a.expense_account_id
					
			)""")

