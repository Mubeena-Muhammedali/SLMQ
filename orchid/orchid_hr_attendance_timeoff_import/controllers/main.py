# -*- coding: utf-8 -*-
import io

from odoo import http
from odoo.http import request

try:
    import openpyxl
    from openpyxl.styles import Font
except ImportError:
    openpyxl = None


class OdAttendanceTimeoffImportController(http.Controller):

    @http.route('/hr_attendance_timeoff_import/template', type='http', auth='user')
    def download_template(self, **kwargs):
        if not openpyxl:
            return request.make_response(
                'The "openpyxl" Python library is not installed on the server.',
                headers=[('Content-Type', 'text/plain')],
            )

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'Timesheet'

        bold = Font(bold=True)

        # Row 1: employee + month
        sheet['A1'] = 'Employee Name'
        sheet['B1'] = 'John Doe'
        sheet['C1'] = 'Month'
        sheet['D1'] = '2025-09'
        sheet['A1'].font = bold
        sheet['C1'].font = bold

        # Row 2: headers
        headers = ['Date', 'Hours', 'Time Off Type']
        for col, title in enumerate(headers, start=1):
            cell = sheet.cell(row=2, column=col, value=title)
            cell.font = bold

        sheet.column_dimensions['A'].width = 16
        sheet.column_dimensions['B'].width = 12
        sheet.column_dimensions['C'].width = 22
        sheet.column_dimensions['D'].width = 14

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        return request.make_response(
            buffer.read(),
            headers=[
                ('Content-Type',
                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition',
                 'attachment; filename="attendance_timeoff_template.xlsx"'),
            ],
        )
