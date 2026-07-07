# -*- coding: utf-8 -*-

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
        data['form'].update({'detail': self.detail,'od_with_closing':self.od_with_closing})
        records = self.env[data['model']].browse(data.get('ids', []))
        print("dataaaaaaaaa",data)
        return self.env.ref(
            'orchid_account_enhancement_v14.action_report_trial_balance').with_context(landscape=True).report_action(
            records, data=data)

