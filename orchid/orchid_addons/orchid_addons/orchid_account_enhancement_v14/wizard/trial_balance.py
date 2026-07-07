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

from odoo import fields, models,_
import xlsxwriter
from io import BytesIO
import base64
from collections import defaultdict
from datetime import datetime
import time
from odoo.exceptions import UserError


class AccountBalanceReport(models.TransientModel):
    _inherit = "account.common.account.report"
    _name = 'account.balance.report'
    _description = 'Trial Balance Report'

    journal_ids = fields.Many2many('account.journal',
                                   'account_balance_report_journal_rel',
                                   'account_id', 'journal_id',
                                   string='Journals', required=True,
                                   default=[])
    excel_file = fields.Binary(string='Dowload Report Excel',readonly="1")
    file_name = fields.Char(string='Excel File',readonly="1")
    date_from = fields.Date(string='Start Date',required=True,default=time.strftime('%Y-01-01'))
    date_to = fields.Date(string='End Date',required=True,default=datetime.today())
    detail = fields.Boolean(string="Detail", default=False)
    groupby = fields.Boolean(string="With Grouping", default=False)
    # od_initial_bal = fields.Boolean(string="Include Initial Balance", default=False)

    def _print_report(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'detail': self.detail,'groupby':self.groupby})
        records = self.env[data['model']].browse(data.get('ids', []))
        # print("dataaaaaaaaa",data)
        data['form'].get('used_context').update({'landscape':True})
        context = dict(data['form'].get('used_context'))
        return self.env.ref(
            'orchid_account_enhancement_v14.action_report_trial_balance').with_context(context).report_action(
            records, data=data)

    #************************EXCEL**************#
    def od_generate_excel_report(self):
      data = {}
      data['form']={}
      data['form'].update(self.read(['display_account','date_to','date_from','target_move'])[0]) 
      # data['form'].update(self.read(['orchid_cc_id'])[0])
      date_from =  data['form']['date_from']
      date_to =  data['form']['date_to']
      display_account = data['form']['display_account']
      # cost_center = data['form']['orchid_cc_id']
      # od_with_closing = self.od_with_closing
      # cost_center_name = False
      # if cost_center:
      #   cost_center_name = cost_center[1]
      #   cost_center = cost_center[0]
        
    
      target_move=data['form']['target_move']
     
      if (date_from and date_to) and (date_from > date_to):
        raise UserError(_('Start date cannot be greater than End date!!'))
      # ctx = self.env.context
      # self.model = self.env.context.get('active_model')
      model = self.env.context.get('active_model')
      # accounts = self.env['account.account'].browse(ctx.get('active_id')) if self.model == 'account.account' else self.env['account.account'].search([])
      accounts = self.env['account.account'].browse(ctx.get('active_id')) if model == 'account.account' else self.env['account.account'].search([('company_id','=',self.env.company.id)])
      # account_data =self.get_account_data(date_from,date_to,accounts,display_account,cost_center,target_move,od_with_closing)
      account_data =self.get_account_data(str(date_from),str(date_to),accounts,display_account,target_move)
      
      # company = self.env['res.company'].browse(self.env.user.company_id.id)
      company = self.env['res.company'].browse(self.env.company.id)
      header =['Debit','Credit','Balance']
      address=defaultdict(list)
      if company.street:
        address['first'].append(company.street)
      if company.street2:
        address['first'].append(company.street2)
      if company.city:
        address['first'].append(company.city)
      address['first']=', '.join(address['first'])
      if company.state_id:
        address['second'].append(company.state_id.name)
      if company.zip:
        address['second'].append(company.zip)
      address['second']=', '.join(address['second'])
      if company.country_id:
        address['third'].append(company.country_id.name)

      
      # workbook= xlwt.Workbook(encoding="UTF-8")
      output = BytesIO()
      workbook = xlsxwriter.Workbook(output)
      # xlwt.add_palette_colour("custom_colour", 0x10)
      # workbook.set_colour_RGB(0x10,208, 211, 212)
      # xlwt.add_palette_colour("custom", 0x11)
      # workbook.set_colour_RGB(0x11,236, 239, 239)
      # sheet= workbook.add_sheet('Trial Balance Report',cell_overwrite_ok=True)
      sheet= workbook.add_worksheet('Trial Balance Report')

      # style1 = xlwt.easyxf('font:height 200, bold True, name Arial; align: horiz center, vert center;')
      style1 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'center','valign':'vcenter'})

      # style = xlwt.easyxf('font:height 200, bold True, name Arial; align: horiz center, vert center;pattern: fore_colour custom_colour,pattern solid;')
      style = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'center','valign':'vcenter','bg_color':'#D4D3D0'})
      
      # style2 = xlwt.easyxf('font:height 200, bold True, name Arial; align: horiz center, vert center;borders: top medium,bottom medium')
      style2 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'center','valign':'vcenter','top':1,'bottom':1})
      
      # style3 = xlwt.easyxf('font:height 200, name Arial; align: horiz right, vert center;')
      # style3.num_format_str = "0.00"
      style3 = workbook.add_format({'font_size':8,'font_name':'Arial','align':'right','valign':'vcenter','num_format':'#,##0.00'})

      # style4 = xlwt.easyxf('font:height 200, name Arial; align: horiz left, vert center;')
      style4 = workbook.add_format({'font_size':8,'font_name':'Arial','align':'left','valign':'vcenter'})

      # style6 = xlwt.easyxf('font:height 200, name Arial; align: horiz left, vert center;pattern: fore_colour custom_colour,pattern solid;')
      style6 = workbook.add_format({'font_size':8,'font_name':'Arial','align':'left','valign':'vcenter','bg_color':'#F0F0F0'})
      
      # style5 = xlwt.easyxf('font:height 200, bold True, name Arial; align: horiz center, vert center;')
      # style5.num_format_str = "0.00"
      style5 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'center','valign':'vcenter','num_format':'#,##0.00'})

      # style7 = xlwt.easyxf('font:height 200, name Arial; align: horiz right, vert center;pattern: fore_colour custom_colour,pattern solid;')
      # style7.num_format_str = "0.00"
      style7 = workbook.add_format({'font_size':8,'font_name':'Arial','align':'right','valign':'vcenter','num_format':'#,##0.00','bg_color':'#F0F0F0'})

      # style8 = xlwt.easyxf('font:height 280, bold True, name Arial; align: horiz center, vert center;')
      style8 = workbook.add_format({'font_size':10,'bold':True,'font_name':'Arial','align':'center','valign':'vcenter'})

      # style9 = xlwt.easyxf('font:height 200, bold True, name Arial; align: horiz center, vert center;pattern: fore_colour custom,pattern solid;')
      style9 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'center','valign':'vcenter','bg_color':'#D4D3D0'})
      
      # style10 = xlwt.easyxf('font:height 200, bold True, name Arial; align: horiz right, vert center;pattern: fore_colour custom,pattern solid;')
      # style10.num_format_str = "0.00"
      style10 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'right','valign':'vcenter','bg_color':'#D4D3D0','num_format':'#,##0.00'})
      
      style11 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'left','valign':'vcenter','bg_color':'#A8A8A8'})
      style12 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'left','valign':'vcenter','bg_color':'#D4D3D0'})
      style13 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'right','valign':'vcenter','bg_color':'#A8A8A8','num_format':'#,##0.00'})
      style14 = workbook.add_format({'font_size':8,'bold':True,'font_name':'Arial','align':'right','valign':'vcenter','bg_color':'#D4D3D0','num_format':'#,##0.00'})

      # sheet.col(0).width = 256*10
      # sheet.col(1).width = 256*50
      sheet.set_column('A:A',5)
      sheet.set_column('B:B',45)
      print_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      # fdate = datetime.strptime(date_from, '%Y-%m-%d').strftime('%d/%m/%Y')
      # tdate = datetime.strptime(date_to, '%Y-%m-%d').strftime('%d/%m/%Y')
      fdate = datetime.strptime(str(date_from), '%Y-%m-%d').strftime('%d/%m/%Y')
      tdate = datetime.strptime(str(date_to), '%Y-%m-%d').strftime('%d/%m/%Y')
      Printed_by = False
      user_obj = self.env['res.users'].search([])
      for user_login in user_obj:
        current_login= self.env.user
        if user_login == current_login:
          Printed_by = current_login.name
      row=0
      col=0
      row_merge=row
      col=0
      col_merge=col+10
      # sheet.write_merge(row,row_merge,col,col_merge,"Trial Balance",style8)
      sheet.merge_range(row,col,row,col_merge,"Trial Balance",style8)

      row=2
      col=7
      sheet.write(row,col,"Printed On",style4)
      row=row+1
      sheet.write(row,col,"Printed By ",style4)
      # row=row+1
      # sheet.write(row,col,"Cost Center",style4)
      row=row+1
      sheet.write(row,col,"Date From",style4)
      col = col +2
      sheet.write(row,col,"Date To",style4)
      row=2
      col=8
      sheet.write(row,col,print_date_time,style4)
      row=row+1
      sheet.write(row,col,Printed_by,style4)
      # if cost_center:
      #   row=row+1
      #   sheet.write(row,col,cost_center_name,style4)
      # else:
      #   row=row+1
      #   sheet.write(row,col,"All",style4)
      # row=row+1
      # sheet.write(row,col,"All",style4)
      row=row+1
      sheet.write(row,col,fdate,style4)
      col = col +2
      sheet.write(row,col,tdate,style4)
      row = 2
      col = 0
      sheet.write(row,col,company.name,style4)
      if address['first']:
        row=row+1
        # sheet.write(row,col,address['first'],style4)
        sheet.write(row,col,''.join(address['first']),style4)
      if address['second']:
        row=row+1
        # sheet.write(row,col,address['second'],style4)
        sheet.write(row,col,''.join(address['second']),style4)
      if address['third']:
        row=row+1
        # sheet.write(row,col,address['third'],style4)
        sheet.write(row,col,''.join(address['third']),style4)
      sub_len=0
      row=row+1
      col=0
      col_merge=1
      row_merge=row
      if date_from:
        sheet.write(row,col,' ',style)
        col=col+1
        sheet.write(row,col,' ',style)
        col=col+1
        col_merge=col+2
        # sheet.write_merge(row,row_merge,col,col_merge,"Opening",style)
        sheet.merge_range(row,col,row,col_merge,"Opening",style)
        sub_len=sub_len+1
      if date_from and date_to:
        col=col_merge+1
        col_merge=col+2
        # sheet.write_merge(row,row_merge,col,col_merge,"Current",style)
        sheet.merge_range(row,col,row,col_merge,"Current",style)
        sub_len=sub_len+1
      if date_to:
        col=col_merge+1
        col_merge=col+2
        # sheet.write_merge(row,row_merge,col,col_merge,"Closing",style)
        sheet.merge_range(row,col,row,col_merge,"Closing",style)
        sub_len=sub_len+1
      row=row+1
      col=0
      sheet.write(row,col,"Code",style2)
      col=col+1
      sheet.write(row,col,"Account",style2)
      for i in range(0,sub_len):
        col=col+1
        # sheet.col(col).width = 256*16
        sheet.write(row,col,header[0],style2)
        col=col+1
        # sheet.col(col).width = 256*16
        sheet.write(row,col,header[1],style2)
        col=col+1
        # sheet.col(col).width = 256*16
        sheet.write(row,col,header[2],style2)

      temp_col=0
      ototal_debit=0
      ototal_credit=0
      ototal_balance=0
      ctotal_debit=0
      ctotal_credit=0
      ctotal_balance=0
      cltotal_debit=0
      cltotal_credit=0
      cltotal_balance=0

      if self.groupby:
        for group in self.env['od.report.template'].search([('report_value','=','tb'),('company_id','=',self.company_id.id)], order='sequence asc'):
          group_accounts = []
          if group.display_details=='compute':
            for subgroup in group.account_group_ids:
              for acc in subgroup.name.account_account_ids:
                group_accounts.append(acc.name.id)
            account_ids = self.env['account.account'].browse(group_accounts)
            group_data =self.get_group_sum(str(date_from),str(date_to),account_ids,display_account,target_move)
            for data in group_data:
              row=row+1
              name = group.name
              print(group,group.name,"groupssssssssssssssssssssss")
              col=0
              sheet.merge_range(row,col,row,1,name,style11)
              col=col+1
              if date_from:
                col=col+1
                debit=data['opening']['debit']
                credit=data['opening']['credit']
                balance=data['opening']['balance']
                sheet.write(row,col,debit,style13)
                col=col+1
                sheet.write(row,col,credit,style13)
                col=col+1
                sheet.write(row,col,balance,style13)
              if date_from and date_to:
                col=col+1
                debit=data['current']['debit']
                credit=data['current']['credit']
                balance=data['current']['balance']
                sheet.write(row,col,debit,style13)
                col=col+1
                sheet.write(row,col,credit,style13)
                col=col+1
                sheet.write(row,col,balance,style13)
              if date_to:
                col=col+1
                debit=data['closing']['debit']
                credit=data['closing']['credit']
                balance=data['closing']['balance']
                sheet.write(row,col,debit,style13)
                col=col+1
                sheet.write(row,col,credit,style13)
                col=col+1
                sheet.write(row,col,balance,style13)
          if group.display_details=='accounts':
            for acc in group.account_account_ids:
              group_accounts.append(acc.name.id)
              account_ids = self.env['account.account'].browse(group_accounts)
            group_data =self.get_group_sum(str(date_from),str(date_to),account_ids,display_account,target_move)
            for data in group_data:
              row=row+1
              name = group.name
              print(group,group.name,"accountsss groupsssss")
              if group.id==16:
                print(group_data)
                # print(s)
              col=0
              sheet.merge_range(row,col,row,1,name,style12)
              col=col+1
              if date_from:
                col=col+1
                debit=data['opening']['debit']
                credit=data['opening']['credit']
                balance=data['opening']['balance']
                sheet.write(row,col,debit,style14)
                col=col+1
                sheet.write(row,col,credit,style14)
                col=col+1
                sheet.write(row,col,balance,style14)
              if date_from and date_to:
                col=col+1
                debit=data['current']['debit']
                credit=data['current']['credit']
                balance=data['current']['balance']
                sheet.write(row,col,debit,style14)
                col=col+1
                sheet.write(row,col,credit,style14)
                col=col+1
                sheet.write(row,col,balance,style14)
              if date_to:
                col=col+1
                debit=data['closing']['debit']
                credit=data['closing']['credit']
                balance=data['closing']['balance']
                sheet.write(row,col,debit,style14)
                col=col+1
                sheet.write(row,col,credit,style14)
                col=col+1
                sheet.write(row,col,balance,style14)
          
            account_data =self.get_account_data(str(date_from),str(date_to),account_ids,display_account,target_move)
            for data in account_data:
              row=row+1
              code=data.get('code')
              name = data.get('name')
              credit = data.get('credit')
              debit = data.get('debit')
              balance = data.get('balance')
              col=temp_col
              sheet.write(row,col,code,style6)
              col=col+1
              sheet.write(row,col,name,style4)
              if date_from:
                if data.get('opening')==False:
                  col=col+1
                  open_debit=0
                  open_credit=0
                  open_balance=open_debit-open_credit
                  sheet.write(row,col,open_debit,style3)
                  col=col+1
                  sheet.write(row,col,open_credit,style3)
                  col=col+1
                  sheet.write(row,col,open_balance,style3)
                  ototal_debit=ototal_debit+open_debit
                  ototal_credit=ototal_credit+open_credit
                  ototal_balance=ototal_balance+open_balance
                else:
                  line_open = data.get('opening')
                  col=col+1
                  # if line_open.get('initial_balnce') is not True:
                  #   open_debit=0
                  #   open_credit=0
                  # else:
                  #   open_debit=line_open.get('debit',0)
                  #   open_credit=line_open.get('credit',0)
                  open_debit=line_open.get('debit',0)
                  open_credit=line_open.get('credit',0)
                  open_balance=open_debit-open_credit
                  sheet.write(row,col,open_debit,style3)
                  col=col+1
                  sheet.write(row,col,open_credit,style3)
                  col=col+1
                  sheet.write(row,col,open_balance,style3)
                  ototal_debit=ototal_debit+open_debit
                  ototal_credit=ototal_credit+open_credit
                  ototal_balance=ototal_balance+open_balance
              if date_from and date_to:
                if data.get('current')==False:
                  col=col+1
                  current_debit=0
                  current_credit=0
                  current_balance=current_debit-current_credit
                  sheet.write(row,col,current_debit,style7)
                  col=col+1
                  sheet.write(row,col,current_credit,style7)
                  col=col+1
                  sheet.write(row,col,current_balance,style7)
                  ctotal_debit=ctotal_debit+current_debit
                  ctotal_credit=ctotal_credit+current_credit
                  ctotal_balance=ctotal_balance+current_balance
                else:
                  line_current=data.get('current')
                  col=col+1
                  current_debit=line_current.get('debit',0)
                  current_credit=line_current.get('credit',0)
                  current_balance=current_debit-current_credit
                  sheet.write(row,col,current_debit,style7)
                  col=col+1
                  sheet.write(row,col,current_credit,style7)
                  col=col+1
                  sheet.write(row,col,current_balance,style7)
                  ctotal_debit=ctotal_debit+current_debit
                  ctotal_credit=ctotal_credit+current_credit
                  ctotal_balance=ctotal_balance+current_balance
                  
              if date_to:
                if data.get('closing')==False:
                  col=col+1
                  close_debit=0
                  close_credit=0
                  close_balance=close_debit-close_credit
                  sheet.write(row,col,close_debit,style3)
                  col=col+1
                  sheet.write(row,col,close_credit,style3)
                  col=col+1
                  sheet.write(row,col,close_balance,style3)
                  cltotal_debit=cltotal_debit+close_debit
                  cltotal_credit=cltotal_credit+close_credit
                  cltotal_balance=cltotal_balance+close_balance
                else:
                  line_closing=data.get('closing')
                  col=col+1
                  # if line_closing.get('initial_balnce') is not True:
                  #   close_debit=current_debit
                  #   close_credit=current_credit
                  # else:
                  #   close_debit=line_closing.get('debit',0)
                  #   close_credit=line_closing.get('credit',0)
                  close_debit=line_closing.get('debit',0)
                  close_credit=line_closing.get('credit',0)
                  close_balance=close_debit-close_credit
                  sheet.write(row,col,close_debit,style3)
                  col=col+1
                  sheet.write(row,col,close_credit,style3)
                  col=col+1
                  sheet.write(row,col,close_balance,style3)
                  cltotal_debit=cltotal_debit+close_debit
                  cltotal_credit=cltotal_credit+close_credit
                  cltotal_balance=cltotal_balance+close_balance
      else:
        for data in account_data:
          row=row+1
          code=data.get('code')
          name = data.get('name')
          # if self.od_currency:
          #   data['credit'] = data['credit'] * self.od_rate
          #   data['debit'] = data['debit'] * self.od_rate
          #   data['balance'] = data['balance'] * self.od_rate
          credit = data.get('credit')
          debit = data.get('debit')
          balance = data.get('balance')
          col=temp_col
          sheet.write(row,col,code,style6)
          col=col+1
          sheet.write(row,col,name,style4)
          if date_from:
            if data.get('opening')==False:
              col=col+1
              open_debit=0
              open_credit=0
              open_balance=open_debit-open_credit
              sheet.write(row,col,open_debit,style3)
              col=col+1
              sheet.write(row,col,open_credit,style3)
              col=col+1
              sheet.write(row,col,open_balance,style3)
              ototal_debit=ototal_debit+open_debit
              ototal_credit=ototal_credit+open_credit
              ototal_balance=ototal_balance+open_balance
            else:
              line_open = data.get('opening')
              col=col+1
              # if line_open.get('initial_balnce') is not True:
              #   open_debit=0
              #   open_credit=0
              # else:
              #   # if self.od_currency:
              #   #   line_open['credit'] = line_open['credit'] * self.od_rate
              #   #   line_open['debit'] = line_open['debit'] * self.od_rate
              #   open_debit=line_open.get('debit',0)
              #   open_credit=line_open.get('credit',0)
              open_debit=line_open.get('debit',0)
              open_credit=line_open.get('credit',0)
              open_balance=open_debit-open_credit
              sheet.write(row,col,open_debit,style3)
              col=col+1
              sheet.write(row,col,open_credit,style3)
              col=col+1
              sheet.write(row,col,open_balance,style3)
              ototal_debit=ototal_debit+open_debit
              ototal_credit=ototal_credit+open_credit
              ototal_balance=ototal_balance+open_balance
          if date_from and date_to:
            if data.get('current')==False:
              col=col+1
              current_debit=0
              current_credit=0
              current_balance=current_debit-current_credit
              sheet.write(row,col,current_debit,style7)
              col=col+1
              sheet.write(row,col,current_credit,style7)
              col=col+1
              sheet.write(row,col,current_balance,style7)
              ctotal_debit=ctotal_debit+current_debit
              ctotal_credit=ctotal_credit+current_credit
              ctotal_balance=ctotal_balance+current_balance
            else:
              line_current=data.get('current')
              col=col+1
              # if self.od_currency:
              #     line_current['credit'] = line_current['credit'] * self.od_rate
              #     line_current['debit'] = line_current['debit'] * self.od_rate
              current_debit=line_current.get('debit',0)
              current_credit=line_current.get('credit',0)
              current_balance=current_debit-current_credit
              sheet.write(row,col,current_debit,style7)
              col=col+1
              sheet.write(row,col,current_credit,style7)
              col=col+1
              sheet.write(row,col,current_balance,style7)
              ctotal_debit=ctotal_debit+current_debit
              ctotal_credit=ctotal_credit+current_credit
              ctotal_balance=ctotal_balance+current_balance
              
          if date_to:
            if data.get('closing')==False:
              col=col+1
              close_debit=0
              close_credit=0
              close_balance=close_debit-close_credit
              sheet.write(row,col,close_debit,style3)
              col=col+1
              sheet.write(row,col,close_credit,style3)
              col=col+1
              sheet.write(row,col,close_balance,style3)
              cltotal_debit=cltotal_debit+close_debit
              cltotal_credit=cltotal_credit+close_credit
              cltotal_balance=cltotal_balance+close_balance
            else:
              line_closing=data.get('closing')
              col=col+1
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
              sheet.write(row,col,close_debit,style3)
              col=col+1
              sheet.write(row,col,close_credit,style3)
              col=col+1
              sheet.write(row,col,close_balance,style3)
              cltotal_debit=cltotal_debit+close_debit
              cltotal_credit=cltotal_credit+close_credit
              cltotal_balance=cltotal_balance+close_balance
        


        row=row+1
        row_merge=row
        col=0
        col_merge=col+1
        # sheet.write_merge(row,row_merge,col,col_merge,"Total",style9)
        sheet.merge_range(row,col,row,col_merge,"Total",style9)
        if date_from:
          col=col+2
          sheet.write(row,col,ototal_debit,style10)
          col=col+1
          sheet.write(row,col,ototal_credit,style10)
          col=col+1
          sheet.write(row,col,ototal_balance,style10)
        if date_from and date_to:
          col=col+1
          sheet.write(row,col,ctotal_debit,style10)
          col=col+1
          sheet.write(row,col,ctotal_credit,style10)
          col=col+1
          sheet.write(row,col,ctotal_balance,style10)
        if date_to:
          col=col+1
          sheet.write(row,col,cltotal_debit,style10)
          col=col+1
          sheet.write(row,col,cltotal_credit,style10)
          col=col+1
          sheet.write(row,col,cltotal_balance,style10)


      filename= 'TrialBalanceReport.xlsx'
      # fp = BytesIO()
      # workbook.save(fp)
      # excel_file = base64.encodestring(fp.getvalue())
      # self.excel_file = excel_file
      # self.file_name =filename
      # fp.close()
      workbook.close()
      output.seek(0)
      excel_file = base64.encodestring(output.read())
      self.excel_file = excel_file
      self.file_name =filename

      ir_model_data = self.env['ir.model.data']
      # compose_form_id = ir_model_data.get_object_reference('account', 'account_report_balance_view')[1]
      compose_form_id = ir_model_data.get_object_reference('orchid_account_enhancement_v14', 'account_report_balance_view')[1]


      return {            
        'type': 'ir.actions.act_window',            
        'view_type': 'form',            
        'view_mode': 'form',            
        'res_model': 'account.balance.report',            
        'views': [(compose_form_id, 'form')], 
        'res_id': self.id,           
        'view_id': compose_form_id,            
        'target': 'new',            
        }

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
      # print("gettttttttttttttttttttttttttttttttttt",l)
      cr=self._cr
      opening_result={}
      current_result={}
      closing_result={}
      # print("hereeeee",(tuple(accounts.ids)))

      if len(accounts.ids)==1:
        where_qry ="WHERE al.account_id = "+str(accounts.id)
      else:
        where_qry ="WHERE al.account_id IN "+str(tuple(accounts.ids))
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
        print('kkkkkkkkk',sql_query)
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
        print(sql_query)
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
          print("llllllffff",opening_result)
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

