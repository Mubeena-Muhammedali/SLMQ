# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    od_lark_user_id = fields.Char(
        string='Lark User ID',
        copy=False,
        help='The employee_id (or open_id, depending on configuration) of this '
             'person in the Lark Platform. Required for attendance sync.',
    )
