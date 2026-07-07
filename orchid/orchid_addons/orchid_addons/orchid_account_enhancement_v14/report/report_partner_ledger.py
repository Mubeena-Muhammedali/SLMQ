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
import datetime

from odoo import api, models, _
from odoo.exceptions import UserError


class ReportPartnerLedger(models.AbstractModel):
    _name = 'report.orchid_account_enhancement_v14.report_partnerledger'
    _description = 'Partner Ledger Report'

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
                    query_get_data[1] + reconcile_clause + where_qry+ """
                    ORDER BY "account_move_line".date"""
            self.env.cr.execute(query, tuple(params))
            res = self.env.cr.dictfetchall()
            sum = 0.0
            lang_code = self.env.context.get('lang') or 'en_US'
            lang = self.env['res.lang']
            lang_id = lang._lang_get(lang_code)
            date_format = lang_id.date_format
            for r in res:
                r['date'] = r['date'].strftime("%d-%m-%Y")
                r['displayed_name'] = '-'.join(
                    r[field_name] for field_name in ('move_name', 'ref', 'name')
                    if r[field_name] not in (None, '', '/')
                )
                sum += r['debit'] - r['credit']
                r['balance'] = r['debit'] - r['credit']#newly added
                r['inv_no'] = r['move_name'] if r['move_type'] in ('out_invoice','out_refund','in_invoice','in_refund') else ""#newly added
                r['progress'] = round(sum,2)
                r['currency_id'] = currency.browse(r.get('currency_id'))
                full_account.append(r)
        return full_account

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

    @api.model
    def _get_report_values(self, docids, data=None):
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
                AND """ + query_get_data[1] + reconcile_clause+ where_qry +"""group by "account_move_line".partner_id"""
        self.env.cr.execute(filter_qry, tuple(filter_params))
        filter_partner = self.env.cr.dictfetchall()
        partner_ids=[]
        for res in filter_partner:
            if res['credit']!=0.0 or res['debit']!=0.0:
                partner_ids.append(res['partner'])
        '''####################################################################################'''
        partners = obj_partner.browse(partner_ids)
        partners = sorted(partners, key=lambda x: (x.ref or '', x.name or ''))
        
        return {
            'doc_ids': partner_ids,
            'doc_model': self.env['res.partner'],
            'data': data,
            'docs': partners,
            'time': time,
            'lines': self._lines,
            'sum_partner': self._sum_partner,
        }
        
