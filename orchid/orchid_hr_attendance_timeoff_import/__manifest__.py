{
    'name': 'Orchid Attendance & Time Off Import',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Import monthly attendance and time off from an Excel timesheet',
    'description': """
Import Attendance & Time Off from an Excel Timesheet
=====================================================

Adds a wizard (menu: Attendances > Reporting > Import Attendance / Time Off)
that lets you:

 - Download a ready-to-fill Excel template.
 - Fill in one sheet per employee:
     * Row 1  : Employee Name | <name> | Month | <YYYY-MM>
     * Row 2  : Column headers -> Date | Hours | Time Off Type
     * Row 3+ : One line per day of the month.
 - Upload the file back:
     * A row with the "Hours" cell filled in creates an Attendance record
       for that day. Overtime is calculated automatically: any hours
       worked beyond the "Standard Daily Hours" configured on the
       Company are stored as Overtime Hours, the rest as Regular Hours.
     * A row with the "Time Off Type" cell filled in creates a Time Off
       (leave) request for that day, matched to an existing Time Off
       Type by name.
     * Only one of the two columns should be filled per row - whichever
       one has a value identifies the row as Attendance or Time Off.
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
