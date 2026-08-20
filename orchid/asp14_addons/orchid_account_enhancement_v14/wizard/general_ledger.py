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

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import get_lang
import xlsxwriter
from io import BytesIO
import base64
from datetime import datetime


class AccountReportGeneralLedger(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    initial_balance = fields.Boolean(string='Include Initial Balances',
                                     help='If you selected date, this field '
                                          'allow you to add a row to display '
                                          'the amount of debit/credit/balance '
                                          'that precedes the filter you\'ve '
                                          'set.')
    sortby = fields.Selection(
        [('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')],
        string='Sort by', required=True, default='sort_date')
    journal_ids = fields.Many2many('account.journal',
                                   'account_report_general_ledger_journal_rel',
                                   'account_id', 'journal_id',
                                   string='Journals', required=True)
    account_ids = fields.Many2many('account.account',string="Accounts")
    partner_ids = fields.Many2many('res.partner',string="Partners")
    excel_file = fields.Binary(string='Dowload Report Excel',readonly="1")
    file_name = fields.Char(string='Excel File',readonly="1")

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update(self.read(['initial_balance', 'sortby'])[0])
        account_ids = self.account_ids and self.account_ids.ids or False
        partner_ids = self.partner_ids and self.partner_ids.ids or False
        data['form'].update({'account_ids': account_ids,'partner_ids': partner_ids})
        if not data['form'].get('account_ids'):
          raise UserError(_("You must select at least one account"))
        if not data['form'].get('journal_ids'):
          raise UserError(_("You must select at least one journal"))

        if data['form'].get('initial_balance') and not data['form'].get(
                'date_from'):
            raise UserError(_("You must define a Start Date"))
        records = self.env[data['model']].browse(data.get('ids', []))
        return self.env.ref(
            'orchid_account_enhancement_v14.action_report_general_ledger').with_context(
            landscape=True).report_action(records, data=data)


    #************************EXCEL**************#
    def od_generate_excel_report(self):
      self.ensure_one()
      data = {}
      data['ids'] = self.env.context.get('active_ids', [])
      data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
      data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
      used_context = self._build_contexts(data)
      data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
      data = self.pre_print_report(data)
      data['form'].update(self.read(['initial_balance', 'sortby'])[0])
      account_ids = self.account_ids and self.account_ids.ids or False
      partner_ids = self.partner_ids and self.partner_ids.ids or False
      data['form'].update({'account_ids': account_ids,'partner_ids': partner_ids})
      if not data['form'].get('account_ids'):
        raise UserError(_("You must select at least one account"))
      if not data['form'].get('journal_ids'):
        raise UserError(_("You must select at least one journal"))

      if data['form'].get('initial_balance') and not data['form'].get(
              'date_from'):
          raise UserError(_("You must define a Start Date"))

      # get report values
      if not data.get('form'):
          raise UserError(
              _("Form content is missing, this report cannot be printed."))

      model='account.report.general.ledger'
      docs = self.env[model].browse(
          self.env.context.get('active_ids', []))

      init_balance = data['form'].get('initial_balance', True)
      sortby = data['form'].get('sortby', 'sort_date')
      display_account = data['form']['display_account']
      codes = []
      if data['form'].get('journal_ids', False):
          codes = [journal.code for journal in
                   self.env['account.journal'].search(
                       [('id', 'in', data['form']['journal_ids'])])]


      if data['form']['account_ids']:
          account_ids = data['form']['account_ids']
          accounts = self.env['account.account'].browse(account_ids)
      else:
          accounts = docs if model == 'account.account' else self.env[
              'account.account'].search([])

      od_partner_search_condition = ''' '''
      if data['form']['partner_ids']:
          partner_ids = data['form']['partner_ids']
          partners = self.env['res.partner'].browse(partner_ids)
          od_partner_search_condition = od_partner_search_condition + ''' and l.partner_id in %s '''
      else:
          partners = False

      accounts_res = self.with_context(
          data['form'].get('used_context', {}))._get_account_move_entry(
          accounts, init_balance, sortby, display_account, partners,od_partner_search_condition)


      output = BytesIO()
      workbook = xlsxwriter.Workbook(output)
      sheet= workbook.add_worksheet('Partner Ledger')
      style = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'left','valign':'vcenter','bg_color':'#E3E4FA'})
      style_0 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'right','valign':'vcenter','bg_color':'#E3E4FA'})
      style1 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'left','valign':'vcenter','bg_color':'#F5F5DC'})
      style2 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'right','valign':'vcenter','bg_color':'#F5F5DC','num_format':'#,##0.00'})
      style3 = workbook.add_format({'font_size':8,'font_name':'Arial','align':'left','valign':'vcenter'})
      style4 = workbook.add_format({'font_size':8,'font_name':'Arial','align':'right','valign':'vcenter','num_format':'#,##0.00'})
      style5 = workbook.add_format({'font_size':10,'bold':True,'font_name':'Arial','align':'center','valign':'vcenter'})
      style6 = workbook.add_format({'font_size':10,'bold':True,'font_name':'Arial','align':'left','valign':'vcenter'})
     
      row=0
      col=0
      row_merge=row
      col=0
      sheet.set_column('C:C',45)
      sheet.set_column('D:D',45)
      sheet.set_column('F:F',45)
      sheet.set_column('E:E',45)
      headings = ['Date','JRNL','Partner','Ref','Move','Entry Label','Debit','Credit','Balance','Cum.Balance']
      col_merge=col+19
      sheet.merge_range(row,col,row,col_merge,"General Ledger",style5)
      row = row+2
      if self.date_from:
        col=0
        sheet.merge_range(row,col,row,2,"Date From"+" :"+str(self.date_from),style6)
        row=row+1
      if self.date_to:
        col=0
        sheet.merge_range(row,col,row,2,"Date to"+"      :"+str(self.date_to),style6)
        row=row+1
      if self.journal_ids:
        col=0
        sheet.set_column('A:A',45)
        jrnl=(', '.join(j.name or '' for j in self.journal_ids))
        sheet.merge_range(row,col,row,2,"Journals"+"      :"+str(jrnl),style6)
        row=row+1
      if data['form']['display_account'] == 'all':
        display_account="All accounts"
      elif data['form']['display_account'] == 'movement':
        display_account="With movements"
      else:
        display_account="With balance not equal to zero"
      col=0
      sheet.merge_range(row,col,row,2,"Display Accounts"+"      :"+str(display_account),style6)
      row=row+1
      if data['form']['target_move'] == 'all':
        target_move="All Entries"
      else:
        target_move="All Posted Entries"
      col=0
      sheet.merge_range(row,col,row,2,"Target Moves"+"      :"+str(target_move),style6)
      row=row+1
      if data['form']['sortby'] == 'sort_date':
        sorted_by="Date"
      else:
        sorted_by="Journal and Partner"
      col=0
      sheet.merge_range(row,col,row,2,"Sorted By"+"      :"+str(sorted_by),style6)
      row=row+1
      col=0
      sheet.merge_range(row,col,row,2,"Currency"+"   :"+self.env.company.currency_id.name,style6)
      col=0
      row = row+2
      for heading in headings:
          style=style
          if heading in ['Debit','Credit','Cum.Balance','Balance']:
              style=style_0
          sheet.write(row,col,heading,style)
          col = col+1
      
      row=row+1
      for account in accounts_res:
        col=0
        col_merge=5
        sheet.merge_range(row,col,row,col_merge,str(account['code'])+str(account['name']),style1)
        col=col_merge+1
        sheet.write(row,col,account['debit'],style2)
        col=col+1
        sheet.write(row,col,account['credit'],style2)
        col=col+1
        sheet.write(row,col,account['balance'],style2)
        col=col+1
        sheet.write(row,col,account['balance'],style2)
        row=row+1
        for line in account['move_lines']:
          col=0
          if line['ldate']:
            date = datetime.strptime(str(line['ldate']), '%Y-%m-%d').strftime('%d-%m-%Y')
          else:
            date=line['ldate']
          # date=
          # print("kkkkkkkkk",line)
          sheet.write(row,col,date,style3)
          col=col+1
          sheet.write(row,col,line['lcode'],style3)
          col=col+1
          sheet.write(row,col,line['partner_name'],style3)
          col=col+1
          sheet.write(row,col,line['lref'],style3)
          col=col+1
          sheet.write(row,col,line['move_name'],style3)
          col=col+1
          sheet.write(row,col,line['lname'],style3)
          col=col+1
          sheet.write(row,col,line['debit'],style4)
          col=col+1
          sheet.write(row,col,line['credit'],style4)
          col=col+1
          sheet.write(row,col,(line['debit']-line['credit']),style4)
          col=col+1
          sheet.write(row,col,line['balance'],style4)
          row=row+1



      workbook.close()
      output.seek(0)
      excel_file = base64.encodestring(output.read())
      self.excel_file = excel_file
      filename= 'GeneralLedger.xlsx'
      self.file_name =filename
      ir_model_data = self.env['ir.model.data']
      compose_form_id = ir_model_data.get_object_reference('orchid_account_enhancement_v14', 'account_report_general_ledger_view')[1]

      return {            
      'type': 'ir.actions.act_window',            
      'view_type': 'form',            
      'view_mode': 'form',            
      'res_model': 'account.report.general.ledger',            
      'views': [(compose_form_id, 'form')], 
      'res_id': self.id,           
      'view_id': compose_form_id,            
      'target': 'new',            
      }




    def _get_account_move_entry(self, accounts, init_balance, sortby,
                            display_account, partners,od_partner_search_condition):
      """
      :param:
              accounts: the recordset of accounts
              init_balance: boolean value of initial_balance
              sortby: sorting by date or partner and journal
              display_account: type of account(receivable, payable and both)

      Returns a dictionary of accounts with following key and value {
              'code': account code,
              'name': account name,
              'debit': sum of total debit amount,
              'credit': sum of total credit amount,
              'balance': total balance,
              'amount_currency': sum of amount_currency,
              'move_lines': list of move line
      }
      """
      cr = self.env.cr
      MoveLine = self.env['account.move.line']
      move_lines = {x: [] for x in accounts.ids}

      # Prepare initial sql query and Get the initial move lines
      if init_balance:
          init_tables, init_where_clause, init_where_params = MoveLine.with_context(
              date_from=self.env.context.get('date_from'), date_to=False,
              initial_bal=True)._query_get()
          init_wheres = [""]
          if init_where_clause.strip():
              init_wheres.append(init_where_clause.strip())
          init_filters = " AND ".join(init_wheres)
          filters = init_filters.replace('account_move_line__move_id',
                                         'm').replace('account_move_line',
                                                      'l')
          sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate, '' AS lcode, 0.0 AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance, '' AS lpartner_id,\
              '' AS move_name, '' AS mmove_id, '' AS currency_code,\
              NULL AS currency_id,\
              '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
              '' AS partner_name\
              FROM account_move_line l\
              LEFT JOIN account_move m ON (l.move_id=m.id)\
              LEFT JOIN res_currency c ON (l.currency_id=c.id)\
              LEFT JOIN res_partner p ON (l.partner_id=p.id)\
              LEFT JOIN account_move i ON (m.id =i.id)\
              JOIN account_journal j ON (l.journal_id=j.id)\
              WHERE l.account_id IN %s"""+ od_partner_search_condition + filters + ' GROUP BY l.account_id')
          

          if od_partner_search_condition != ''' ''':
              params = (tuple(accounts.ids),) + (tuple(partners.ids),) + tuple(init_where_params)
          else:
              params = (tuple(accounts.ids),) + tuple(init_where_params)
          cr.execute(sql, params)
          for row in cr.dictfetchall():
              move_lines[row.pop('account_id')].append(row)

      sql_sort = 'l.date, l.move_id'
      if sortby == 'sort_journal_partner':
          sql_sort = 'j.code, p.name, l.move_id'

      # Prepare sql query base on selected parameters from wizard
      tables, where_clause, where_params = MoveLine._query_get()
      wheres = [""]
      if where_clause.strip():
          wheres.append(where_clause.strip())
      filters = " AND ".join(wheres)
      filters = filters.replace('account_move_line__move_id', 'm').replace(
          'account_move_line', 'l')

      # Get move lines base on sql query and Calculate the total balance of move lines
      sql = ('''SELECT l.id AS lid, l.account_id AS account_id, l.date AS ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) AS balance,\
          m.name AS move_name, c.symbol AS currency_code, p.name AS partner_name\
          FROM account_move_line l\
          JOIN account_move m ON (l.move_id=m.id)\
          LEFT JOIN res_currency c ON (l.currency_id=c.id)\
          LEFT JOIN res_partner p ON (l.partner_id=p.id)\
          JOIN account_journal j ON (l.journal_id=j.id)\
          JOIN account_account acc ON (l.account_id = acc.id) \
          WHERE l.account_id IN %s '''+ od_partner_search_condition + filters + ''' GROUP BY l.id, l.account_id, l.date, j.code, l.currency_id, l.amount_currency, l.ref, l.name, m.name, c.symbol, p.name ORDER BY ''' + sql_sort)
      if od_partner_search_condition != ''' ''':
          params = (tuple(accounts.ids),) + (tuple(partners.ids),) + tuple(where_params)
      else:
          params = (tuple(accounts.ids),) + tuple(where_params)

      cr.execute(sql, params)

      for row in cr.dictfetchall():
          balance = 0
          for line in move_lines.get(row['account_id']):
              balance += line['debit'] - line['credit']
          row['balance'] += balance
          move_lines[row.pop('account_id')].append(row)

      # Calculate the debit, credit and balance for Accounts
      account_res = []
      for account in accounts:
          currency = account.currency_id and account.currency_id or account.company_id.currency_id
          res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
          res['code'] = account.code
          res['name'] = account.name
          res['move_lines'] = move_lines[account.id]
          for line in res.get('move_lines'):
              res['debit'] += line['debit']
              res['credit'] += line['credit']
              res['balance'] = line['balance']
          if display_account == 'all':
              account_res.append(res)
          if display_account == 'movement' and res.get('move_lines'):
              account_res.append(res)
          if display_account == 'not_zero' and not currency.is_zero(
                  res['balance']):
              account_res.append(res)

      return account_res

