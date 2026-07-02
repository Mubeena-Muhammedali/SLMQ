# -*- coding: utf-8 -*-
from odoo import fields, models


class OdLarkSyncLog(models.Model):
    _name = 'od.lark.sync.log'
    _description = 'Lark Attendance Sync Log'
    _order = 'create_date desc'

    date = fields.Datetime(string='Run Date', default=fields.Datetime.now, required=True)
    state = fields.Selection(
        [('success', 'Success'), ('error', 'Error')],
        string='Status', required=True, default='success',
    )
    employees_processed = fields.Integer(string='Employees Processed')
    attendances_created = fields.Integer(string='Attendances Created')
    attendances_updated = fields.Integer(string='Attendances Updated')
    message = fields.Text(string='Details')
