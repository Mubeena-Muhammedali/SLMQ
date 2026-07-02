# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    od_lark_domain = fields.Selection(
        selection=[
            ('https://open.feishu.cn', 'Feishu (China)'),
            ('https://open.larksuite.com', 'Lark (International)'),
        ],
        string='Lark Platform',
        config_parameter='lark_attendance_sync.domain',
        default='https://open.larksuite.com',
    )
    od_lark_app_id = fields.Char(
        string='Lark App ID',
        config_parameter='lark_attendance_sync.app_id',
    )
    od_lark_app_secret = fields.Char(
        string='Lark App Secret',
        config_parameter='lark_attendance_sync.app_secret',
    )
    od_lark_sync_days_back = fields.Integer(
        string='Days to Look Back on Each Sync',
        config_parameter='lark_attendance_sync.days_back',
        default=1,
        help='Each sync run will pull punch records from N days ago until now. '
             'Keep this small (1-3) for a cron that runs every few hours.',
    )
