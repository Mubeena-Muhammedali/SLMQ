# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
import openerp.addons.decimal_precision as dp
from odoo.exceptions import UserError,ValidationError


from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import time 
import datetime

class orchid_prepayment_lines(models.Model):
	_name = 'orchid.prepayment.lines'
	_description = 'Prepayment'

	
	account_id = fields.Many2one('account.account', string='Account')
	name = fields.Char(string='Name')
	move_id = fields.Many2one('account.move', string='Journal Entry',required=True, readonly=True)
	date = fields.Date(related='move_id.date', string='Date', readonly=True)  # related is required
	partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
	debit = fields.Float(string="Debit", readonly=True)
	credit = fields.Float(string="Credit", readonly=True)
	date_start = fields.Date(string="Start Date")
	date_end = fields.Date(string="End Date")
	expense_account_id = fields.Many2one('account.account', string="Account")
	journal_id = fields.Many2one('account.journal', string="Journal")
	remark = fields.Char(string="Remark")
	cost_center = fields.Many2one('orchid.account.cost.center',string="Cost Center")
	company_id = fields.Many2one('res.company',string="Company")
	linked_partner_id = fields.Many2one('res.partner', string='Partner')
	analytic_account_id = fields.Many2one('account.analytic.account',string="Analytic Account")
	state = fields.Selection([('draft', 'Draft'), ('in_progress', 'In progress'),('done', 'Done'), ('cancel', 'Cancel')], string='Status',required=True, readonly=True, default='draft')
	line_history_ids = fields.One2many('orchid.prepayment.board.history', 'prepayment_id', string='History', copy=False)

	
	def load_prepayment_line(self):
		move_ids = []
		current_prepayment_lines = self.search([])
		for cpl_obj in current_prepayment_lines:
			move_ids.append(cpl_obj.move_id and cpl_obj.move_id.id)
		account_obj = self.env['account.account'].search([('od_prepaid_account','=',True)])
		account_ids = []
		for account in account_obj:
			account_ids.append(account.id)
		move_line = self.env['account.move.line'].search([('account_id','in',account_ids)])
		for move in move_line:
			data_obj = {}
			data_obj['account_id'] = move.account_id and move.account_id.id
			data_obj['move_id'] = move.move_id and move.move_id.id
			data_obj['date'] = move.date
			data_obj['partner_id'] = move.partner_id and move.partner_id.id
			data_obj['company_id'] = move.company_id and move.company_id.id

			data_obj['debit'] = move.debit
			data_obj['credit'] = move.credit
			data_obj['date_start'] = move.date
#           data_obj['date_end'] = move.date
#           data_obj['journal_id'] = move.journal_id and move.journal_id.id
			data_obj['remark'] = 'Prepayment Line'
#           data_obj['expense_account_id'] = move.account_id and move.account_id.id
			
			if move.move_id.id not in move_ids and move.move_id.state != 'draft':
				data_obj['state'] = 'draft'
				if data_obj['debit'] !=0:
					a = self.create(data_obj)
		action = self.sudo().env.ref('orchid_prepayment_v14.action_orchid_prepayment')
		result = action.sudo().read()[0] 
		return result             


	def generate_prepayment_board(self):
		is_valid = self.validate_fields()
		if not is_valid:
			return 0
			
			
	def button_cancel(self):
		self.state = 'cancel'
		line = self.line_history_ids
		for li in line:
			if li.state == 'running':
				li.state = 'cancel'


	def get_month_day_range(self,date):

		last_day = date + relativedelta(day=1, months=+1, days=-1)
		first_day = date + relativedelta(day=1)
		return first_day, last_day
	def button_confirm(self):
		if not self.line_history_ids:
			raise ValidationError('no line found')
			

		self.state = 'in_progress'
		return True

	def validate_fields(self):
		wizard_account_id=0
		journal_id = 0
		id = self.account_id.id
		line_history_ids = self.line_history_ids
		if line_history_ids:
			raise ValidationError('already line is generated')
			
		# active_ids = self._context['active_ids']#self.browse(self.id)

		datas = self.search([('id','=',self.id)])
		if not self.date_end or not self.expense_account_id or not self.journal_id or not self.date_start:
			raise ValidationError('check date or account or journal')
		for data in datas:
			if data.state != 'draft':
				raise ValidationError('Payment board already generated!')
