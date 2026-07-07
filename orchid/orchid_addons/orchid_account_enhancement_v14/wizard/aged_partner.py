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

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools import float_is_zero

import xlsxwriter
from io import BytesIO
import base64
# import logging
# _logger = logging.getLogger(__name__)


class AccountAgedTrialBalance(models.TransientModel):
    _name = 'account.aged.trial.balance'
    _inherit = 'account.common.partner.report'
    _description = 'Account Aged Trial balance Report'

    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   required=True)
    period_length = fields.Integer(string='Period Length (days)',
                                   required=True, default=30)
    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))
    excel_file = fields.Binary(string='Dowload Report Excel',readonly="1")
    file_name = fields.Char(string='Excel File',readonly="1")
    partner_ids = fields.Many2many('res.partner', string='Partner')#orchid field
    user_ids = fields.Many2many('res.users', string='Salesperson')#orchid field

    def _print_report(self, data):

        res = {}
        data = self.pre_print_report(data)
        data['form'].update(self.read(['period_length'])[0])
        period_length = data['form']['period_length']
        if period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise UserError(_('You must set a start date.'))

        start = data['form']['date_from']

        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            res[str(i)] = {
                'name': (i != 0 and (
                            str((5 - (i + 1)) * period_length) + '-' + str(
                        (5 - i) * period_length)) or (
                                     '+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'].update(res)
        partner_ids = self.partner_ids and self.partner_ids.ids or False
        data['form'].update({'partner_ids': partner_ids})
        user_ids = self.user_ids and self.user_ids.ids or False
        data['form'].update({'user_ids': user_ids})
        return self.env.ref(
            'orchid_account_enhancement_v14.action_report_aged_partner_balance').with_context(
            landscape=True).report_action(self, data=data)

    #************************EXCEL**************#
    def od_generate_excel_report(self):
        res = {}
        data = {}
        data['form']={}
        data['form'].update(self.read(['result_selection','date_from','target_move'])[0]) 
        data['form'].update(self.read(['period_length'])[0])
        partner_ids = self.partner_ids and self.partner_ids.ids or False
        data['form'].update({'partner_ids': partner_ids})
        user_ids = self.user_ids and self.user_ids.ids or False
        data['form'].update({'user_ids': user_ids})
        period_length = data['form']['period_length']
        if period_length <= 0:
            raise UserError(_('You must set a period length greater than 0.'))
        if not data['form']['date_from']:
            raise UserError(_('You must set a start date.'))

        start = data['form']['date_from']

        for i in range(5)[::-1]:
            stop = start - relativedelta(days=period_length - 1)
            res[str(i)] = {
                'name': (i != 0 and (
                            str((5 - (i + 1)) * period_length) + '-' + str(
                        (5 - i) * period_length)) or (
                                     '+' + str(4 * period_length))),
                'stop': start.strftime('%Y-%m-%d'),
                'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
            }
            start = stop - relativedelta(days=1)
        data['form'].update(res)


        total = []
        # model = self.env.context.get('active_model')
        # docs = self.env[model].browse(self.env.context.get('active_id'))

        target_move = data['form'].get('target_move', 'all')
        date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))

        if data['form']['result_selection'] == 'customer':
            account_type = ['receivable']
            account_type_str = "Receivable Accounts"
        elif data['form']['result_selection'] == 'supplier':
            account_type = ['payable']
            account_type_str = "Payable Accounts"
        else:
            account_type = ['payable', 'receivable']
            account_type_str = "Receivable & Payable Accounts"

        # movelines, total, dummy = self.env['report.orchid_account_enhancement_v14.report_agedpartnerbalance']._get_partner_move_lines(account_type,
        #                                                        str(date_from),
        #                                                        target_move,
        #                                                        data['form'][
        #                                                            'period_length'])

        movelines, total, dummy = self.env['report.orchid_account_enhancement_v14.report_agedpartnerbalance']._get_partner_move_lines(account_type,
                                                               str(date_from),
                                                               target_move,
                                                               data['form'])


        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet= workbook.add_worksheet('AgedPartnerBalance')
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'fg_color': '#D7E4BC',
            'border': 0}) 
        header_style = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color':'#aeadad',
            'border':0})
        # tot_format = workbook.add_format({
        #   'bold': True,
        #   'align': 'left',
        #   'border': 0})
        tot_format1 = workbook.add_format({
            'bold': True,
            'align': 'right',
            'num_format': '#,##0.00',
            'border': 0})
        info_style = workbook.add_format({
            'bold': True,
            'border': 0})
        row_num_style = workbook.add_format({'num_format': '#,##0.00'}) 

        header_range = 'A1:H1'
        header = "Aged Partner Balance from "+str(self.date_from)
        sheet.merge_range(header_range,header,title_format)
        row = 0
        row = row + 2
        col = 0
        sheet.merge_range(row,col,row,2,"Start Date"+" :"+str(self.date_from),info_style)
        row = row + 1
        # vat = self.partner_id.vat or ""
        sheet.merge_range(row,col,row,2,"Period Length (days)"+" :"+ str(self.period_length),info_style)
        row = row + 1
        sheet.merge_range(row,col,row,2,"Partner's"+" :"+account_type_str,info_style)
        row = row + 1
        target_move = "All Entries"
        if self.target_move =='posted':
            target_move = "All Posted Entries"
        sheet.merge_range(row,col,row,2,"Target Moves:"+" :"+target_move,info_style)
        row = row + 1
        sheet.merge_range(row,col,row,2,"Currency"+" :"+self.env.company.currency_id.name,info_style)

        headers = ["Partner","Not Due", data['form']['4']['name'],data['form']['3']['name'],data['form']['2']['name'],data['form']['1']['name'],data['form']['0']['name'],"Total"]

        if movelines:
            add_headers = ["Account Total",total[6],total[4],total[3],total[2],total[1],total[0],total[5]]

        sheet.set_column('A:A',25)
        sheet.set_column('B:B',15)
        sheet.set_column('C:C',15)
        sheet.set_column('D:D',15)
        sheet.set_column('E:E',15)
        sheet.set_column('F:F',15)
        sheet.set_column('G:G',15)
        sheet.set_column('H:H',15)
        sheet.set_column('I:I',15)
        sheet.set_column('J:J',15)

        row=row+1
        col=0
        for heading in headers:
            sheet.write(row,col,heading,header_style)
            col = col + 1
        row=row+1
        col=0
        # _logger.debug("movelines****************************************************8")
        # _logger.debug("movelines****************************************************8")
        # _logger.debug("movelines****************************************************8")
        # _logger.debug("movelines****************************************************8")
        # _logger.debug("movelines****************************************************8")
        # _logger.debug("movelines****************************************************8")
        # _logger.debug("movelines****************************************************8")
        # _logger.debug("movelines****************************************************8 %s",movelines)
        if movelines:
            for heading in add_headers:
                if col==0:
                    att_style=info_style
                else:
                    att_style=tot_format1
                sheet.write(row,col,heading,att_style)
                col = col + 1
                # if self.partner_ids:
                #     movelines = [sub for sub in movelines if sub['partner_id'] in self.partner_ids.ids]
        for partner in movelines:
            row=row+1
            col=0
            sheet.write(row,col,partner['name'])
            col=col+1
            sheet.write(row,col,partner['direction'],row_num_style)
            col=col+1
            sheet.write(row,col,partner['4'],row_num_style)
            col=col+1
            sheet.write(row,col,partner['3'],row_num_style)
            col=col+1
            sheet.write(row,col,partner['2'],row_num_style)
            col=col+1
            sheet.write(row,col,partner['1'],row_num_style)
            col=col+1
            sheet.write(row,col,partner['0'],row_num_style)
            col=col+1
            sheet.write(row,col,partner['total'],row_num_style)
        workbook.close()
        output.seek(0)
        excel_file = base64.encodestring(output.read())
        self.excel_file = excel_file
        filename= 'AgedPartnerBalance.xlsx'
        self.file_name =filename
        return {            
        'type': 'ir.actions.act_window',            
        'view_type': 'form',            
        'view_mode': 'form',            
        'res_model': 'account.aged.trial.balance',            
        'res_id': self.id,           
        # 'view_id': compose_form_id,            
        'target': 'new',            
        }
















