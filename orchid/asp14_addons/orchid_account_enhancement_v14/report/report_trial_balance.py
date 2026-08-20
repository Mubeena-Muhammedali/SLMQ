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

import time

from odoo import api, models, _
from odoo.exceptions import UserError
from datetime import datetime


class ReportTrialBalance(models.AbstractModel):
    _name = 'report.orchid_account_enhancement_v14.report_trial_balance'
    _description = 'Trial Balance Report'

    def _get_accounts(self, accounts, display_account):
        """ compute the balance, debit and credit for the provided accounts
            :Arguments:
                `accounts`: list of accounts record,
                `display_account`: it's used to display either all accounts or those accounts which balance is > 0
            :Returns a list of dictionary of Accounts with following key and value
                `name`: Account name,
                `code`: Account code,
                `credit`: total amount of credit,
                `debit`: total amount of debit,
                `balance`: total amount of balance,
        """

        account_result = {}
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        # compute the balance, debit and credit for the provided accounts
        request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
        params = (tuple(accounts.ids),) + tuple(where_params)
        # print("filterrrrr",filters)
        # print("where_clausewhere_clausewhere_clause",where_clause)
        # print("requeeeeee",request)
        # print("ppp",params)
        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res['code'] = account.code
            res['name'] = account.name
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(
                    res['credit'])):
                account_res.append(res)
        return account_res
        

    def _get_accounts_groupby(self, accounts, display_account):
        account_result = {}
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        # compute the balance, debit and credit for the provided accounts
        request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
        params = (tuple(accounts.ids),) + tuple(where_params)
        # print("filterrrrr",filters)
        # print("where_clausewhere_clausewhere_clause",where_clause)
        # print("requeeeeee",request)
        # print("ppp",params)
        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res['code'] = account.code
            res['name'] = account.name
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(
                    res['credit'])):
                account_res.append(res)
        d_res={'debit': 0, 'credit': 0, 'balance': 0}
        for data in account_res:
            d_res['debit'] = d_res['debit']+data.get('debit')
            d_res['credit'] = d_res['credit']+data.get('credit')
            d_res['balance'] = d_res['balance']+data.get('balance')
        # group_sum.append(res)
        return d_res

    def get_account_data(self,date_from,date_to,accounts,display_account,target_move):
        company = self.env['res.company'].browse(self.env.company.id)
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
        od_context = dict(self._context or {})
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
            print("fffffffff",financial_start_month)
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
                    """+open_qry+""" AND actp.include_initial_balance is true AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)
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
                    """+pl_qry+""" AND actp.include_initial_balance is not true AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)

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
            #         """+open_qry+""" AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)
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
                    """+current_qry+""" AND am.company_id=%s GROUP BY al.account_id""" )%(company.id)
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
                    """+close_qry+""" AND actp.include_initial_balance is true AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)
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
                    """+pl_close_qry+""" AND actp.include_initial_balance is not true AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)
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
            #         """+close_qry+""" AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)
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

    def get_account_data_groupby(self,date_from,date_to,accounts,display_account,target_move):
      company = self.env['res.company'].browse(self.env.company.id)
      cr=self._cr
      opening_result={}
      current_result={}
      closing_result={}
      if len(accounts.ids)==1:
        where_qry ="WHERE al.account_id = "+str(accounts.id)
      else:
        where_qry ="WHERE al.account_id IN "+str(tuple(accounts.ids))
      od_context = dict(self._context or {})
      # print("hhhhhhhhhhggggggggggg",od_context)
      # print(s)
      if target_move=='posted':
        where_qry=where_qry+" and am.state='posted'"
      if date_from:
        open_qry=where_qry+ " and al.date <"+"'"+date_from+"' "
        financial_start_month = self.env['ir.config_parameter'].sudo().search([('key','=','od_financial_start_month')])
        if not financial_start_month:
          raise UserError(_("od_financial_start_month param is not set!!"))
        financial_start_month = int(financial_start_month.value)
        print("fffffffff",financial_start_month)
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
                """+open_qry+""" AND actp.include_initial_balance is true AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)
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
                """+pl_qry+""" AND actp.include_initial_balance is not true AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)

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
                """+close_qry+""" AND actp.include_initial_balance is true AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)
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
                """+pl_close_qry+""" AND actp.include_initial_balance is not true AND am.company_id=%s GROUP BY al.account_id,actp.include_initial_balance""" )%(company.id)
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
      # group_sum=[]
      res={'open_debit': 0, 'open_credit': 0, 'open_balance': 0, 'current_debit': 0, 'current_credit': 0, 'current_balance': 0, 'close_debit': 0, 'close_credit': 0, 'close_balance': 0}
      for data in account_res:
        if date_from:
          if data.get('opening')==False:
            open_debit=0
            open_credit=0
            open_balance=open_debit-open_credit
            res['open_debit']=res['open_debit']+open_debit
            res['open_credit']=res['open_credit']+open_credit
            res['open_balance']=res['open_balance']+open_balance
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
            res['open_debit']=res['open_debit']+open_debit
            res['open_credit']=res['open_credit']+open_credit
            res['open_balance']=res['open_balance']+open_balance
        if date_from and date_to:
          if data.get('current')==False:
            current_debit=0
            current_credit=0
            current_balance=current_debit-current_credit
            res['current_debit']=res['current_debit']+current_debit
            res['current_credit']=res['current_credit']+current_credit
            res['current_balance']=res['current_balance']+current_balance
          else:
            line_current=data.get('current')
            current_debit=line_current.get('debit',0)
            current_credit=line_current.get('credit',0)
            current_balance=current_debit-current_credit
            res['current_debit']=res['current_debit']+current_debit
            res['current_credit']=res['current_credit']+current_credit
            res['current_balance']=res['current_balance']+current_balance
            
        if date_to:
          if data.get('closing')==False:
            close_debit=0
            close_credit=0
            close_balance=close_debit-close_credit
            res['close_debit']=res['close_debit']+close_debit
            res['close_credit']=res['close_credit']+close_credit
            res['close_balance']=res['close_balance']+close_balance
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
            res['close_debit']=res['close_debit']+close_debit
            res['close_credit']=res['close_credit']+close_credit
            res['close_balance']=res['close_balance']+close_balance
      # group_sum.append(res)
      return res

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(
            self.env.context.get('active_ids', []))
        display_account = data['form'].get('display_account')
        accounts = docs if model == 'account.account' else self.env[
            'account.account'].search([])

        if not (data['form'].get('detail')) and not (data['form'].get('groupby')):
            # account_data =self.get_account_data(str(data['form'].get('date_from')),str(data['form'].get('date_to')),accounts,display_account,data['form'].get('target_move'))
            # print("accounttttffffff",account_data)
            # else:
            account_res = self.with_context(data['form'].get('used_context'))._get_accounts(accounts,display_account)
            # print("acccccccc",account_res)
        
            # return {
            #     'doc_ids': self.ids,
            #     'doc_model': model,
            #     'data': data['form'],
            #     'docs': docs,
            #     'time': time,
            #     'Accounts': account_res,
            # }
        elif not (data['form'].get('detail')) and (data['form'].get('groupby')):
            account_res=[]
            for group in self.env['od.report.template'].search([('report_value','=','tb'),('company_id','=',data['form'].get('company_id')[0])], order='sequence asc'):
                group_accounts = []
                if group.display_details=='compute':
                    for subgroup in group.account_group_ids:
                      for acc in subgroup.name.account_account_ids:
                        group_accounts.append(acc.name.id)
                    accounts = self.env['account.account'].browse(group_accounts)
                    group_data =self.with_context(data['form'].get('used_context'))._get_accounts_groupby(accounts,display_account)
                    group_data['name']=group.name
                    group_data['d_type']=group.display_details
                    account_res.append(group_data)
                if group.display_details=='accounts':
                    for acc in group.account_account_ids:
                      group_accounts.append(acc.name.id)
                    accounts = self.env['account.account'].browse(group_accounts)
                    group_data = self.with_context(data['form'].get('used_context'))._get_accounts_groupby(accounts,display_account)
                    group_data['name']=group.name
                    group_data['d_type']=group.display_details
                    account_res.append(group_data)
                    account_data = self.with_context(data['form'].get('used_context'))._get_accounts(accounts,display_account)
                    for a_data in account_data:
                        a_data['d_type']='account'
                        account_res.append(a_data)
        elif (data['form'].get('detail')) and (data['form'].get('groupby')):
            account_res=[]
            for group in self.env['od.report.template'].search([('report_value','=','tb'),('company_id','=',data['form'].get('company_id')[0])], order='sequence asc'):
                group_accounts = []
                if group.display_details=='compute':
                    for subgroup in group.account_group_ids:
                      for acc in subgroup.name.account_account_ids:
                        group_accounts.append(acc.name.id)
                    accounts = self.env['account.account'].browse(group_accounts)
                    group_data =self.get_account_data_groupby(str(data['form'].get('date_from')),str(data['form'].get('date_to')),accounts,display_account,data['form'].get('target_move'))
                    group_data['name']=group.name
                    group_data['d_type']=group.display_details
                    account_res.append(group_data)
                if group.display_details=='accounts':
                    for acc in group.account_account_ids:
                      group_accounts.append(acc.name.id)
                    accounts = self.env['account.account'].browse(group_accounts)
                    group_data = self.get_account_data_groupby(str(data['form'].get('date_from')),str(data['form'].get('date_to')),accounts,display_account,data['form'].get('target_move'))
                    group_data['name']=group.name
                    group_data['d_type']=group.display_details
                    account_res.append(group_data)
                    account_data = self.with_context(data['form'].get('used_context')).get_account_data(str(data['form'].get('date_from')),str(data['form'].get('date_to')),accounts,display_account,data['form'].get('target_move'))
                    date_from =  data['form']['date_from']
                    date_to =  data['form']['date_to']
                    ototal_debit=0
                    ototal_credit=0
                    ototal_balance=0
                    ctotal_debit=0
                    ctotal_credit=0
                    ctotal_balance=0
                    cltotal_debit=0
                    cltotal_credit=0
                    cltotal_balance=0
                    for a_data in account_data:
                        data_res={}
                        code=a_data.get('code')
                        name = a_data.get('name')
                        credit = a_data.get('credit')
                        debit = a_data.get('debit')
                        balance = a_data.get('balance')
                        data_res['code'] = code
                        data_res['name'] = name
                        data_res['d_type'] = 'account'
                        if date_from:
                          if a_data.get('opening')==False:
                            open_debit=0
                            open_credit=0
                            open_balance=open_debit-open_credit
                            data_res['open_debit'] = open_debit
                            data_res['open_credit'] = open_credit
                            data_res['open_balance'] = open_balance
                            ototal_debit=ototal_debit+open_debit
                            ototal_credit=ototal_credit+open_credit
                            ototal_balance=ototal_balance+open_balance
                          else:
                            line_open = a_data.get('opening')
                            # if line_open.get('initial_balnce') is not True:
                            #   open_debit=0
                            #   open_credit=0
                            # else:
                            #   open_debit=line_open.get('debit',0)
                            #   open_credit=line_open.get('credit',0)
                            open_debit=line_open.get('debit',0)
                            open_credit=line_open.get('credit',0)
                            open_balance=open_debit-open_credit
                            data_res['open_debit'] = open_debit
                            data_res['open_credit'] = open_credit
                            data_res['open_balance'] = open_balance
                            ototal_debit=ototal_debit+open_debit
                            ototal_credit=ototal_credit+open_credit
                            ototal_balance=ototal_balance+open_balance
                        if date_from and date_to:
                          if a_data.get('current')==False:
                            current_debit=0
                            current_credit=0
                            current_balance=current_debit-current_credit
                            # sheet.write(row,col,current_debit,style7)
                            # col=col+1
                            # sheet.write(row,col,current_credit,style7)
                            # col=col+1
                            # sheet.write(row,col,current_balance,style7)
                            data_res['current_debit'] = current_debit
                            data_res['current_credit'] = current_credit
                            data_res['current_balance'] = current_balance
                            ctotal_debit=ctotal_debit+current_debit
                            ctotal_credit=ctotal_credit+current_credit
                            ctotal_balance=ctotal_balance+current_balance
                          else:
                            line_current=a_data.get('current')
                            # if self.od_currency:
                            #     line_current['credit'] = line_current['credit'] * self.od_rate
                            #     line_current['debit'] = line_current['debit'] * self.od_rate
                            current_debit=line_current.get('debit',0)
                            current_credit=line_current.get('credit',0)
                            current_balance=current_debit-current_credit
                            data_res['current_debit'] = current_debit
                            data_res['current_credit'] = current_credit
                            data_res['current_balance'] = current_balance
                            ctotal_debit=ctotal_debit+current_debit
                            ctotal_credit=ctotal_credit+current_credit
                            ctotal_balance=ctotal_balance+current_balance
                            
                        if date_to:
                          if a_data.get('closing')==False:
                            close_debit=0
                            close_credit=0
                            close_balance=close_debit-close_credit
                            data_res['close_debit'] = close_debit
                            data_res['close_credit'] = close_credit
                            data_res['close_balance'] = close_balance
                            cltotal_debit=cltotal_debit+close_debit
                            cltotal_credit=cltotal_credit+close_credit
                            cltotal_balance=cltotal_balance+close_balance
                          else:
                            line_closing=a_data.get('closing')
                            # if self.od_currency:
                            #     line_closing['credit'] = line_closing['credit'] * self.od_rate
                            #     line_closing['debit'] = line_closing['debit'] * self.od_rate
                            # if line_closing.get('initial_balnce') is not True:
                            #   close_debit=current_debit
                            #   close_credit=current_credit
                            # else:
                            #   close_debit=line_closing.get('debit',0)
                            #   close_credit=line_closing.get('credit',0)
                            close_debit=line_closing.get('debit',0)
                            close_credit=line_closing.get('credit',0)
                            close_balance=close_debit-close_credit
                            data_res['close_debit'] = close_debit
                            data_res['close_credit'] = close_credit
                            data_res['close_balance'] = close_balance
                            cltotal_debit=cltotal_debit+close_debit
                            cltotal_credit=cltotal_credit+close_credit
                            cltotal_balance=cltotal_balance+close_balance
                        account_res.append(data_res)

        elif (data['form'].get('detail')) and not (data['form'].get('groupby')):
            # print("yessssss",data['form'].get('detail'))
            account_data =self.get_account_data(str(data['form'].get('date_from')),str(data['form'].get('date_to')),accounts,display_account,data['form'].get('target_move'))
            # print("accccccccggggggggg",account_data)
            account_res=[]
            date_from =  data['form']['date_from']
            date_to =  data['form']['date_to']
            ototal_debit=0
            ototal_credit=0
            ototal_balance=0
            ctotal_debit=0
            ctotal_credit=0
            ctotal_balance=0
            cltotal_debit=0
            cltotal_credit=0
            cltotal_balance=0
            for a_data in account_data:
                data_res={}
                # print("dataaaaa")
                code=a_data.get('code')
                name = a_data.get('name')
                credit = a_data.get('credit')
                debit = a_data.get('debit')
                balance = a_data.get('balance')
                data_res['code'] = code
                data_res['name'] = name
                if date_from:
                  if a_data.get('opening')==False:
                    open_debit=0
                    open_credit=0
                    open_balance=open_debit-open_credit
                    data_res['open_debit'] = open_debit
                    data_res['open_credit'] = open_credit
                    data_res['open_balance'] = open_balance
                    ototal_debit=ototal_debit+open_debit
                    ototal_credit=ototal_credit+open_credit
                    ototal_balance=ototal_balance+open_balance
                  else:
                    line_open = a_data.get('opening')
                    # if line_open.get('initial_balnce') is not True:
                    #     print("joookmmmmmmmmmmmmmm",line_open,name)
                    #   open_debit=0
                    #   open_credit=0
                    # else:
                    #   open_debit=line_open.get('debit',0)
                    #   open_credit=line_open.get('credit',0)
                    open_debit=line_open.get('debit',0)
                    open_credit=line_open.get('credit',0)
                    open_balance=open_debit-open_credit
                    data_res['open_debit'] = open_debit
                    data_res['open_credit'] = open_credit
                    data_res['open_balance'] = open_balance
                    print("ddddd",data_res)
                    ototal_debit=ototal_debit+open_debit
                    ototal_credit=ototal_credit+open_credit
                    ototal_balance=ototal_balance+open_balance
                if date_from and date_to:
                  if a_data.get('current')==False:
                    current_debit=0
                    current_credit=0
                    current_balance=current_debit-current_credit
                    # sheet.write(row,col,current_debit,style7)
                    # col=col+1
                    # sheet.write(row,col,current_credit,style7)
                    # col=col+1
                    # sheet.write(row,col,current_balance,style7)
                    data_res['current_debit'] = current_debit
                    data_res['current_credit'] = current_credit
                    data_res['current_balance'] = current_balance
                    ctotal_debit=ctotal_debit+current_debit
                    ctotal_credit=ctotal_credit+current_credit
                    ctotal_balance=ctotal_balance+current_balance
                  else:
                    line_current=a_data.get('current')
                    # if self.od_currency:
                    #     line_current['credit'] = line_current['credit'] * self.od_rate
                    #     line_current['debit'] = line_current['debit'] * self.od_rate
                    current_debit=line_current.get('debit',0)
                    current_credit=line_current.get('credit',0)
                    current_balance=current_debit-current_credit
                    data_res['current_debit'] = current_debit
                    data_res['current_credit'] = current_credit
                    data_res['current_balance'] = current_balance
                    ctotal_debit=ctotal_debit+current_debit
                    ctotal_credit=ctotal_credit+current_credit
                    ctotal_balance=ctotal_balance+current_balance
                    
                if date_to:
                  if a_data.get('closing')==False:
                    close_debit=0
                    close_credit=0
                    close_balance=close_debit-close_credit
                    data_res['close_debit'] = close_debit
                    data_res['close_credit'] = close_credit
                    data_res['close_balance'] = close_balance
                    cltotal_debit=cltotal_debit+close_debit
                    cltotal_credit=cltotal_credit+close_credit
                    cltotal_balance=cltotal_balance+close_balance
                  else:
                    line_closing=a_data.get('closing')
                    # if self.od_currency:
                    #     line_closing['credit'] = line_closing['credit'] * self.od_rate
                    #     line_closing['debit'] = line_closing['debit'] * self.od_rate
                    # if line_closing.get('initial_balnce') is not True:
                    #   close_debit=current_debit
                    #   close_credit=current_credit
                    # else:
                    #   close_debit=line_closing.get('debit',0)
                    #   close_credit=line_closing.get('credit',0)
                    close_debit=line_closing.get('debit',0)
                    close_credit=line_closing.get('credit',0)
                    close_balance=close_debit-close_credit
                    data_res['close_debit'] = close_debit
                    data_res['close_credit'] = close_credit
                    data_res['close_balance'] = close_balance
                    cltotal_debit=cltotal_debit+close_debit
                    cltotal_credit=cltotal_credit+close_credit
                    cltotal_balance=cltotal_balance+close_balance
                account_res.append(data_res)
        # print("lllll",account_res)
        # print("pppppppppp",data)
        # print("nnnnnnnnnnnnnn",data['form'])
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Accounts': account_res,
        } 
