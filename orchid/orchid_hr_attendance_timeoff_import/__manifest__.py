{
    'name': 'Orchid Attendance & Time Off Import',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Import attendance and time off for multiple employees from an Excel timesheet',
    'description': """
Import Attendance & Time Off from an Excel Timesheet
=====================================================

Adds a wizard (menu: Attendances > Reporting > Import Attendance / Time Off)
that lets you:

 - Download a ready-to-fill Excel template (one table, any number of
   employees and dates).
 - Fill in one row per employee per day, from row 2 onward:
     Employee Name | Date | Hours | Time Off Type | Time off
 - Upload the file back:
     * Hours only -> a plain Attendance record for that many hours
       (no cap, so overtime days are supported).
     * Time Off Type only -> a Time Off request. The "Time off" column
       gives the number of hours off (e.g. 8 = a full day); if left
       blank a full standard day is assumed. Any hours left over up to
       the employee's standard daily hours are logged as Attendance
       automatically.
     * Both Hours and Time Off Type filled -> Hours is treated as the
       actual worked time, and Time Off is recalculated as
       (standard daily hours - Hours), so the day always adds up to
       the employee's standard hours.
""",
    "author": "OrchidERP",
    "website": "http://www.orchiderp.com",
    'license': 'LGPL-3',
    'depends': ['hr_attendance', 'hr_holidays'],
    'external_dependencies': {'python': ['openpyxl']},
    'data': [
        'security/ir.model.access.csv',
        'wizard/attendance_timeoff_import_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
