from odoo import api, fields, models, _

class OrchidRecurring(models.TransientModel):
	_name = 'orchid.recurring.wiz'
	_description = 'Recurring'
	
	company_id = fields.Many2one("res.company",string="Company",default=lambda self: self.env.user.company_id)
	recurring_entry = fields.Many2one('account.move',string="Recurring Entry",check_company=True)	

	def generate(self):
		move_line = self.env['account.move.line']
		[data] = self.read()
		active_id = self.env.context.get('active_id')
		if active_id:
			[move_data] = self.env['account.move'].browse(active_id).read(['date', 'name', 'ref','journal_id','narration'])
		date = move_data.get('date')
		journal_id = self.recurring_entry.journal_id and self.recurring_entry.journal_id.id or False
		name = move_data.get('name')
		ref = self.recurring_entry.ref or False
		narration = self.recurring_entry.narration or False
		move_lines = []
		for line in self.recurring_entry.line_ids:
			res = {
				'account_id': line.account_id and line.account_id.id or False,
				'partner_id': line.partner_id and line.partner_id.id or False,
				'name': line.name,
				'debit': line.debit,
				'credit': line.credit,
				'move_id': active_id,
			}
			move_lines.append((0,0,res))
		move_vals = {
				'ref': ref,
				'line_ids': move_lines,
				'journal_id': journal_id,
				'date': date,
				'narration': narration,
				'od_recurring':True,
			}
		self.env['account.move'].browse(active_id).write(move_vals)
		return {'type': 'ir.actions.act_window_close'}