#           data.state = 'in_progress'
			wizard_account_id = data.account_id.id
			journal_id = data.journal_id.id
			move_id = data.move_id.id
			if not move_id:
				raise ValidationError('You cannot create entries for this move')        
			prepayment = self.env['orchid.prepayment.lines']
			# pre_ids = prepayment.search([('move_id','=',move_id)])
			# if pre_ids:
				# raise ValidationError('You cannot create entries for this move')          
			account_move_obj = self.env['account.move'].browse(move_id)
			voucher_date = account_move_obj.date
			if data.date_start < voucher_date:
				raise ValidationError('check date')
			if data.date_end < data.date_start:
				raise ValidationError('end date must be greater than start date')
				

			line_ids = []
			if not account_move_obj.line_ids:

				raise ValidationError('no lines found')
			pre_account_id = False    
			non_prepayment_acc =[]
			prepayment_acc = []  
			debit_account_id =[]
			credit_account_id = []
			for acc in account_move_obj.line_ids:
				if acc.account_id.od_prepaid_account and acc.debit >0:
					prepayment_acc.append(acc.account_id.id)
					debit_account_id.append(acc.account_id.id)

				elif acc.account_id.od_prepaid_account and acc.credit >0:
					prepayment_acc.append(acc.account_id.id)
					
					credit_account_id.append(acc.account_id.id)

			if len(prepayment_acc) ==0:
				raise ValidationError('no prepayment account')
