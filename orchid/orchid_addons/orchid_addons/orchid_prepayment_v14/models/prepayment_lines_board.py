# -*- coding: utf-8 -*-

from odoo import models, fields, api
import openerp.addons.decimal_precision as dp

from odoo.exceptions import UserError,ValidationError

# class orchid_prepayment_board(models.Model):
#     _name = 'orchid.prepayment.board'
#     _description = 'Prepayment Board'

#     name = fields.Char(string='Recurring Name', readonly=True,required=True,copy=False)
#     date_start = fields.Date(string='Start Date',readonly=True, index=True,copy=False)
#     date_end = fields.Date(string='End Date',readonly=True, index=True,copy=False)
#     move_id = fields.Many2one('account.move', string='Entry',required=True,readonly="1")
#     account_id = fields.Many2one('account.account',string="Account",required="1",readonly="1")
#     prepayment_line_id = fields.Many2one('orchid.prepayment.lines',string='Prepayment Line Id')
#     one_day_amount = fields.Float(string='Amount Per Day',readonly="1")

#     state = fields.Selection([
#             ('running','Running'),
#             ('closed','Closed'),
#         ], string='Status',default='running')

#     line_ids = fields.One2many('orchid.prepayment.board.line', 'prepayment_id', string='MoveLines', copy=False)
#     line_history_ids = fields.One2many('orchid.prepayment.board.history', 'prepayment_id', string='History', copy=False)

# class orchid_prepayment_board_line(models.Model):
#     _name = 'orchid.prepayment.board.line'
#     _description = 'Prepayment Board Line'

#     prepayment_id = fields.Many2one('orchid.prepayment.board', readonly=True,string='Prepayment',ondelete='cascade')
#     partner_id = fields.Many2one('res.partner',string='Partner', readonly=True)
#     account_id = fields.Many2one('account.account', string='Account', readonly=True)
#     credit = fields.Float(string='Credit', readonly=True, digits=dp.get_precision('Account'))
#     debit = fields.Float(string='Debit', readonly=True, digits=dp.get_precision('Account'))
#     analytic_id = fields.Many2one('account.analytic.account', readonly=True,string='Analytic Account')
#     account_id = fields.Many2one('account.account', readonly=True,string='Account',required="1")

class orchid_prepayment_board_history(models.Model):
    _name = 'orchid.prepayment.board.history'
    _description = 'Prepayment Board Line History'
            
    prepayment_id = fields.Many2one('orchid.prepayment.lines', readonly=True,string='Prepayment',ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Credit Account', readonly=True)
    debit_account_id = fields.Many2one('account.account', string='Debit Account')
    partner_id = fields.Many2one('res.partner',string='Partner')
    amount = fields.Float('Amount', readonly=True)
    date = fields.Date('Date', readonly=True)
    journal_id = fields.Many2one('account.journal','journal', readonly=True)
    state = fields.Selection([
            ('running','Running'),
            ('closed','Closed'),
            ('cancel','Cancel'),
        ], string='Status',default='running', readonly=True)
    cost_center = fields.Many2one('orchid.account.cost.center',string="Cost Center")
    company_id = fields.Many2one('res.company',string="Company")
    analytic_account_id = fields.Many2one('account.analytic.account',string="Analytic Account")
    entry_id = fields.Many2one('account.move', string='Prepayment Journal Entry',required=True, readonly=True, ondelete='restrict')
    


    def action_prepayment_generate(self):
        data = self
        if data.state != 'running':
            raise ValidationError('You cannot create entries for this move') 
            return 0

        prepayment_ids = data
#        prepayment_ids = self.pool.get('od.prepayment.line.history').search(cr, uid,[('period_id', '=', period_id),('state','=','running')])
        account_move_obj = self.env['account.move']
            
        if prepayment_ids:
            account_move_id = self.env['account.move'].create({'journal_id':data.journal_id.id,'date':data.date})
            self.write({'state':'closed'})
            vals1 = {
                'journal_id':data.journal_id and data.journal_id.id,
                'date':data.date,
                'narration':'Prepayment',
                'name':'Prepayment:' + data.prepayment_id.move_id.name,
                'partner_id':data.partner_id and data.partner_id.id,
                'account_id':data.account_id and data.account_id.id,
                'credit':data.amount,
            }


            vals = {
                'journal_id':data.journal_id.id,
                'date':data.date,
                'narration':'Prepayment',
                'name':'Prepayment:' + data.prepayment_id.move_id.name,
                'partner_id':data.partner_id and data.partner_id.id,
                'account_id':data.debit_account_id and data.debit_account_id.id,
                'debit':data.amount,
            }
            data_lines = []
            data_lines.append((0,0,vals),)
            data_lines.append((0,0,vals1),)
            if account_move_id:
                self.env['account.move'].browse(account_move_id.id).write({'line_ids':data_lines})
            states = []
            prepayment_id = data.prepayment_id.id
            for objects in self.env['orchid.prepayment.board'].browse(prepayment_id):
                for lines in objects.line_history_ids:
                    states.append(lines.state)
                if 'running' not in states:
                    self.env['orchid.prepayment.board'].browse(objects.id).write({'state':'closed'})
        return True



