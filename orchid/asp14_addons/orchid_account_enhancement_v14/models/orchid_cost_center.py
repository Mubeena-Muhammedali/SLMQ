# -*- coding: utf-8 -*-
from odoo import api, models, fields, _	
			
class OrchidAccountDivision(models.Model):
	_name = 'orchid.account.division'
	_description = "Account Division"

	code = fields.Char(string='Code',required=True)
	name = fields.Char(string='Name',required=True)
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)


class OrchidAccountBranch(models.Model):
	_name = 'orchid.account.branch'
	_description = "Account Branch"

	code = fields.Char(string='Code',required=True)
	name = fields.Char(string='Name',required=True)
	company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.user.company_id.id)

class OrchidAccountCostCenter(models.Model):
	_name = 'orchid.account.cost.center'
	_description = "Account Cost Center"

	code = fields.Char(string='Code',required=True)
	seq = fields.Integer(string="Sequence")
	name = fields.Char(string='Name',required=True)
	branch_id = fields.Many2one('orchid.account.branch',string='Branch')
	div_id = fields.Many2one('orchid.account.division',string='Division')
	div_mgr_id = fields.Many2one('res.users',string="Division Manager")
	target= fields.Float(string="Sales Target",help="This is for Day Report...Not for Incentive")
	company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.user.company_id.id)


# Modification in Account Move Line
class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'
	# _order = "sequence,id "
	 
	orchid_cc_id =  fields.Many2one('orchid.account.cost.center', string='Cost Center')
	# sequence = fields.Integer(help='Used to order Journal Entries in the dashboard view', default=10)

	@api.onchange('account_id')
	def move_line_account_change(self):
		# if self.journal_id and self.journal_id.orchid_div_id:
		# 	self.orchid_div_id = self.journal_id.orchid_div_id.id
		# if self.journal_id and self.journal_id.orchid_br_id:
		# 	self.orchid_br_id = self.journal_id.orchid_br_id.id
		if self.journal_id and self.journal_id.orchid_cc_id:
			self.orchid_cc_id = self.journal_id.orchid_cc_id.id

# Modifications in account.journal
class AccountJournal(models.Model):
	_inherit = "account.journal"
	# od_cheque_in_acc_id = fields.Many2one('account.account', string='Cheque In Account',
		# domain=[('deprecated', '=', False)], help="Cheque Recieved and posted to this account instead Bank A/C")
	# od_cheque_out_acc_id = fields.Many2one('account.account', string='Cheque Out Account',
		# domain=[('deprecated', '=', False)], help="Cheque Issued and posted to this account instead Bank A/C")
	orchid_div_id =  fields.Many2one('orchid.account.division', string='Division')
	orchid_br_id =  fields.Many2one('orchid.account.branch', string='Branch')
	orchid_cc_id =  fields.Many2one('orchid.account.cost.center', string='Cost Center')
	# active = fields.Boolean(default=True)