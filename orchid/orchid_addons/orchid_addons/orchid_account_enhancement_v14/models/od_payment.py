
# -*- coding: utf-8 -*-

from odoo import fields,models,api,_
from odoo import tools
from copy import copy
from odoo.exceptions import UserError, ValidationError


# Modifications in account.payment for PDC
class AccountPayment(models.Model):
	_inherit = "account.payment"

	is_clearing = fields.Boolean(string='Clearing',copy=False)
	od_clearing_account = fields.Many2one('account.account', string='Clearing Account', domain=[('deprecated', '=', False)], help="Select Clearing Account (Default filled from Journal)",copy=False)
	od_release_move_id = fields.Many2one('account.move',string="Release Entry")
	od_released = fields.Boolean(string='Released')
	od_bank_account = fields.Many2one('account.account', string='Bank Account', domain=[('deprecated', '=', False)], help="Select Bank Account (Default filled from Journal)",copy=False)


	@api.onchange('payment_method_code')
	def payment_methiod_onchange(self):
		if self.payment_method_code == 'pdc':
			self.is_clearing = True
		else:
			self.is_clearing = False

	def action_draft(self):
		''' posted -> draft '''
		result = super(AccountPayment,self).action_draft()
		if self.od_released==True:
			self.write({'od_released': False })
		if self.od_release_move_id:
			self.od_release_move_id.button_draft()
		return result

	def action_cancel(self):
		result = super(AccountPayment,self).action_cancel()
		# test = self.nn_released
		# raise UserError(str(test))
		#test1 = self.nn_release_move_id
		#raise UserError(str(test1))
		if self.od_released==True:
			self.write({'od_released': False })
		if self.od_release_move_id:
			self.od_release_move_id.button_cancel()
			# self.od_release_move_id.unlink()
		return result

	@api.onchange('journal_id')
	def _onchange_journal(self):
		if self.journal_id:
			# self.currency_id = self.journal_id.currency_id or self.company_id.currency_id
			# # Set default payment method (we consider the first to be the default one)
			# payment_methods = self.payment_type == 'inbound' and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
			# self.payment_method_id = payment_methods and payment_methods[0] or False
			# # Set payment method domain (restrict to methods enabled for the journal and to selected payment type)
			# payment_type = self.payment_type in ('outbound', 'transfer') and 'outbound' or 'inbound'
			self.od_bank_account = self.payment_type == 'outbound' and self.journal_id.payment_debit_account_id.id or self.journal_id.payment_credit_account_id.id
			# self.od_clearing_account = self.payment_type == 'outbound' and self.journal_id.nn_cheque_out_acc_id.id or self.journal_id.nn_cheque_in_acc_id.id
			
			# return {'domain': {'payment_method_id': [('payment_type', '=', payment_type), ('id', 'in', payment_methods.ids)]}}
		# return {}

	def release(self):
		
		# if not self.od_release_move_id:
		debit_account_id = False
		credit_account_id = False
		# journal_id = self.journal_id and self.journal_id.id or False
		journal_id = self.env['ir.config_parameter'].search([('key','=','od_release_journal_id')])
		if not journal_id:
			raise UserError(_("System parameter 'od_release_journal_id' is not set!!!"))
		journal_id = int(journal_id.value)
		payment_type = self.payment_type
		partner_id = self.partner_id and self.partner_id.id
		if payment_type == 'outbound':
			debit_account_id = self.od_clearing_account and  self.od_clearing_account.id or False
			credit_account_id = self.od_bank_account and self.od_bank_account.id or False
		elif payment_type == 'inbound':
			credit_account_id = self.od_clearing_account and  self.od_clearing_account.id or False
			debit_account_id = self.od_bank_account and self.od_bank_account.id or False
		# check_date = self.od_check_date
		check_date = self.effective_date
		# check_no = self.od_check_no
		check_no = self.cheque_reference
		name = self.name
		amount = self.amount
		# communication=self.communication or " "
		communication=self.ref or " "
		move_vals = {'journal_id':journal_id,'date':check_date,'ref':self.name + _(' / ') + communication}
		move_line = []
		# debit_line_vals = (0,0,{'nn_check_no':check_no,'account_id':debit_account_id,'name':name,'credit':0.0,'debit':amount,'partner_id':partner_id})
		debit_line_vals = (0,0,{'account_id':debit_account_id,'name':name,'credit':0.0,'debit':amount,'partner_id':partner_id,'date_maturity':check_date})
		# credit_line_vals =  (0,0,{'nn_check_no':check_no,'account_id':credit_account_id,'name':name,'credit':amount,'debit':0.0,'partner_id':partner_id})
		credit_line_vals =  (0,0,{'account_id':credit_account_id,'name':name,'credit':amount,'debit':0.0,'partner_id':partner_id,'date_maturity':check_date})
		move_line.append(debit_line_vals)
		move_line.append(credit_line_vals)
		move_vals['line_ids'] = move_line
		print("gggggggggggggggg",move_vals)
		if self.od_release_move_id:
			print("jjjjjjjmmmmm",move_line)
			# print(s)
			self.od_release_move_id.line_ids.unlink()
			self.od_release_move_id.update({'journal_id':journal_id,'date':check_date,'ref':self.name + _(' / ') + communication})
			self.od_release_move_id.line_ids = move_line
			move = self.od_release_move_id
		else:
			move_pool = self.env['account.move']
			move = move_pool.create(move_vals)
		print("jjjjjjjjjjjjjjjjjjjj")
		move_id = move.id
		move.post()
		self.write({'od_release_move_id':move_id,'od_released':True})

	def _seek_for_lines(self):
		''' Helper used to dispatch the journal items between:
		- The lines using the temporary liquidity account.
		- The lines using the counterpart account.
		- The lines being the write-off lines.
		:return: (liquidity_lines, counterpart_lines, writeoff_lines)
		'''
		self.ensure_one()

		liquidity_lines = self.env['account.move.line']
		counterpart_lines = self.env['account.move.line']
		writeoff_lines = self.env['account.move.line']

		for line in self.move_id.line_ids:
			if self.is_clearing:
				if line.account_id in (self.od_clearing_account, self.journal_id.payment_debit_account_id, self.journal_id.payment_credit_account_id):
					liquidity_lines += line
				elif line.account_id.internal_type in ('receivable', 'payable') or line.partner_id == line.company_id.partner_id:
					counterpart_lines += line
				else:
					writeoff_lines += line

			else:
				if line.account_id in (self.od_bank_account,self.journal_id.payment_debit_account_id, self.journal_id.payment_credit_account_id):
					liquidity_lines += line
				elif line.account_id.internal_type in ('receivable', 'payable') or line.partner_id == line.company_id.partner_id:
					counterpart_lines += line
				else:
					writeoff_lines += line

		return liquidity_lines, counterpart_lines, writeoff_lines

	def _prepare_move_line_default_vals(self, write_off_line_vals=None):
		print("odoooooprepppppppppp")
		''' Prepare the dictionary to create the default account.move.lines for the current payment.
		:param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
			* amount:       The amount to be added to the counterpart amount.
			* name:         The label to set on the line.
			* account_id:   The account on which create the write-off.
		:return: A list of python dictionary to be passed to the account.move.line's 'create' method.
		'''
		self.ensure_one()
		write_off_line_vals = write_off_line_vals or {}

		if not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id:
			raise UserError(_(
				"You can't create a new payment without an outstanding payments/receipts accounts set on the %s journal."
			) % self.journal_id.display_name)

		# Compute amounts.
		write_off_amount = write_off_line_vals.get('amount', 0.0)

		if self.payment_type == 'inbound':
			# Receive money.
			counterpart_amount = -self.amount
			write_off_amount *= -1
		elif self.payment_type == 'outbound':
			# Send money.
			counterpart_amount = self.amount
		else:
			counterpart_amount = 0.0
			write_off_amount = 0.0

		balance = self.currency_id._convert(counterpart_amount, self.company_id.currency_id, self.company_id, self.date)
		counterpart_amount_currency = counterpart_amount
		write_off_balance = self.currency_id._convert(write_off_amount, self.company_id.currency_id, self.company_id, self.date)
		write_off_amount_currency = write_off_amount
		currency_id = self.currency_id.id

		if self.is_internal_transfer:
			if self.payment_type == 'inbound':
				liquidity_line_name = _('Transfer to %s', self.journal_id.name)
			else: # payment.payment_type == 'outbound':
				liquidity_line_name = _('Transfer from %s', self.journal_id.name)
		else:
			liquidity_line_name = self.payment_reference

		# Compute a default label to set on the journal items.

		payment_display_name = {
			'outbound-customer': _("Customer Reimbursement"),
			'inbound-customer': _("Customer Payment"),
			'outbound-supplier': _("Vendor Payment"),
			'inbound-supplier': _("Vendor Reimbursement"),
		}
		print("beforeeeeeeeeeeyesssssssss",self.payment_reference)
		default_line_name = self.env['account.move.line']._get_default_line_name(
			payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
			self.amount,
			self.currency_id,
			self.date,
			partner=self.partner_id,
		)
		print("yesssssssssssssssssssssssssssssssssssss")
		account_id = self.journal_id.payment_debit_account_id.id if balance < 0.0 else self.journal_id.payment_credit_account_id.id
		if self.od_bank_account:
			account_id = self.od_bank_account.id
		if self.is_clearing:
			print("yesssssssssssssssstttttttttttt")
			account_id = self.od_clearing_account.id
		print("kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk")
		print("kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk")
		print("kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk",account_id)
		line_vals_list = [
			# Liquidity line.
			{
				'name': liquidity_line_name or default_line_name,
				# 'date_maturity': self.date,
				'date_maturity': self.effective_date if self.effective_date else self.date,
				'amount_currency': -counterpart_amount_currency,
				'currency_id': currency_id,
				'debit': balance < 0.0 and -balance or 0.0,
				'credit': balance > 0.0 and balance or 0.0,
				'partner_id': self.partner_id.id,
				# 'account_id': self.journal_id.payment_debit_account_id.id if balance < 0.0 else self.journal_id.payment_credit_account_id.id,
				'account_id': account_id,
			},
			# Receivable / Payable.
			{
				'name': self.payment_reference or default_line_name,
				# 'date_maturity': self.date,
				'date_maturity': self.effective_date if self.effective_date else self.date,
				'amount_currency': counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0,
				'currency_id': currency_id,
				'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
				'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
				'partner_id': self.partner_id.id,
				'account_id': self.destination_account_id.id,
			},
		]
		if write_off_balance:
			# Write-off line.
			line_vals_list.append({
				'name': write_off_line_vals.get('name') or default_line_name,
				'amount_currency': -write_off_amount_currency,
				'currency_id': currency_id,
				'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
				'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
				'partner_id': self.partner_id.id,
				'account_id': write_off_line_vals.get('account_id'),
			})
		return line_vals_list


class AccountPartialReconcile(models.Model):
	_inherit = "account.partial.reconcile"

	@api.depends('debit_move_id.date', 'credit_move_id.date')
	def _compute_max_date(self):
		for partial in self:
			partial.max_date = max(
				partial.debit_move_id.date,
				partial.credit_move_id.date
			)
			# payment_id = partial.env['account.payment'].search([('move_id','in',[debit_move_id.move_id.id,credit_move_id.move_id.id])])
			payment_id = False
			if partial.debit_move_id.payment_id:
				payment_id = partial.debit_move_id.payment_id
			if partial.credit_move_id.payment_id:
				payment_id=partial.credit_move_id.payment_id
			if payment_id:
				if payment_id.payment_method_code =='pdc':
					partial.max_date = payment_id.effective_date

