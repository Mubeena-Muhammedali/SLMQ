# -*- coding: utf-8 -*-
import io
from datetime import date

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
        sheet.title = 'Attendance & Time Off'

        header_font = Font(bold=True)

        # Row 1: column headers - one table, any number of employees/dates below
        headers = ['Employee Name', 'Date', 'Hours', 'Time Off Type', 'Time off']
        for col, title in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=col, value=title)
            cell.font = header_font

        

        sheet.column_dimensions['A'].width = 18
        sheet.column_dimensions['B'].width = 14
        sheet.column_dimensions['C'].width = 10
        sheet.column_dimensions['D'].width = 18
        sheet.column_dimensions['E'].width = 12

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
