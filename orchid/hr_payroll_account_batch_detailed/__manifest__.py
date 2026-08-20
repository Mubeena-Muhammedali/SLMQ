# -*- coding: utf-8 -*-
{
    'name': 'Payroll Batch Move Lines - Detailed by Employee',
    'category': 'Human Resources/Payroll',
    'summary': 'Batch payroll journal entries per period while keeping separate accounting lines per employee.',
    'description': """
Payroll Batch Move Lines - Detailed by Employee
================================================

Adds a new company setting, "Batch Payroll Move Lines (Detailed by Employee)", on top of
the standard "Batch Payroll Move Lines" setting from hr_payroll_account.

Priority logic
--------------
- Both settings disabled: normal behavior, one journal entry per payslip.
- Only "Batch Payroll Move Lines" enabled: current/standard behavior, one journal entry
  per journal/month, with amounts merged into a single line per account across all
  employees.
- "Batch Payroll Move Lines (Detailed by Employee)" enabled (with or without the other
  setting also enabled): one journal entry per journal/month is still created, but each
  account keeps a separate accounting line per employee, following each salary rule's own
  "Set employee on account line" setting. The detailed setting always takes priority when
  both are enabled.

This module does not modify hr_payroll_account; it only extends it.
    """,
    'depends': ['hr_payroll_account'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'OEEL-1',
}
