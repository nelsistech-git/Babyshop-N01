from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta
import calendar
import io
import base64
import pytz
from odoo.http import request


class AttendanceSheetCheckInOutWizard(models.TransientModel):
    _name = 'attendance.sheet.checkin.checkout.wizard'
    _description = 'Attendance Sheet Check In / Check Out Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: date.today().replace(
            day=calendar.monthrange(date.today().year, date.today().month)[1]
        )
    )
    department_id = fields.Many2one('hr.department', string='Department')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    location = fields.Char(string='Location')

    def action_download_excel(self):
        report_data = self._get_report_data()

        try:
            import xlsxwriter
        except ImportError:
            raise UserError("xlsxwriter library is not installed.")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Attendance')

        # ── Formats ──────────────────────────────────────────────
        fmt_title = workbook.add_format({
            'bold': True, 'font_size': 12, 'font_name': 'Arial'
        })
        fmt_company = workbook.add_format({
            'bold': True, 'font_size': 18, 'font_name': 'Arial',
            'align': 'center', 'valign': 'vcenter',           # ← center
        })
        fmt_address = workbook.add_format({
            'font_size': 10, 'font_name': 'Arial',
            'align': 'center', 'valign': 'vcenter',           # ← center
            'text_wrap': True,
        })
        fmt_title_center = workbook.add_format({
            'bold': True, 'font_size': 12, 'font_name': 'Arial',
            'align': 'center',
        })
        fmt_header = workbook.add_format({
            'bold': True, 'bg_color': '#F0F0F0',
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'font_name': 'Arial', 'font_size': 8, 'text_wrap': True
        })
        fmt_sl = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'font_name': 'Arial', 'font_size': 8
        })
        fmt_text = workbook.add_format({
            'border': 1, 'valign': 'vcenter',
            'font_name': 'Arial', 'font_size': 8
        })
        fmt_in = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center',
            'font_color': '#006400', 'font_name': 'Arial', 'font_size': 8
        })
        fmt_out = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center',
            'font_color': '#8B0000', 'font_name': 'Arial', 'font_size': 8
        })
        fmt_cell = workbook.add_format({
            'border': 1, 'align': 'center', 'font_name': 'Arial', 'font_size': 8
        })

        # ── Company Info from Odoo (dynamic) ─────────────────────
        company = self.env.company
        COMPANY_NAME = company.name or ''
        address_parts = []
        if company.street:
            address_parts.append(company.street)
        if company.street2:
            address_parts.append(company.street2)
        if company.city:
            address_parts.append(company.city)
        if company.state_id:
            address_parts.append(company.state_id.name)
        if company.zip:
            address_parts.append(company.zip)
        if company.country_id:
            address_parts.append(company.country_id.name)
        COMPANY_ADDRESS = ', '.join(filter(None, address_parts))

        n_dates = len(report_data['date_headers'])
        last_col = 4 + n_dates - 1

        # ── Company Logo — floating top-left ─────────────────────
        if company.logo:
            try:
                logo_bytes = base64.b64decode(company.logo)
                sheet.insert_image(
                    0, 0, 'company_logo.png',
                    {
                        'image_data': io.BytesIO(logo_bytes),
                        'x_scale': 0.50,
                        'y_scale': 0.50,
                        'x_offset': 6,
                        'y_offset': 6,
                        'object_position': 1,
                    }
                )
            except Exception:
                pass

        # ── Company Name & Address — centered across ALL columns ──
        sheet.merge_range(0, 0, 0, last_col, COMPANY_NAME, fmt_company)
        sheet.merge_range(1, 0, 1, last_col, COMPANY_ADDRESS, fmt_address)
        sheet.set_row(0, 36)   # Company name row height
        sheet.set_row(1, 20)   # Address row height

        # Empty row 2 for spacing
        sheet.set_row(2, 12)

        # ── Title rows — centered ─────────────────────────────────
        sheet.merge_range(3, 0, 3, last_col, 'Attendance Report', fmt_title_center)
        sheet.merge_range(4, 0, 4, last_col,
                         'For the month of ' + self.date_from.strftime('%B - %Y'), fmt_title_center)
        if self.location:
            sheet.merge_range(5, 0, 5, last_col, self.location, fmt_title_center)
            header_row = 7
        else:
            header_row = 6

        date_headers = report_data['date_headers']
        employees = report_data['employees']

        # ── Column widths ─────────────────────────────────────────
        sheet.set_column(0, 0, 4)   # SL
        sheet.set_column(1, 1, 20)  # Employee Name
        sheet.set_column(2, 2, 15)  # Department
        sheet.set_column(3, 3, 4)   # IN/OUT label
        sheet.set_column(4, last_col, 9)  # date columns

        # ── Header row ────────────────────────────────────────────
        sheet.write(header_row, 0, 'SL', fmt_header)
        sheet.write(header_row, 1, 'Employee Name', fmt_header)
        sheet.write(header_row, 2, 'Department', fmt_header)
        sheet.write(header_row, 3, '', fmt_header)
        for col_idx, dh in enumerate(date_headers):
            sheet.write(header_row, 4 + col_idx, dh, fmt_header)

        # ── Data rows ─────────────────────────────────────────────
        current_row = header_row + 1
        for emp in employees:
            # IN row
            sheet.merge_range(
                current_row, 0, current_row + 1, 0,
                emp['sl'], fmt_sl
            )
            sheet.merge_range(
                current_row, 1, current_row + 1, 1,
                emp['name'], fmt_text
            )
            sheet.merge_range(
                current_row, 2, current_row + 1, 2,
                emp['department'], fmt_text
            )
            sheet.write(current_row, 3, 'IN', fmt_in)
            for col_idx, d in enumerate(emp['dates']):
                sheet.write(current_row, 4 + col_idx, d['check_in'], fmt_cell)

            # OUT row
            sheet.write(current_row + 1, 3, 'OUT', fmt_out)
            for col_idx, d in enumerate(emp['dates']):
                sheet.write(current_row + 1, 4 + col_idx, d['check_out'], fmt_cell)

            current_row += 2

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read()).decode('utf-8')

        # ── Attachment তৈরি করে download দেওয়া ─────────────────────
        filename = 'Attendance_{}_{}.xlsx'.format(
            self.date_from.strftime('%Y%m%d'),
            self.date_to.strftime('%Y%m%d')
        )
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment.id),
            'target': 'self',
        }

    def _get_report_data(self):
        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)
        date_from = self.date_from
        date_to = self.date_to
        date_list = []
        current = date_from
        while current <= date_to:
            date_list.append(current)
            current += timedelta(days=1)

        domain = [('active', '=', True)]
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))
        employees = self.env['hr.employee'].search(domain, order='name asc')

        att_domain = [
            ('employee_id', 'in', employees.ids),
            ('check_in', '>=', str(date_from) + ' 00:00:00'),
            ('check_in', '<=', str(date_to) + ' 23:59:59'),
        ]
        attendances = self.env['hr.attendance'].search(att_domain)

        att_map = {}
        for att in attendances:
            emp_id = att.employee_id.id
            att_date = att.check_in.date()

            check_in_local = att.check_in and pytz.utc.localize(att.check_in).astimezone(local_tz)
            check_out_local = att.check_out and pytz.utc.localize(att.check_out).astimezone(local_tz)
            att_date = check_in_local.date() if check_in_local else att.check_in.date()

            if emp_id not in att_map:
                att_map[emp_id] = {}
            date_str = str(att_date)
            if date_str not in att_map[emp_id]:
                att_map[emp_id][date_str] = {
                    'check_in': check_in_local.strftime('%H:%M') if check_in_local else '',
                    'check_out': check_out_local.strftime('%H:%M') if check_out_local else '',
                }

        employee_data = []
        for idx, emp in enumerate(employees):
            row_dates = []
            for d in date_list:
                date_str = str(d)
                emp_att = att_map.get(emp.id, {}).get(date_str, {})
                row_dates.append({
                    'date': d.strftime('%d'),
                    'check_in': emp_att.get('check_in', ''),
                    'check_out': emp_att.get('check_out', ''),
                })
            employee_data.append({
                'sl': idx + 1,
                'name': emp.name,
                'department': emp.department_id.name if emp.department_id else '',
                'dates': row_dates,
            })

        return {
            'date_headers': [d.strftime('%-m/%-d/%Y') for d in date_list],
            'employees': employee_data,
        }