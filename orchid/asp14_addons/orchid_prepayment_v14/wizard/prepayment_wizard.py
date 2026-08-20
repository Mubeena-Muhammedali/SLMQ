# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class prepayment_wizard(models.TransientModel):
	_name = "prepayment.wizard"

 
	date_start = fields.Date('Date From')
	date_to = fields.Date('Date To')
	company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id) 	

	
	
	def generate(self):
		date_start = self.date_start
		date_to = self.date_to
		lines = self.env['orchid.prepayment.board.history'].search([('date','>=',date_start),('date','<=',date_to),('company_id','=',self.company_id.id),('state','not in',('closed','cancel'))])
		move_ids = []
		for line in lines:
			partner_id = line.partner_id and line.partner_id.id
			date = line.date
			journal_id = line.journal_id and line.journal_id.id
			ref = 'Prepayment'
			if line.prepayment_id.move_id.name:
			
				ref = 'Prepayment'+"["+line.prepayment_id.move_id.name+"]"
			debit_account_id = line.debit_account_id and line.debit_account_id.id
			credit_account_id = line.account_id and line.account_id.id
			cost_center = line.cost_center and line.cost_center.id
			company_id = line.prepayment_id.move_id.company_id and line.prepayment_id.move_id.company_id.id
			analytic_id = line.analytic_account_id and line.analytic_account_id.id
			remarks = line.prepayment_id.remark
			amount = line.amount
			move_line = []
			
			if debit_account_id and credit_account_id and line.prepayment_id.state =='in_progress':

				debit_line = (0,0,{'account_id':debit_account_id,'partner_id':partner_id,'analytic_account_id':analytic_id,
				'name':remarks,'credit':0.0,'debit':amount,'orchid_cc_id':cost_center})
				credit_line = (0,0,{'account_id':credit_account_id,'partner_id':partner_id,
				'analytic_account_id':analytic_id,'name':remarks,'credit':amount,'debit':0,'orchid_cc_id':cost_center})    	    
				move_line.append(debit_line)  		    
				move_line.append(credit_line) 
				vals = {'date':date,'ref':ref,'journal_id':journal_id,'company_id':company_id,'line_ids':move_line,'move_type':'entry'} 		    
				move_id = self.env['account.move'].create(vals)
				move_ids.append(move_id.id)  		    
				line.state = 'closed' 
				line.entry_id =move_id.id  		    
				states_array = [] 		    
				for all_line in line.prepayment_id.line_history_ids:    	     		    
					states_array.append(all_line.state)
				
				if 'running' in states_array:
					all_line.prepayment_id.state = 'in_progress'
				
				else:
					all_line.prepayment_id.state = 'done'
		domain = []
		action = self.env.ref('account.action_move_journal_line')
		result = action.read()[0]
		domain.append(('id','in',move_ids))
			
		result['domain'] = domain
		return result
								
					
		


  
