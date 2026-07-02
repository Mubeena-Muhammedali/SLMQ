# -*- coding: utf-8 -*-
{
    'name': 'Lark Attendance Sync',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Sync employee check-in/check-out records from Lark (Feishu) into Odoo Attendances',
    'description': """
Lark (Feishu) Attendance Sync
==============================
Pulls punch/check-in records from the Lark Open Platform Attendance API
and creates matching hr.attendance records in Odoo.

Features
--------
* Configure Lark App ID / App Secret / domain (Feishu CN or Lark Intl) in Settings.
* Map each hr.employee to their Lark user_id.
* Manual "Sync Now" button.
* Scheduled action (cron) to sync automatically every N hours.
* Sync log kept on each employee / in server logs for troubleshooting.
""",
    "author": "OrchidERP",
    "website": "http://www.orchiderp.com",
    'license': 'LGPL-3',
    'depends': ['hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
        'views/hr_employee_views.xml',
        'views/lark_sync_log_views.xml',
    ],
    'installable': True,
    'application': False,
}
