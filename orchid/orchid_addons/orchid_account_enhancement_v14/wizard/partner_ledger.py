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
from odoo.tools.misc import get_lang
import xlsxwriter
from io import BytesIO
import base64
from datetime import datetime

class AccountPartnerLedger(models.TransientModel):
    _name = "account.report.partner.ledger"
    _inherit = "account.common.partner.report"
    _description = "Account Partner Ledger"

    amount_currency = fields.Boolean("With Currency",
                                     help="It adds the currency column on report if the "
                                          "currency differs from the company currency.")
    reconciled = fields.Boolean('Reconciled Entries', default=True)
    summary = fields.Boolean('Summary')
    partner_ids = fields.Many2many('res.partner',string="Partners")
    excel_file = fields.Binary(string='Dowload Report Excel',readonly="1")
    file_name = fields.Char(string='Excel File',readonly="1")
    user_ids = fields.Many2many('res.users', string='Salesperson')#orchid field


    def _print_report(self, data):
        data = self.pre_print_report(data)
        partner_ids = self.partner_ids and self.partner_ids.ids or False
        user_ids = self.user_ids and self.user_ids.ids or False
        data['form'].update({'reconciled': self.reconciled,
                             'amount_currency': self.amount_currency,'partner_ids': partner_ids,'user_ids': user_ids,'summary':self.summary})
        return self.env.ref(
            'orchid_account_enhancement_v14.action_report_partnerledger').with_context(landscape=True).report_action(
            self, data=data)



    #************************EXCEL**************#
    def od_generate_excel_report(self):

        # fetch accounts and partners
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        data = self.pre_print_report(data)
        partner_ids = self.partner_ids and self.partner_ids.ids or False
        user_ids = self.user_ids and self.user_ids.ids or False
        data['form'].update({'reconciled': self.reconciled,
                             'amount_currency': self.amount_currency,'partner_ids': partner_ids,'user_ids': user_ids,'summary':self.summary})
        if not data.get('form'):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))

        data['computed'] = {}

        obj_partner = self.env['res.partner']
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {}))._query_get()
        data['computed']['move_state'] = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            data['computed']['move_state'] = ['posted']
        result_selection = data['form'].get('result_selection', 'customer')
        if result_selection == 'supplier':
            data['computed']['ACCOUNT_TYPE'] = ['payable']
        elif result_selection == 'customer':
            data['computed']['ACCOUNT_TYPE'] = ['receivable']
        else:
            data['computed']['ACCOUNT_TYPE'] = ['payable', 'receivable']

        self.env.cr.execute("""
            SELECT a.id
            FROM account_account a
            WHERE a.internal_type IN %s
            AND NOT a.deprecated""",
                            (tuple(data['computed']['ACCOUNT_TYPE']),))
        data['computed']['account_ids'] = [a for (a,) in
                                           self.env.cr.fetchall()]
        params = [tuple(data['computed']['move_state']),
                  tuple(data['computed']['account_ids'])] + query_get_data[2]
        reconcile_clause = "" if data['form'][
            'reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
        if data['form']['partner_ids']:
            partner_ids = data['form']['partner_ids']
        else:
            query = """
                SELECT DISTINCT "account_move_line".partner_id
                FROM """ + query_get_data[0] + """, account_account AS account, account_move AS am
                WHERE "account_move_line".partner_id IS NOT NULL
                    AND "account_move_line".account_id = account.id
                    AND am.id = "account_move_line".move_id
                    AND am.state IN %s
                    AND "account_move_line".account_id IN %s
                    AND NOT account.deprecated
                    AND """ + query_get_data[1] + reconcile_clause
            self.env.cr.execute(query, tuple(params))
            partner_ids = [res['partner_id'] for res in self.env.cr.dictfetchall()]

        '''########to filter partner with non zero debit and credit######'''
        filter_params = [tuple(partner_ids), tuple(data['computed']['move_state']),
              tuple(data['computed']['account_ids'])] + \
             query_get_data[2]

        where_qry = ""
        if data['form'].get('user_ids'):
            where_qry+=""" AND m.invoice_user_id IN %s """
            filter_params += (tuple(data['form'].get('user_ids')),)

        filter_qry = """SELECT sum(debit) as debit,sum(credit) as credit, "account_move_line".partner_id as partner
            FROM """ + query_get_data[0] + """, account_move AS m
            WHERE "account_move_line".partner_id in %s
                AND m.id = "account_move_line".move_id
                AND m.state IN %s
                AND account_id IN %s
                AND """ + query_get_data[1] + reconcile_clause+ where_qry+"""group by "account_move_line".partner_id"""
        self.env.cr.execute(filter_qry, tuple(filter_params))
        filter_partner = self.env.cr.dictfetchall()
        partner_ids=[]
        for res in filter_partner:
            if res['credit']!=0.0 or res['debit']!=0.0:
                partner_ids.append(res['partner'])
        '''####################################################################################'''
        partners = obj_partner.browse(partner_ids)
        partners = sorted(partners, key=lambda x: (x.ref or '', x.name or ''))

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
        if self.summary:
            sheet.set_column('A:A',45)
            headings = ['Partner','Debit','Credit','Balance']
            col_merge=col+3
        else:
            sheet.set_column('B:B',45)
            headings = ['Date','Ref','Debit','Credit','Balance','Cum.Balance']
            col_merge=col+5
        sheet.merge_range(row,col,row,col_merge,"Partner Ledger",style5)
        row = row+2
        if self.date_from:
            col=0
            sheet.merge_range(row,col,row,2,"Date From"+" :"+str(self.date_from),style6)
            row=row+1
        if self.date_to:
            col=0
            sheet.merge_range(row,col,row,2,"Date to"+"      :"+str(self.date_to),style6)
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
        for partner in partners:
            col=0
            if not self.summary:
                sheet.write(row,col,partner.ref,style1)
                col=col+1
            sheet.write(row,col,partner.name,style1)
            col=col+1
            sheet.write(row,col,self._sum_partner(data, partner, 'debit'),style2)
            col=col+1
            sheet.write(row,col,self._sum_partner(data, partner, 'credit'),style2)
            col=col+1
            bal_col=col
            bal_row=row
            if not self.summary:
                col=col+1
            sheet.write(row,col,self._sum_partner(data, partner, 'debit - credit'),style2)
            row=row+1
            if not self.summary:
                partner_lines = self._lines(data, partner)
                for line in partner_lines:
                    col=0
                    date=str(line['date'])
                    date = datetime.strptime(str(line['date']), '%Y-%m-%d').strftime('%d-%m-%Y')
                    sheet.write(row,col,date,style3)
                    col=col+1
                    sheet.write(row,col,line['displayed_name'],style3)
                    col=col+1
                    sheet.write(row,col,line['debit'],style4)
                    col=col+1
                    sheet.write(row,col,line['credit'],style4)
                    col=col+1
                    sheet.write(row,col,(line['debit']-line['credit']),style4)
                    col=col+1
                    sheet.write(row,col,line['progress'],style4)
                    row=row+1
                if partner_lines:
                    sheet.write(bal_row,bal_col,line['progress'],style2)

        workbook.close()
        output.seek(0)
        excel_file = base64.encodestring(output.read())
        self.excel_file = excel_file
        filename= 'PartnerLedger.xlsx'
        self.file_name =filename
        ir_model_data = self.env['ir.model.data']
        compose_form_id = ir_model_data.get_object_reference('orchid_account_enhancement_v14', 'account_report_partner_ledger_view')[1]

        return {            
        'type': 'ir.actions.act_window',            
        'view_type': 'form',            
        'view_mode': 'form',            
        'res_model': 'account.report.partner.ledger',            
        'views': [(compose_form_id, 'form')], 
        'res_id': self.id,           
        'view_id': compose_form_id,            
        'target': 'new',            
        }

    def _sum_partner(self, data, partner, field):
        if field not in ['debit', 'credit', 'debit - credit']:
            return
        result = 0.0
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {}))._query_get()
        reconcile_clause = "" if data['form'][
            'reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '

        params = [partner.id, tuple(data['computed']['move_state']),
                  tuple(data['computed']['account_ids'])] + \
                 query_get_data[2]

        where_qry = ""
        if data['form'].get('user_ids'):
                where_qry+=""" AND m.invoice_user_id IN %s """
                params += (tuple(data['form'].get('user_ids')),)


        query = """SELECT sum(""" + field + """)
                FROM """ + query_get_data[0] + """, account_move AS m
                WHERE "account_move_line".partner_id = %s
                    AND m.id = "account_move_line".move_id
                    AND m.state IN %s
                    AND account_id IN %s
                    AND """ + query_get_data[1] + reconcile_clause + where_qry
        self.env.cr.execute(query, tuple(params))

        contemp = self.env.cr.fetchone()
        if contemp is not None:
            result = contemp[0] or 0.0
        return result

    def _lines(self, data, partner):
        full_account = []
        if not data['form']['summary']:
            currency = self.env['res.currency']
            query_get_data = self.env['account.move.line'].with_context(
                data['form'].get('used_context', {}))._query_get()
            reconcile_clause = "" if data['form'][
                'reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
            params = [partner.id, tuple(data['computed']['move_state']),
                      tuple(data['computed']['account_ids'])] + \
                     query_get_data[2]
            where_qry = ""
            if data['form'].get('user_ids'):
                where_qry+=""" AND m.invoice_user_id IN %s """
                params += (tuple(data['form'].get('user_ids')),)

            query = """
                SELECT "account_move_line".id, "account_move_line".date, j.code, acc.code as a_code, acc.name as a_name, "account_move_line".ref, m.name as move_name, "account_move_line".name, "account_move_line".debit, "account_move_line".credit, "account_move_line".amount_currency,"account_move_line".currency_id, c.symbol AS currency_code, m.move_type as move_type
                FROM """ + query_get_data[0] + """
                LEFT JOIN account_journal j ON ("account_move_line".journal_id = j.id)
                LEFT JOIN account_account acc ON ("account_move_line".account_id = acc.id)
                LEFT JOIN res_currency c ON ("account_move_line".currency_id=c.id)
                LEFT JOIN account_move m ON (m.id="account_move_line".move_id)
                WHERE "account_move_line".partner_id = %s
                    AND m.state IN %s
                    AND "account_move_line".account_id IN %s AND """ + \
                    query_get_data[1] + reconcile_clause + where_qry + """
                    ORDER BY "account_move_line".date"""
            self.env.cr.execute(query, tuple(params))
            res = self.env.cr.dictfetchall()
            sum = 0.0
            lang_code = self.env.context.get('lang') or 'en_US'
            lang = self.env['res.lang']
            lang_id = lang._lang_get(lang_code)
            date_format = lang_id.date_format
            for r in res:
                r['date'] = r['date']
                r['displayed_name'] = '-'.join(
                    r[field_name] for field_name in ('move_name', 'ref', 'name')
                    if r[field_name] not in (None, '', '/')
                )
                sum += r['debit'] - r['credit']
                r['balance'] = r['debit'] - r['credit']#newly added
                r['inv_no'] = r['move_name'] if r['move_type'] in ('out_invoice','out_refund','in_invoice','in_refund') else ""#newly added
                r['progress'] = sum
                r['currency_id'] = currency.browse(r.get('currency_id'))
                full_account.append(r)
        return full_account





