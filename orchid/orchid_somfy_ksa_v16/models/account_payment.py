from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, formatLang

class AccountPayment(models.Model):
	_inherit = 'account.payment'

	od_exchange_rate=fields.Float(string="Exchange Rate",digits=(12, 12))
	od_local_amount=fields.Float(string="LC Amount")
	od_bank_charges = fields.Monetary(currency_field='currency_id', string="Bank Charges")
	od_bank_charges_account_id = fields.Many2one('account.account', string="Bank Charges Account")
	od_total_amount = fields.Monetary(currency_field='currency_id', string="Total Amount Paid", compute="od_get_total_amount")


	api.depends('od_bank_charges','amount')
	def od_get_total_amount(self):
		for record in self:
			record.od_total_amount=record.amount+record.od_bank_charges

	@api.depends('journal_id')
	def _compute_currency_id(self):
		for pay in self:
			# pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id
			euro_currency_id = pay.env.ref('base.EUR')
			pay.currency_id = euro_currency_id



	# bank charges changes
	def _prepare_move_line_default_vals(self, write_off_line_vals=None):
		''' Prepare the dictionary to create the default account.move.lines for the current payment.
		:param write_off_line_vals: Optional list of dictionaries to create a write-off account.move.line easily containing:
			* amount:       The amount to be added to the counterpart amount.
			* name:         The label to set on the line.
			* account_id:   The account on which create the write-off.
		:return: A list of python dictionary to be passed to the account.move.line's 'create' method.
		'''
		
		self.ensure_one()
		if self.od_bank_charges:
			if not self.od_bank_charges_account_id:
				raise UserError(_("Please set Bank Charges Account to continue!!"))

			write_off_line_vals = write_off_line_vals or {}

			if not self.outstanding_account_id:
				raise UserError(_(
					"You can't create a new payment without an outstanding payments/receipts account set either on the company or the %s payment method in the %s journal.",
					self.payment_method_line_id.name, self.journal_id.display_name))

			dummy_write_off_line_vals=[]
			for wl_vals in write_off_line_vals:
				if wl_vals['account_id']!=self.od_bank_charges_account_id.id:
					dummy_write_off_line_vals.append(wl_vals)
			write_off_line_vals = dummy_write_off_line_vals
			# Compute amounts.
			write_off_line_vals_list = write_off_line_vals or []
			write_off_amount_currency = sum(x['amount_currency'] for x in write_off_line_vals_list)
			write_off_balance = sum(x['balance'] for x in write_off_line_vals_list)

			if self.payment_type == 'inbound':
				# Receive money.
				liquidity_amount_currency = self.amount
			elif self.payment_type == 'outbound':
				# Send money.
				liquidity_amount_currency = -self.amount
			else:
				liquidity_amount_currency = 0.0

			liquidity_balance = self.currency_id._convert(
				liquidity_amount_currency,
				self.company_id.currency_id,
				self.company_id,
				self.date,
			)
			bank_charges_balance = self.currency_id._convert(
				self.od_bank_charges,
				self.company_id.currency_id,
				self.company_id,
				self.date,
			)

			# payment exchange rate changes
			if self.currency_id.id != self.company_id.currency_id.id and self.od_exchange_rate and self.payment_type=='outbound':
				print("heloooooooooooooooooooo")
				# Apply your custom rate
				liquidity_balance = liquidity_amount_currency * self.od_exchange_rate
				bank_charges_balance = bank_charges_balance * self.od_exchange_rate
				
			counterpart_amount_currency = -(liquidity_amount_currency+self.od_bank_charges) - write_off_amount_currency
			counterpart_balance = -(liquidity_balance+bank_charges_balance) - write_off_balance
			currency_id = self.currency_id.id

			# Compute a default label to set on the journal items.
			liquidity_line_name = ''.join(x[1] for x in self._get_liquidity_aml_display_name_list())
			counterpart_line_name = ''.join(x[1] for x in self._get_counterpart_aml_display_name_list())

			line_vals_list = [
				# Liquidity line.
				{
					'name': liquidity_line_name,
					'date_maturity': self.date,
					'amount_currency': liquidity_amount_currency,
					'currency_id': currency_id,
					'debit': liquidity_balance if liquidity_balance > 0.0 else 0.0,
					'credit': -liquidity_balance if liquidity_balance < 0.0 else 0.0,
					'partner_id': self.partner_id.id,
					'account_id': self.outstanding_account_id.id,
				},
				# bank charges
				{
					'name': "Bank Charges "+formatLang(self.env, self.od_bank_charges, currency_obj=self.currency_id)+"- "+self.partner_id.display_name,
					'date_maturity': self.date,
					'amount_currency': self.od_bank_charges,
					'currency_id': currency_id,
					'debit': bank_charges_balance if bank_charges_balance > 0.0 else 0.0,
					'credit': -bank_charges_balance if bank_charges_balance < 0.0 else 0.0,
					'partner_id': self.partner_id.id,
					'account_id': self.od_bank_charges_account_id.id,
				},
				# Receivable / Payable.
				{
					'name': counterpart_line_name,
					'date_maturity': self.date,
					'amount_currency': counterpart_amount_currency,
					'currency_id': currency_id,
					'debit': counterpart_balance if counterpart_balance > 0.0 else 0.0,
					'credit': -counterpart_balance if counterpart_balance < 0.0 else 0.0,
					'partner_id': self.partner_id.id,
					'account_id': self.destination_account_id.id,
				},
			]
			return line_vals_list + write_off_line_vals_list

		else:
			lines = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals)
			if self.currency_id.id != self.company_id.currency_id.id and self.od_exchange_rate and self.payment_type=='outbound':
				for line in lines:
					amount_currency = line.get('amount_currency', 0.0)
					# Apply your custom rate
					balance = amount_currency * self.od_exchange_rate

					# Update values
					if balance > 0:
						line['debit'] = balance
						line['credit'] = 0.0
					else:
						line['credit'] = -balance
						line['debit'] = 0.0

					# Optional but good practice
					line['balance'] = balance
			return lines


	def _synchronize_to_moves(self, changed_fields):
		''' Update the account.move regarding the modified account.payment.
		:param changed_fields: A list containing all modified fields on account.payment.
		'''
		if self._context.get('skip_account_move_synchronization'):
			return

		if not any(field_name in changed_fields for field_name in (
			'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
			'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id',
			'od_bank_charges','od_bank_charges_account_id'
		)):
			return

		for pay in self.with_context(skip_account_move_synchronization=True):
			liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

			# Make sure to preserve the write-off amount.
			# This allows to create a new payment with custom 'line_ids'.

			write_off_line_vals = []
			if liquidity_lines and counterpart_lines and writeoff_lines:
				write_off_line_vals.append({
					'name': writeoff_lines[0].name,
					'account_id': writeoff_lines[0].account_id.id,
					'partner_id': writeoff_lines[0].partner_id.id,
					'currency_id': writeoff_lines[0].currency_id.id,
					'amount_currency': sum(writeoff_lines.mapped('amount_currency')),
					'balance': sum(writeoff_lines.mapped('balance')),
				})

			line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

			line_ids_commands = [
				Command.update(liquidity_lines.id, line_vals_list[0]) if liquidity_lines else Command.create(line_vals_list[0]),
				Command.update(counterpart_lines.id, line_vals_list[1]) if counterpart_lines else Command.create(line_vals_list[1])
			]

			for line in writeoff_lines:
				line_ids_commands.append((2, line.id))

			for extra_line_vals in line_vals_list[2:]:
				line_ids_commands.append((0, 0, extra_line_vals))

			# Update the existing journal items.
			# If dealing with multiple write-off lines, they are dropped and a new one is generated.

			pay.move_id.write({
				'partner_id': pay.partner_id.id,
				'currency_id': pay.currency_id.id,
				'partner_bank_id': pay.partner_bank_id.id,
				'line_ids': line_ids_commands,
			})