#           if len(prepayment_acc) >=2:
#               raise ValidationError('multiple prepayment account')
					
			 
			date_start = datetime.datetime.strptime(str(data.date_start), "%Y-%m-%d")
			date_end = datetime.datetime.strptime(str(data.date_end), "%Y-%m-%d")# + timedelta(days=1)
			no_of_days = ((date_end - date_start).days + 1) or 1
			month_difference = (date_end.year - date_start.year)*12 + date_end.month - date_start.month
	# ((date_end).month) - ((date_start).month)

			res = []
			max_value = self.debit or self.credit
			no_of_lines = []
			partner =False
			# for line in account_move_obj.line_ids:
			#     if line.debit >max_value:
			#         max_value = line.debit
			#     no_of_lines.append(line.id)
			#     partner = line.partner_id.id or False  
			#     line_vals = {
			#             'account_id':wizard_account_id,
			#             'account_id':line.account_id.id,
			#             'analytic_id':line.analytic_account_id and line.analytic_account_id.id or False,
			#             'partner_id':line.partner_id and line.partner_id.id or False,
			#             'debit':line.debit,
			#             'credit':line.credit,
			#             }
			#     res.append((0, 0, line_vals),)

			# vals={
			#     'move_id':move_id,
			#     'account_id':wizard_account_id,
			#     'name':data.remark,
			#     'date_start':data.date_start,
			#     'date_end': data.date_end,
			#     'line_ids':res,
			#     'one_day_amount':max_value/no_of_days
			# }
			# if len(no_of_lines) >2:
			#     raise ValidationError('more than two lines found in move line')
			# prepayment_id = prepayment.create(vals)
			diff = 0
			debit_account_id = self.expense_account_id and self.expense_account_id.id
			analytic_acc_id = self.analytic_account_id and self.analytic_account_id.id
			cost_center = self.cost_center and self.cost_center.id
			company_id = self.company_id and self.company_id.id
			partner = self.linked_partner_id and self.linked_partner_id.id
			if month_difference ==0:
				diff = no_of_days
				ds = datetime.datetime.strptime(str(data.date_start), "%Y-%m-%d")
				first_day,last_day = self.get_month_day_range(ds)
				board_history_data = {'amount':(max_value/no_of_days) * diff,
				'prepayment_id':self.id,#prepayment_id and prepayment_id.id,
				'date':str(last_day),
				'journal_id':journal_id,
				'account_id':credit_account_id and credit_account_id[0] or wizard_account_id,
				'debit_account_id': debit_account_id or False,
				'cost_center':cost_center,
				'company_id':company_id,
				'analytic_account_id':analytic_acc_id,
				'partner_id':partner}
				self.env['orchid.prepayment.board.history'].create(board_history_data)
			if month_difference >=1:
				ds = datetime.datetime.strptime(str(data.date_start), "%Y-%m-%d")
				de = datetime.datetime.strptime(str(data.date_end), "%Y-%m-%d")
				first_day_of_start_date,last_day_of_start_date = self.get_month_day_range(ds)
				first_day_of_end_date,last_day_of_end_date = self.get_month_day_range(de)
				no_of_days_for_firstmonth = (last_day_of_start_date - ds).days +1
				no_of_days_last_month = (de - first_day_of_end_date).days + 1
				board_history_data = {'amount':(max_value/no_of_days) * no_of_days_for_firstmonth,
				'prepayment_id':self.id,#prepayment_id and prepayment_id.id,
				'date':str(last_day_of_start_date),
				'journal_id':journal_id,
				'account_id':credit_account_id and credit_account_id[0] or wizard_account_id,
				'debit_account_id': debit_account_id or False,
				'cost_center':cost_center,
				'company_id':company_id,
				'analytic_account_id':analytic_acc_id,
				'partner_id':partner}
				self.env['orchid.prepayment.board.history'].create(board_history_data)
				next_date = last_day_of_start_date
				while next_date < last_day_of_end_date:
					next_date = next_date + relativedelta(months=1)
					first_day_of_next_date,last_day_of_next_date = self.get_month_day_range(next_date)
					if not last_day_of_next_date >= last_day_of_end_date:
						first_day_of_next_date,last_day_of_next_date = self.get_month_day_range(next_date)
						days_in_intermediate_month = (last_day_of_next_date - first_day_of_next_date).days + 1

						query = {'amount':(max_value/no_of_days) * days_in_intermediate_month,
						'prepayment_id':self.id,#prepayment_id and prepayment_id.id,
						'date':str(last_day_of_next_date),
						'journal_id':journal_id,
						'cost_center':cost_center,
						'company_id':company_id,
						'analytic_account_id':analytic_acc_id,
						'account_id':credit_account_id and credit_account_id[0] or wizard_account_id,
						'debit_account_id': debit_account_id or False,
						'partner_id':partner}

						self.env['orchid.prepayment.board.history'].create(query)
						
				self.env['orchid.prepayment.board.history'].create({'amount':(max_value/no_of_days) * no_of_days_last_month,'prepayment_id':self.id,'date':str(last_day_of_end_date),'journal_id':journal_id,'account_id':credit_account_id and credit_account_id[0] or wizard_account_id,'partner_id':partner,'debit_account_id': debit_account_id or False,'analytic_account_id':analytic_acc_id,'cost_center':cost_center,'company_id':company_id,})
			
		return True



class account_account(models.Model):
	_inherit = 'account.account'

	od_prepaid_account = fields.Boolean('Prepaid Account')



class account_move(models.Model):
	_inherit = 'account.move'

	od_is_prepayment = fields.Boolean(string="Prepayment Entry",store=True,compute="_check_prepayment",default=False)
	
	
	@api.depends('state', 'line_ids.account_id')
	def _check_prepayment(self):
		for rec in self:
			print("hellllllllllllllllllllllllllllllllllllllllllllllllllll")
			od_is_prepayment = False
			for line in rec.line_ids:
				print("lkkkkjjjjjjjjjjjjcccc",line,line.account_id.od_prepaid_account, line.debit)
				if line.account_id.od_prepaid_account and line.debit:
					od_is_prepayment = True
			rec.od_is_prepayment = od_is_prepayment


	
	def open_prepayment_view(self):
		ids = []
		domain = []
		ids.append(self.id)
		domain.append(('move_id','in',ids))
		
		action = self.env['orchid.prepayment.lines'].load_prepayment_line()
		action['domain'] = domain
		return action

	
	def button_cancel(self):
		res = super(account_move, self).button_cancel()
		prepayment_objs = self.env['orchid.prepayment.lines'].search([('move_id','=',self.id)])
		for prepayment_obj in prepayment_objs:
			if prepayment_obj.state == 'draft':
				prepayment_obj.unlink()
			elif prepayment_obj.state != 'draft':
				raise ValidationError(_('There are generated prepayment lines!!'))
		return res
	
