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
import re

from odoo import api, models, fields, _
import xlsxwriter
from io import BytesIO
import base64
from datetime import datetime
from odoo.exceptions import UserError


class FinancialReport(models.TransientModel):
    _name = "financial.report"
    _inherit = "account.common.report"
    _description = "Financial Reports"

    view_format = fields.Selection([
        ('vertical', 'Vertical'),
        ('horizontal', 'Horizontal')],
        default='vertical',
        string="Format")

    @api.model
    def _get_account_report(self):
        reports = []
        if self._context.get('active_id'):
            menu = self.env['ir.ui.menu'].browse(
                self._context.get('active_id')).name
            reports = self.env['account.financial.report'].search([
                ('name', 'ilike', menu)])
        return reports and reports[0] or False

    enable_filter = fields.Boolean(
        string='Enable Comparison',
        default=False)
    account_report_id = fields.Many2one(
        'account.financial.report',
        string='Account Reports',
        required=True)

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    debit_credit = fields.Boolean(
        string='Display Debit/Credit Columns',
        default=True,
        help="This option allows you to"
             " get more details about the "
             "way your balances are computed."
             " Because it is space consuming,"
             " we do not allow to use it "
             "while doing a comparison.")
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        index=True,
        default=lambda self: self.env.company.id)
    od_groupby = fields.Boolean(string="With Grouping", default=False)
    od_report_value = fields.Selection([('pl','Profit & Loss'),('tb','Trial Balance'),('bl','Balance Sheet')], string="Report", required=True,default='tb')
    excel_file = fields.Binary(string='Dowload Report Excel',readonly="1")
    file_name = fields.Char(string='Excel File',readonly="1")

    @api.model
    def default_get(self,fields):
        res = super(FinancialReport, self).default_get(fields)
        if self._context.get('default_account_report_id'):
            if self._context.get('default_account_report_id') == self.env.ref('orchid_account_enhancement_v14.account_financial_report_profitandloss0').id:
                res['od_report_value']='pl'
            if self._context.get('default_account_report_id') == self.env.ref('orchid_account_enhancement_v14.account_financial_report_balancesheet0').id:
                res['od_report_value']='bl'

        return res

    def od_view_report_xl_groupby(self):
        self.ensure_one()
        report_template = self.env['od.report.template'].search([('report_value','=',self.od_report_value),('company_id','=',self.company_id.id)])
        if not report_template:
            raise UserError(_("No Template set for this report!!!"))
        data = dict()
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(
            ['date_from', 'enable_filter', 'debit_credit', 'date_to',
             'account_report_id', 'target_move', 'view_format',
             'company_id','od_groupby','od_report_value'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(
            used_context,
            lang=self.env.context.get('lang') or 'en_US')
        context = dict(data['form'].get('used_context'))
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet_name = self.account_report_id and self.account_report_id.name
        sheet= workbook.add_worksheet(sheet_name)
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'fg_color': '#D7E4BC',
            'border': 0,
            'font_size':14}) 
        header_style = workbook.add_format({
            'bold': True,
            'align': 'center',
            'fg_color':'#b2b2b2',
            'border':0})
        sub_header_style = workbook.add_format({
            'bold': True,
            'border':0})
        tot_format = workbook.add_format({
            'bold': True,
            'align': 'left',
            'border': 0})
        tot_format1 = workbook.add_format({
            'bold': True,
            'align': 'right',
            'num_format': '#,##0.00',
            'border': 0})
        row_num_style = workbook.add_format({'num_format': '#,##0.00'}) 

        row=0
        col=0
        row_merge=row
        col=0
        col_merge=col+3
        sheet.merge_range(row,col,row,col_merge,sheet_name,title_format)
        row = row+2
        sheet.write(row,col,self.company_id.name,sub_header_style)
        row+=1
        sheet.write(row,col,"Target Moves")
        col = col+1
        target_move = "All Entries"
        if self.target_move=='posted':
            target_move="All Posted Entries"
        sheet.write(row,col,target_move)
        col = 0
        if self.date_from:
            fdate = datetime.strptime(str(self.date_from), '%Y-%m-%d').strftime('%d/%m/%Y')
            row=row+1
            sheet.write(row,col,"Date from")
            col = col+1
            sheet.write(row,col,fdate)
        if self.date_to:
            tdate = datetime.strptime(str(self.date_to), '%Y-%m-%d').strftime('%d/%m/%Y')
            col=0
            row=row+1
            sheet.write(row,col,"Date to")
            col = col+1
            sheet.write(row,col,tdate)
        headers = ['Name','Balance']
        if self.debit_credit:
            headers = ['Name','Debit','Credit','Balance']
        col = 0
        row=row+2
        for head in headers:
            sheet.write(row,col,head,header_style)
            col+=1
        sheet.set_column('A:A',27)
        sheet.set_column('B:B',15)
        sheet.set_column('C:C',15)
        sheet.set_column('D:D',15)
        # not on sign
        # if display type accounts;
        ##### accountbalance=balance*group.sign--only when write no change in qry
        #####groupbalance=if preserve sign take absolute else balance*group.sign when write
        for group in self.env['od.report.template'].search([('report_value','=',self.od_report_value),('company_id','=',self.company_id.id)], order='sequence asc'):
            group_accounts = []
            if group.display_details=='compute':
                for subgroup in group.account_group_ids:
                  for acc in subgroup.name.account_account_ids:
                    group_accounts.append(acc.name.id)
                account_ids = self.env['account.account'].browse(group_accounts)
                group_data =self.with_context(context)._od_compute_account_group_balance(account_ids,group)
                row = row+2
                col=0
                sheet.write(row,col,group.name,sub_header_style)
                if self.debit_credit:
                    col=col+1
                    sheet.write(row,col,group_data['debit'],tot_format1)
                    col=col+1
                    sheet.write(row,col,group_data['credit'],tot_format1)
                col=col+1
                sheet.write(row,col,group_data['balance'],tot_format1)
                # row=row+1
            if group.display_details=='report_value':
                group_accounts = []
                for subgroup in group.report_template_id.account_group_ids:
                  for acc in subgroup.name.account_account_ids:
                    group_accounts.append(acc.name.id)
                account_ids = self.env['account.account'].browse(group_accounts)
                group_data =self.with_context(context)._od_compute_account_group_balance(account_ids,group.report_template_id)
                row = row+2
                col=0
                sheet.write(row,col,group.name,sub_header_style)
                if self.debit_credit:
                    col=col+1
                    sheet.write(row,col,group_data['debit'],tot_format1)
                    col=col+1
                    sheet.write(row,col,group_data['credit'],tot_format1)
                col=col+1
                sheet.write(row,col,group_data['balance'],tot_format1)

            if group.display_details=='accounts':
                for acc in group.account_account_ids:
                  group_accounts.append(acc.name.id)
                  account_ids = self.env['account.account'].browse(group_accounts)
                group_data =self.with_context(context)._od_compute_account_group_balance(account_ids,group)
                # print("groupppppp",group_data)
                row = row+2
                col=0
                sheet.write(row,col,group.name,sub_header_style)
                if self.debit_credit:
                    col=col+1
                    sheet.write(row,col,group_data['debit'],tot_format1)
                    col=col+1
                    sheet.write(row,col,group_data['credit'],tot_format1)
                col=col+1
                balance = group_data['balance']
                if int(group.sign)>0:
                    if self.od_report_value=='pl':
                        balance = abs(balance)
                    else:
                        balance = balance
                else:
                    balance = group_data['balance']*int(group.sign)
                sheet.write(row,col,balance,tot_format1)
                account_data =self.with_context(context)._compute_account_balance(account_ids)
                for a_data in account_data:
                    row = row+1
                    account_id = self.env['account.account'].browse(a_data['id'])
                    col=0
                    sheet.write(row,col,account_id.display_name)
                    if self.debit_credit:
                        col=col+1
                        debit = a_data['debit']
                        sheet.write(row,col,debit,row_num_style)
                        col=col+1
                        credit = a_data['credit']
                        sheet.write(row,col,credit,row_num_style)
                    col=col+1
                    balance = a_data['balance']*int(group.sign)
                    sheet.write(row,col,balance,row_num_style)

        filename= sheet_name+'.xlsx'
        workbook.close()
        output.seek(0)
        excel_file = base64.encodestring(output.read())
        self.excel_file = excel_file
        self.file_name =filename

        return {            
        'type': 'ir.actions.act_window',            
        'view_type': 'form',            
        'view_mode': 'form',            
        'res_model': 'financial.report',            
        'res_id': self.id,           
        'target': 'new',            
        }

    def view_report_pdf(self):
        """This function will be executed when we click the view button
        from the wizard. Based on the values provided in the wizard, this
        function will print pdf report"""
        self.ensure_one()
        if self.od_groupby:
            raise UserError(_("PDF Report to be implemented!!"))
        data = dict()
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        
        data['form'] = self.read(
            ['date_from', 'enable_filter', 'debit_credit', 'date_to',
             'account_report_id', 'target_move', 'view_format',
             'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(
            used_context,
            lang=self.env.context.get('lang') or 'en_US')
        report_lines = self.get_account_lines(data['form'])
        # find the journal items of these accounts
        journal_items = self.find_journal_items(report_lines, data['form'])

        def set_report_level(rec):
            """This function is used to set the level of each item.
            This level will be used to set the alignment in the dynamic reports."""
            level = 1
            if not rec['parent']:
                return level
            else:
                for line in report_lines:
                    key = 'a_id' if line['type'] == 'account' else 'id'
                    if line[key] == rec['parent']:
                        return level + set_report_level(line)

        # finding the root
        for item in report_lines:
            item['balance'] = round(item['balance'], 2)
            if not item['parent']:
                item['level'] = 1
                parent = item
                report_name = item['name']
                id = item['id']
                report_id = item['r_id']
            else:
                item['level'] = set_report_level(item)
        currency = self._get_currency()
        data['currency'] = currency
        data['journal_items'] = journal_items
        data['report_lines'] = report_lines
        # checking view type
        return self.env.ref(
            'orchid_account_enhancement_v14.financial_report_pdf').report_action(self,
                                                                      data)

    def _compute_account_balance(self, accounts):
        """ compute the balance, debit
        and credit for the provided accounts
        """
        print("ssssss",self._context)
        mapping = {
            'balance':
                "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0)"
                " as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        res_ls = []
        for account in accounts:
            res[account.id] = dict((fn, 0.0)
                                   for fn in mapping.keys())
        if accounts:
            tables, where_clause, where_params = (
                self.env['account.move.line']._query_get())
            tables = tables.replace(
                '"', '') if tables else "account_move_line"
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            request = ("SELECT account_id as id, " +
                       ', '.join(mapping.values()) +
                       " FROM " + tables +
                       " WHERE account_id IN %s " +
                       filters +
                       " GROUP BY account_id")
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            print("trfffffffff",request)
            print("ppppp",params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row
                res_ls.append(row)
        if self.od_groupby:
            return res_ls
        else:
            return res

    # def _od_compute_account_report_balance(self, accounts,group):
    def _od_compute_account_group_balance(self, accounts,group):
        """ compute the balance, debit
        and credit for the provided accounts
        """
        mapping = {
            'balance':
                "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0)"
                " as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        # for account in accounts:
        #     res[account.id] = dict((fn, 0.0)
        #                            for fn in mapping.keys())
        if accounts:
            print("ghsdsss",group.name)
            if group.display_details=='accounts':
                tables, where_clause, where_params = (
                    self.env['account.move.line']._query_get())
                tables = tables.replace(
                    '"', '') if tables else "account_move_line"
                wheres = [""]
                if where_clause.strip():
                    wheres.append(where_clause.strip())
                filters = " AND ".join(wheres)
                request = ("SELECT " +
                           ', '.join(mapping.values()) +
                           " FROM " + tables +
                           " WHERE account_id IN %s " +
                           filters)
                params = (tuple(accounts._ids),) + tuple(where_params)
                self.env.cr.execute(request, params)
                for row in self.env.cr.dictfetchall():
                    res = row
                return res
            if group.display_details=='compute':
                print("hereeeee????????")
                total_debit=total_credit=total_balance=0
                for subgroup in group.account_group_ids:
                    # print("kkffff",subgroup)
                    group_accounts=[]
                    for acc in subgroup.name.account_account_ids:
                        group_accounts.append(acc.name.id)
                    account_ids = self.env['account.account'].browse(group_accounts)
                    tables, where_clause, where_params = (
                        self.env['account.move.line']._query_get())
                    tables = tables.replace(
                        '"', '') if tables else "account_move_line"
                    wheres = [""]
                    if where_clause.strip():
                        wheres.append(where_clause.strip())
                    filters = " AND ".join(wheres)
                    request = ("SELECT " +
                               ', '.join(mapping.values()) +
                               " FROM " + tables +
                               " WHERE account_id IN %s " +
                               filters)
                    params = (tuple(account_ids._ids),) + tuple(where_params)
                    self.env.cr.execute(request, params)
                    for row in self.env.cr.dictfetchall():
                        debit = row['debit']
                        credit = row['credit']
                        balance = row['balance']
                        if int(subgroup.name.sign)>0:
                            if (self.od_report_value=='pl') or (group.report_value=='pl'):
                                debit = abs(debit)
                                credit = abs(credit)
                                balance = abs(balance)
                            else:
                                debit = debit
                                credit = credit
                                balance = balance
                        else:
                            debit = row['debit']*int(subgroup.name.sign)
                            credit = row['credit']*int(subgroup.name.sign)
                            balance = row['balance']*int(subgroup.name.sign)
                        total_debit+=debit
                        total_credit+=credit
                        total_balance+=balance
                    res['debit']=total_debit
                    res['credit']=total_credit
                    res['balance']=total_balance
                return res
        return res

    def _compute_report_balance(self, reports):
        """returns a dictionary with key=the ID of a record and
         value=the credit, debit and balance amount
        computed for this record. If the record is of type :
        'accounts' : it's the sum of the linked accounts
        'account_type' : it's the sum of leaf accounts with
         such an account_type
        'account_report' : it's the amount of the related report
        'sum' : it's the sum of the children of this record
         (aka a 'view' record)"""
        res = {}
        fields = ['credit', 'debit', 'balance']
        for report in reports:
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields)
            if report.type == 'accounts':
                # it's the sum of the linked accounts
                res[report.id]['account'] = self._compute_account_balance(
                    report.account_ids
                )
                for value in \
                        res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_type':
                # it's the sum the leaf accounts
                #  with such an account type
                accounts = self.env['account.account'].search([
                    ('user_type_id', 'in', report.account_type_ids.ids)
                ])
                res[report.id]['account'] = self._compute_account_balance(
                    accounts)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._compute_report_balance(report.account_report_id)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
            elif report.type == 'sum':
                # it's the sum of the children of this account.report
                res2 = self._compute_report_balance(report.children_ids)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
        return res

    def get_account_lines(self, data):
        lines = []
        account_report = self.env['account.financial.report'].search([
            ('id', '=', data['account_report_id'][0])
        ])
        child_reports = account_report._get_children_by_order()
        res = self.with_context(
            data.get('used_context'))._compute_report_balance(child_reports)
        if data['enable_filter']:
            comparison_res = self._compute_report_balance(child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in \
                            comparison_res[report_id].get('account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']

        for report in child_reports:
            r_name = str(report.name)
            # r_name = r_name.replace(" ", "-") + "-"
            r_name = re.sub('[^0-9a-zA-Z]+', '', r_name)
            if report.parent_id:
                p_name = str(report.parent_id.name)
                p_name = re.sub('[^0-9a-zA-Z]+', '', p_name) + str(
                    report.parent_id.id)
                # p_name = p_name.replace(" ", "-") +
                #  "-" + str(report.parent_id.id)
            else:
                p_name = False
            vals = {
                'r_id': report.id,
                'id': r_name + str(report.id),
                'sequence': report.sequence,
                'parent': p_name,
                'name': report.name,
                'balance': res[report.id]['balance'] * int(report.sign),
                'type': 'report',
                'level': bool(
                    report.style_overwrite) and report.style_overwrite or
                         report.level,
                'account_type': report.type or False,
                # used to underline the financial report balances
            }
            if data['debit_credit']:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * int(
                    report.sign)

            lines.append(vals)
            if report.display_detail == 'no_detail':
                # the rest of the loop is
                # used to display the details of the
                #  financial report, so it's not needed here.
                continue

            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value \
                        in res[report.id]['account'].items():
                    # if there are accounts to display,
                    #  we add them to the lines with a level equals
                    #  to their level in
                    # the COA + 1 (to avoid having them with a too low level
                    #  that would conflicts with the level of data
                    # financial reports for Assets, liabilities...)
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    # new_r_name = str(report.name)
                    # new_r_name = new_r_name.replace(" ", "-") + "-"
                    vals = {
                        'account': account.id,
                        'a_id': account.code + re.sub('[^0-9a-zA-Z]+', 'acnt',
                                                      account.name) + str(
                            account.id),
                        'name': account.code + '-' + account.name,
                        'balance': value['balance'] * int(report.sign) or 0.0,
                        'type': 'account',
                        'parent': r_name + str(report.id),
                        'level': (
                                report.display_detail == 'detail_with_hierarchy' and
                                4),
                        'account_type': account.internal_type,
                    }
                    if data['debit_credit']:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not account.company_id.currency_id.is_zero(
                                vals['debit']) or \
                                not account.company_id.currency_id.is_zero(
                                    vals['credit']):
                            flag = True
                    if not account.company_id.currency_id.is_zero(
                            vals['balance']):
                        flag = True
                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * int(
                            report.sign)
                        if not account.company_id.currency_id.is_zero(
                                vals['balance_cmp']):
                            flag = True
                    if flag:
                        sub_lines.append(vals)
                lines += sorted(sub_lines,
                                key=lambda sub_line: sub_line['name'])
        return lines

    def find_journal_items(self, report_lines, form):
        cr = self.env.cr
        journal_items = []
        for i in report_lines:
            if i['type'] == 'account':
                account = i['account']
                if form['target_move'] == 'posted':
                    search_query = "select aml.id, am.id as j_id, aml.account_id, aml.date," \
                                   " aml.name as label, am.name, " \
                                   + "(aml.debit-aml.credit) as balance, aml.debit, aml.credit, aml.partner_id " \
                                   + " from account_move_line aml join account_move am " \
                                     "on (aml.move_id=am.id and am.state=%s) " \
                                   + " where aml.account_id=%s"
                    vals = [form['target_move']]
                else:
                    search_query = "select aml.id, am.id as j_id, aml.account_id, aml.date, " \
                                   "aml.name as label, am.name, " \
                                   + "(aml.debit-aml.credit) as balance, aml.debit, aml.credit, aml.partner_id " \
                                   + " from account_move_line aml join account_move am on (aml.move_id=am.id) " \
                                   + " where aml.account_id=%s"
                    vals = []
                if form['date_from'] and form['date_to']:
                    search_query += " and aml.date>=%s and aml.date<=%s"
                    vals += [account, form['date_from'], form['date_to']]
                elif form['date_from']:
                    search_query += " and aml.date>=%s"
                    vals += [account, form['date_from']]
                elif form['date_to']:
                    search_query += " and aml.date<=%s"
                    vals += [account, form['date_to']]
                else:
                    vals += [account]
                cr.execute(search_query, tuple(vals))
                items = cr.dictfetchall()

                for j in items:
                    temp = j['id']
                    j['id'] = re.sub('[^0-9a-zA-Z]+', '', i['name']) + str(
                        temp)
                    j['p_id'] = str(i['a_id'])
                    j['type'] = 'journal_item'
                    journal_items.append(j)
        return journal_items

    @api.model
    def _get_currency(self):
        journal = self.env['account.journal'].browse(
            self.env.context.get('default_journal_id', False))
        if journal.currency_id:
            return journal.currency_id.id
        return self.env.company.currency_id.symbol


class ProfitLossPdf(models.AbstractModel):
    """ Abstract model for generating PDF report value and send to template """

    _name = 'report.orchid_account_enhancement_v14.report_financial'
    _description = 'Financial Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """ Provide report values to template """
        ctx = {
            'data': data,
            'journal_items': data['journal_items'],
            'report_lines': data['report_lines'],
            'account_report': data['form']['account_report_id'][1],
            'currency': data['currency'],
        }
        return ctx
