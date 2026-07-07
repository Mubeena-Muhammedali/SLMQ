# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2019-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import fields, models
import xlsxwriter
from io import BytesIO
import base64
from collections import defaultdict
from datetime import datetime
import time



class AccountBalanceReport(models.TransientModel):
    _inherit = 'account.balance.report'

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'detail': self.detail,'groupby':self.groupby,'od_with_closing': self.od_with_closing})
        # data['form'].update({'detail': self.detail,'groupby':self.groupby})
        records = self.env[data['model']].browse(data.get('ids', []))
        data['form'].get('used_context').update({'landscape':True,'od_with_closing': self.od_with_closing})
        context = dict(data['form'].get('used_context'))
        return self.env.ref(
            'orchid_account_enhancement_v14.action_report_trial_balance').with_context(context).report_action(
            records, data=data)
    
    # def get_account_data(self,date_from,date_to,accounts,display_account,cost_center,target_move,od_with_closing):
    def get_account_data(self,date_from,date_to,accounts,display_account,target_move):
    
      cr=self.env.cr
      opening_result={}
      current_result={}
      closing_result={}
      if len(accounts.ids)==1:
        where_qry ="WHERE al.account_id = "+str(accounts.id)
      else:
        where_qry ="WHERE al.account_id IN "+str(tuple(accounts.ids))
      # if cost_center:
      #   where_qry = where_qry+" and al.orchid_cc_id="+"'"+str(cost_center)+"'"
      if not self.od_with_closing:
        where_qry = where_qry + " and aj.od_closing_journal is not true"
      if target_move=='posted':
        where_qry=where_qry+" and am.state='posted'"
      # if od_with_closing == False :
      #   where_qry = where_qry + " and aj.od_closing_journal is not true"      
      if date_from:
        open_qry=where_qry+ " and al.date <"+"'"+date_from+"' "
        financial_start_month = self.env['ir.config_parameter'].sudo().search([('key','=','od_financial_start_month')])
        if not financial_start_month:
          raise UserError(_("od_financial_start_month param is not set!!"))
        financial_start_month = int(financial_start_month.value)
        year_start_date = datetime.strptime(date_from, '%Y-%m-%d')
        year_start_date = year_start_date.replace(day=1)
        year_start_date = year_start_date.replace(month=financial_start_month)
        year_start_date = year_start_date.strftime('%Y-%m-%d')
        print("yearrr",year_start_date)
        pl_qry=open_qry+ " and al.date >="+"'"+str(year_start_date)+"' "

        union_qry1=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+open_qry+""" AND actp.include_initial_balance is true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_qry2=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+pl_qry+""" AND actp.include_initial_balance is not true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_qry = ("""%s UNION %s """)%(union_qry1,union_qry2)
        sql_query=("""SELECT 
                foo.id as id,
                foo.initial_balnce as initial_balnce,
                SUM(foo.debit) AS debit, 
                SUM(foo.credit) AS credit, 
                (SUM(foo.debit) - SUM(foo.credit)) AS balance 
                FROM 
                  (%s) as foo
                GROUP BY foo.id,foo.initial_balnce""")%(union_qry)
        # sql_query=("""SELECT 
        #         al.account_id as id,
        #         actp.include_initial_balance as initial_balnce,
        #         SUM(al.debit) AS debit, 
        #         SUM(al.credit) AS credit, 
        #         (SUM(al.debit) - SUM(al.credit)) AS balance 
        #         FROM account_move_line al
        #         LEFT JOIN account_move am ON am.id=al.move_id
        #         LEFT JOIN account_account a ON a.id =al.account_id
        #         -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
        #         LEFT JOIN account_journal aj ON aj.id = al.journal_id
        #         LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
        #         """+open_qry+""" GROUP BY al.account_id,actp.include_initial_balance""" )
        cr.execute(sql_query)
        for row in self.env.cr.dictfetchall():
          opening_result[row.pop('id')] = row
      if date_from and date_to:
        current_qry=where_qry+ " and al.date >="+"'"+date_from+"'"+" and al.date <="+"'"+date_to+"'"
        sql_query=("""SELECT 
                al.account_id as id,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                """+current_qry+""" GROUP BY al.account_id""" )
        cr.execute(sql_query)
        for row in self.env.cr.dictfetchall():
          current_result[row.pop('id')] = row
      if date_to:
        close_qry=where_qry+" and al.date <="+"'"+date_to+"'"
        financial_start_month = self.env['ir.config_parameter'].sudo().search([('key','=','od_financial_start_month')])
        if not financial_start_month:
          raise UserError(_("od_financial_start_month param is not set!!"))
        financial_start_month = int(financial_start_month.value)
        year_start_date = datetime.strptime(date_from, '%Y-%m-%d')
        year_start_date = year_start_date.replace(day=1)
        year_start_date = year_start_date.replace(month=financial_start_month)
        year_start_date = year_start_date.strftime('%Y-%m-%d')
        print("yearrr",year_start_date)
        pl_close_qry=close_qry+ " and al.date >="+"'"+str(year_start_date)+"' "
        union_close_qry1=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+close_qry+""" AND actp.include_initial_balance is true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_close_qry2=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+pl_close_qry+""" AND actp.include_initial_balance is not true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_close_qry = ("""%s UNION %s """)%(union_close_qry1,union_close_qry2)
        sql_query=("""SELECT 
                foo.id as id,
                foo.initial_balnce as initial_balnce,
                SUM(foo.debit) AS debit, 
                SUM(foo.credit) AS credit, 
                (SUM(foo.debit) - SUM(foo.credit)) AS balance 
                FROM 
                  (%s) as foo
                GROUP BY foo.id,foo.initial_balnce""")%(union_close_qry)
        # sql_query=("""SELECT 
        #         al.account_id as id,
        #         actp.include_initial_balance as initial_balnce,
        #         SUM(al.debit) AS debit, 
        #         SUM(al.credit) AS credit, 
        #         (SUM(al.debit) - SUM(al.credit)) AS balance 
        #         FROM account_move_line al
        #         LEFT JOIN account_move am ON am.id=al.move_id
        #         LEFT JOIN account_account a ON a.id =al.account_id
        #         -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
        #         LEFT JOIN account_journal aj ON aj.id = al.journal_id 
        #         LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
        #         """+close_qry+""" GROUP BY al.account_id,actp.include_initial_balance""" )
        cr.execute(sql_query)
        for row in self.env.cr.dictfetchall():
          closing_result[row.pop('id')] = row

      account_res = []
      opening_res=[]
      closing_res=[]
      current_res=[]
      for account in accounts:
        res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance',])
        currency = account.currency_id and account.currency_id or account.company_id.currency_id
        res['code'] = account.code
        res['name'] = account.name

        if account.id in opening_result:
          res['opening']=opening_result[account.id]
        else:
          res['opening']=False
        if account.id in current_result:
          res['current']=current_result[account.id]
        else:
          res['current']=False
        if account.id in closing_result:
          res['closing']=closing_result[account.id]
        else:
          res['closing']=False
        if not(res.get('opening')==False):
          for line in res.get('opening'):
            if account.id in opening_result:
              res['debit']+= opening_result[account.id].get('debit')   
              res['credit']+= opening_result[account.id].get('credit')  
              res['balance']+= opening_result[account.id].get('balance') 
        if not(res.get('current')==False):
          for line in res.get('current'):
            if account.id in current_result:
              res['debit']+= current_result[account.id].get('debit') 
              res['credit']+= current_result[account.id].get('credit') 
              res['balance']+= current_result[account.id].get('balance') 
        
        if not(res.get('closing')==False):
          for line in res.get('closing'):
            if account.id in closing_result:
              res['debit']+= closing_result[account.id].get('debit')   
              res['credit']+= closing_result[account.id].get('credit') 
              res['balance']+= closing_result[account.id].get('balance') 
        
        if display_account == 'all':
          account_res.append(res)
        if display_account == 'not_zero' and not currency.is_zero(res['balance']):
          account_res.append(res)
        if display_account == 'movement' and (not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
          account_res.append(res)

      return account_res

    def get_group_sum(self,date_from,date_to,accounts,display_account,target_move):
      cr=self._cr
      opening_result={}
      current_result={}
      closing_result={}
      # print("hereeeee",(tuple(accounts.ids)))

      if len(accounts.ids)==1:
        where_qry ="WHERE al.account_id = "+str(accounts.id)
      else:
        where_qry ="WHERE al.account_id IN "+str(tuple(accounts.ids))
      if not self.od_with_closing:
        where_qry = where_qry + " and aj.od_closing_journal is not true"
      if target_move=='posted':
        where_qry=where_qry+" and am.state='posted'"
      if date_from:
        open_qry=where_qry+ " and al.date <"+"'"+date_from+"' "
        financial_start_month = self.env['ir.config_parameter'].sudo().search([('key','=','od_financial_start_month')])
        if not financial_start_month:
          raise UserError(_("od_financial_start_month param is not set!!"))
        financial_start_month = int(financial_start_month.value)
        year_start_date = datetime.strptime(date_from, '%Y-%m-%d')
        year_start_date = year_start_date.replace(day=1)
        year_start_date = year_start_date.replace(month=financial_start_month)
        year_start_date = year_start_date.strftime('%Y-%m-%d')
        print("yearrr",year_start_date)
        pl_qry=open_qry+ " and al.date >="+"'"+str(year_start_date)+"' "

        union_qry1=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+open_qry+""" AND actp.include_initial_balance is true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_qry2=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+pl_qry+""" AND actp.include_initial_balance is not true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_qry = ("""%s UNION %s """)%(union_qry1,union_qry2)
        sql_query=("""SELECT 
                foo.id as id,
                foo.initial_balnce as initial_balnce,
                SUM(foo.debit) AS debit, 
                SUM(foo.credit) AS credit, 
                (SUM(foo.debit) - SUM(foo.credit)) AS balance 
                FROM 
                  (%s) as foo
                GROUP BY foo.id,foo.initial_balnce""")%(union_qry)
        # sql_query=("""SELECT 
        #         al.account_id as id,
        #         -- ag.id as id,
        #         actp.include_initial_balance as initial_balnce,
        #         SUM(al.debit) AS debit, 
        #         SUM(al.credit) AS credit, 
        #         (SUM(al.debit) - SUM(al.credit)) AS balance 
        #         FROM account_move_line al
        #         LEFT JOIN account_move am ON am.id=al.move_id
        #         LEFT JOIN account_account a ON a.id =al.account_id
        #         LEFT JOIN account_journal aj ON aj.id = al.journal_id
        #         LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
        #         """+open_qry+""" GROUP BY al.account_id, actp.include_initial_balance""" )
        cr.execute(sql_query)
        for row in self.env.cr.dictfetchall():
          opening_result[row.pop('id')] = row
      if date_from and date_to:
        current_qry=where_qry+ " and al.date >="+"'"+date_from+"'"+" and al.date <="+"'"+date_to+"'"
        sql_query=("""SELECT 
                al.account_id as id,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                """+current_qry+""" GROUP BY al.account_id""" )
        cr.execute(sql_query)
        for row in self.env.cr.dictfetchall():
          current_result[row.pop('id')] = row

      if date_to:
        close_qry=where_qry+" and al.date <="+"'"+date_to+"'"
        financial_start_month = self.env['ir.config_parameter'].sudo().search([('key','=','od_financial_start_month')])
        if not financial_start_month:
          raise UserError(_("od_financial_start_month param is not set!!"))
        financial_start_month = int(financial_start_month.value)
        year_start_date = datetime.strptime(date_from, '%Y-%m-%d')
        year_start_date = year_start_date.replace(day=1)
        year_start_date = year_start_date.replace(month=financial_start_month)
        year_start_date = year_start_date.strftime('%Y-%m-%d')
        print("yearrr",year_start_date)
        pl_close_qry=close_qry+ " and al.date >="+"'"+str(year_start_date)+"' "
        union_close_qry1=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+close_qry+""" AND actp.include_initial_balance is true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_close_qry2=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+pl_close_qry+""" AND actp.include_initial_balance is not true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_close_qry = ("""%s UNION %s """)%(union_close_qry1,union_close_qry2)
        sql_query=("""SELECT 
                foo.id as id,
                foo.initial_balnce as initial_balnce,
                SUM(foo.debit) AS debit, 
                SUM(foo.credit) AS credit, 
                (SUM(foo.debit) - SUM(foo.credit)) AS balance 
                FROM 
                  (%s) as foo
                GROUP BY foo.id,foo.initial_balnce""")%(union_close_qry)
        # sql_query=("""SELECT 
        #         al.account_id as id,
        #         actp.include_initial_balance as initial_balnce,
        #         SUM(al.debit) AS debit, 
        #         SUM(al.credit) AS credit, 
        #         (SUM(al.debit) - SUM(al.credit)) AS balance 
        #         FROM account_move_line al
        #         LEFT JOIN account_move am ON am.id=al.move_id
        #         LEFT JOIN account_account a ON a.id =al.account_id
        #         LEFT JOIN account_journal aj ON aj.id = al.journal_id 
        #         LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
        #         """+close_qry+""" GROUP BY al.account_id,actp.include_initial_balance""" )
        cr.execute(sql_query)
        for row in self.env.cr.dictfetchall():
          closing_result[row.pop('id')] = row

      account_res = []
      opening_res=[]
      closing_res=[]
      current_res=[]
      for account in accounts:
        res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance',])
        # account = self.env['account.account'].browse(account)
        currency = account.currency_id and account.currency_id or account.company_id.currency_id
        res['code'] = account.code
        res['name'] = account.name

        if account.id in opening_result:
          res['opening']=opening_result[account.id]
        else:
          res['opening']=False
        if account.id in current_result:
          res['current']=current_result[account.id]
        else:
          res['current']=False
        if account.id in closing_result:
          res['closing']=closing_result[account.id]
        else:
          res['closing']=False
        if not(res.get('opening')==False):
          for line in res.get('opening'):
            if account.id in opening_result:
              res['debit']+= opening_result[account.id].get('debit')   
              res['credit']+= opening_result[account.id].get('credit')  
              res['balance']+= opening_result[account.id].get('balance')

        if not(res.get('current')==False):
          for line in res.get('current'):
            if account.id in current_result:
              res['debit']+= current_result[account.id].get('debit') 
              res['credit']+= current_result[account.id].get('credit') 
              res['balance']+= current_result[account.id].get('balance') 
        
        if not(res.get('closing')==False):
          for line in res.get('closing'):
            if account.id in closing_result:
              res['debit']+= closing_result[account.id].get('debit')   
              res['credit']+= closing_result[account.id].get('credit') 
              res['balance']+= closing_result[account.id].get('balance') 
        
        if display_account == 'all':
          account_res.append(res)
        if display_account == 'not_zero' and not currency.is_zero(res['balance']):
          account_res.append(res)
        if display_account == 'movement' and (not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
          account_res.append(res)
      group_sum=[]
      res={'opening': {'debit': 0, 'credit': 0, 'balance': 0}, 'current': {'debit': 0, 'credit': 0, 'balance': 0}, 'closing': {'debit': 0, 'credit': 0, 'balance': 0}}
      for data in account_res:
        if date_from:
          if data.get('opening')==False:
            open_debit=0
            open_credit=0
            open_balance=open_debit-open_credit
            res['opening']['debit']=res['opening']['debit']+open_debit
            res['opening']['credit']=res['opening']['credit']+open_credit
            res['opening']['balance']=res['opening']['balance']+open_balance
          else:
            line_open = data.get('opening')
            # if line_open.get('initial_balnce') is not True:
            #   open_debit=0
            #   open_credit=0
            # else:
            #   open_debit=line_open.get('debit',0)
            #   open_credit=line_open.get('credit',0)
            open_debit=line_open.get('debit',0)
            open_credit=line_open.get('credit',0)
            open_balance=open_debit-open_credit
            res['opening']['debit']=res['opening']['debit']+open_debit
            res['opening']['credit']=res['opening']['credit']+open_credit
            res['opening']['balance']=res['opening']['balance']+open_balance
        if date_from and date_to:
          if data.get('current')==False:
            current_debit=0
            current_credit=0
            current_balance=current_debit-current_credit
            res['current']['debit']=res['current']['debit']+current_debit
            res['current']['credit']=res['current']['credit']+current_credit
            res['current']['balance']=res['current']['balance']+current_balance
          else:
            line_current=data.get('current')
            current_debit=line_current.get('debit',0)
            current_credit=line_current.get('credit',0)
            current_balance=current_debit-current_credit
            res['current']['debit']=res['current']['debit']+current_debit
            res['current']['credit']=res['current']['credit']+current_credit
            res['current']['balance']=res['current']['balance']+current_balance
            
        if date_to:
          if data.get('closing')==False:
            close_debit=0
            close_credit=0
            close_balance=close_debit-close_credit
            res['closing']['debit']=res['closing']['debit']+close_debit
            res['closing']['credit']=res['closing']['credit']+close_credit
            res['closing']['balance']=res['closing']['balance']+close_balance
          else:
            line_closing=data.get('closing')
            # if line_closing.get('initial_balnce') is not True:
            #   close_debit=current_debit
            #   close_credit=current_credit
            # else:
            #   close_debit=line_closing.get('debit',0)
            #   close_credit=line_closing.get('credit',0)
            close_debit=line_closing.get('debit',0)
            close_credit=line_closing.get('credit',0)
            close_balance=close_debit-close_credit
            res['closing']['debit']=res['closing']['debit']+close_debit
            res['closing']['credit']=res['closing']['credit']+close_credit
            res['closing']['balance']=res['closing']['balance']+close_balance
      group_sum.append(res)
      return group_sum

    def get_account_data_groupby(self,date_from,date_to,accounts,display_account,target_move):
    
      cr=self.env.cr
      opening_result={}
      current_result={}
      closing_result={}
      if len(accounts.ids)==1:
        where_qry ="WHERE al.account_id = "+str(accounts.id)
      else:
        where_qry ="WHERE al.account_id IN "+str(tuple(accounts.ids))
      # if cost_center:
      #   where_qry = where_qry+" and al.orchid_cc_id="+"'"+str(cost_center)+"'"
      if target_move=='posted':
        where_qry=where_qry+" and am.state='posted'"
      if not self.od_with_closing:
        where_qry = where_qry + " and aj.od_closing_journal is not true"
      # if od_with_closing == False :
      #   where_qry = where_qry + " and aj.od_closing_journal is not true"      
      if date_from:
        open_qry=where_qry+ " and al.date <"+"'"+date_from+"' "
        financial_start_month = self.env['ir.config_parameter'].sudo().search([('key','=','od_financial_start_month')])
        if not financial_start_month:
          raise UserError(_("od_financial_start_month param is not set!!"))
        financial_start_month = int(financial_start_month.value)
        year_start_date = datetime.strptime(date_from, '%Y-%m-%d')
        year_start_date = year_start_date.replace(day=1)
        year_start_date = year_start_date.replace(month=financial_start_month)
        year_start_date = year_start_date.strftime('%Y-%m-%d')
        print("yearrr",year_start_date)
        pl_qry=open_qry+ " and al.date >="+"'"+str(year_start_date)+"' "

        union_qry1=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+open_qry+""" AND actp.include_initial_balance is true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_qry2=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+pl_qry+""" AND actp.include_initial_balance is not true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_qry = ("""%s UNION %s """)%(union_qry1,union_qry2)
        sql_query=("""SELECT 
                foo.id as id,
                foo.initial_balnce as initial_balnce,
                SUM(foo.debit) AS debit, 
                SUM(foo.credit) AS credit, 
                (SUM(foo.debit) - SUM(foo.credit)) AS balance 
                FROM 
                  (%s) as foo
                GROUP BY foo.id,foo.initial_balnce""")%(union_qry)

        # sql_query=("""SELECT 
        #         al.account_id as id,
        #         actp.include_initial_balance as initial_balnce,
        #         SUM(al.debit) AS debit, 
        #         SUM(al.credit) AS credit, 
        #         (SUM(al.debit) - SUM(al.credit)) AS balance 
        #         FROM account_move_line al
        #         LEFT JOIN account_move am ON am.id=al.move_id
        #         LEFT JOIN account_account a ON a.id =al.account_id
        #         -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
        #         LEFT JOIN account_journal aj ON aj.id = al.journal_id
        #         LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
        #         """+open_qry+""" GROUP BY al.account_id,actp.include_initial_balance""" )
        print(sql_query)
        cr.execute(sql_query)
        for row in self.env.cr.dictfetchall():
          opening_result[row.pop('id')] = row
      if date_from and date_to:
        current_qry=where_qry+ " and al.date >="+"'"+date_from+"'"+" and al.date <="+"'"+date_to+"'"
        sql_query=("""SELECT 
                al.account_id as id,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                """+current_qry+""" GROUP BY al.account_id""" )
        cr.execute(sql_query)
        for row in self.env.cr.dictfetchall():
          current_result[row.pop('id')] = row
      if date_to:
        close_qry=where_qry+" and al.date <="+"'"+date_to+"'"
        financial_start_month = self.env['ir.config_parameter'].sudo().search([('key','=','od_financial_start_month')])
        if not financial_start_month:
          raise UserError(_("od_financial_start_month param is not set!!"))
        financial_start_month = int(financial_start_month.value)
        year_start_date = datetime.strptime(date_from, '%Y-%m-%d')
        year_start_date = year_start_date.replace(day=1)
        year_start_date = year_start_date.replace(month=financial_start_month)
        year_start_date = year_start_date.strftime('%Y-%m-%d')
        print("yearrr",year_start_date)
        pl_close_qry=close_qry+ " and al.date >="+"'"+str(year_start_date)+"' "
        union_close_qry1=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+close_qry+""" AND actp.include_initial_balance is true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_close_qry2=("""SELECT 
                al.account_id as id,
                actp.include_initial_balance as initial_balnce,
                SUM(al.debit) AS debit, 
                SUM(al.credit) AS credit, 
                (SUM(al.debit) - SUM(al.credit)) AS balance 
                FROM account_move_line al
                LEFT JOIN account_move am ON am.id=al.move_id
                LEFT JOIN account_account a ON a.id =al.account_id
                -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
                LEFT JOIN account_journal aj ON aj.id = al.journal_id
                LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
                """+pl_close_qry+""" AND actp.include_initial_balance is not true GROUP BY al.account_id,actp.include_initial_balance""" )
        union_close_qry = ("""%s UNION %s """)%(union_close_qry1,union_close_qry2)
        sql_query=("""SELECT 
                foo.id as id,
                foo.initial_balnce as initial_balnce,
                SUM(foo.debit) AS debit, 
                SUM(foo.credit) AS credit, 
                (SUM(foo.debit) - SUM(foo.credit)) AS balance 
                FROM 
                  (%s) as foo
                GROUP BY foo.id,foo.initial_balnce""")%(union_close_qry)
        # sql_query=("""SELECT 
        #         al.account_id as id,
        #         actp.include_initial_balance as initial_balnce,
        #         SUM(al.debit) AS debit, 
        #         SUM(al.credit) AS credit, 
        #         (SUM(al.debit) - SUM(al.credit)) AS balance 
        #         FROM account_move_line al
        #         LEFT JOIN account_move am ON am.id=al.move_id
        #         LEFT JOIN account_account a ON a.id =al.account_id
        #         -- LEFT JOIN orchid_account_cost_center cc ON (al.orchid_cc_id=cc.id)
        #         LEFT JOIN account_journal aj ON aj.id = al.journal_id 
        #         LEFT JOIN account_account_type actp ON a.user_type_id = actp.id
        #         """+close_qry+""" GROUP BY al.account_id,actp.include_initial_balance""" )
        cr.execute(sql_query)
        for row in self.env.cr.dictfetchall():
          closing_result[row.pop('id')] = row

      account_res = []
      internal_group_res = []
      account_type_res = []
      opening_res=[]
      closing_res=[]
      current_res=[]
      for account in accounts:
        res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance',])
        currency = account.currency_id and account.currency_id or account.company_id.currency_id
        res['code'] = account.code
        res['name'] = account.name
        res['internal_group'] = account.internal_group
        res['type'] = account.user_type_id.name

        if account.id in opening_result:
          res['opening']=opening_result[account.id]
        else:
          res['opening']=False
        if account.id in current_result:
          res['current']=current_result[account.id]
        else:
          res['current']=False
        if account.id in closing_result:
          res['closing']=closing_result[account.id]
        else:
          res['closing']=False
        if not(res.get('opening')==False):
          for line in res.get('opening'):
            if account.id in opening_result:
              res['debit']+= opening_result[account.id].get('debit')   
              res['credit']+= opening_result[account.id].get('credit')  
              res['balance']+= opening_result[account.id].get('balance') 
        if not(res.get('current')==False):
          for line in res.get('current'):
            if account.id in current_result:
              res['debit']+= current_result[account.id].get('debit') 
              res['credit']+= current_result[account.id].get('credit') 
              res['balance']+= current_result[account.id].get('balance') 
        
        if not(res.get('closing')==False):
          for line in res.get('closing'):
            if account.id in closing_result:
              res['debit']+= closing_result[account.id].get('debit')   
              res['credit']+= closing_result[account.id].get('credit') 
              res['balance']+= closing_result[account.id].get('balance') 
        
        if display_account == 'all':
          account_res.append(res)
        if display_account == 'not_zero' and not currency.is_zero(res['balance']):
          account_res.append(res)
        if display_account == 'movement' and (not currency.is_zero(res['debit']) or not currency.is_zero(res['credit'])):
          account_res.append(res)
      internal_groups = list(set([data.get('internal_group') for data in account_res]))
      account_type = list(set([data.get('type') for data in account_res]))
      for at in account_type:
        data_res = []
        for data in account_res:
          if at ==data.get('type'):
            data_res.append(data)
        if data_res:
          type_dict={}
          type_dict[at] = data_res
          account_type_res.append(type_dict)
      for ig in internal_groups:
        ig_data = []
        for data in account_type_res:
          for acc_type in account_type:
            data_ls = [] if data.get(acc_type)==None else data.get(acc_type)
            for d in data_ls:
              print("dataajjjjjj",d,ig)
          if d.get('internal_group')==ig:
            ig_data.append(data)
        if ig_data:
          grp_dict={}
          internal_gp=ig.upper()
          grp_dict[internal_gp] = ig_data
          internal_group_res.append(grp_dict)
      return internal_group_res

