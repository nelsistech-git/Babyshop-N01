# -*- coding: utf-8 -*-
import io
import base64
import xlsxwriter
from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class VisitReportPDF(models.AbstractModel):
    _name = 'report.front_office_management.report_all_visits_template'
    _description = 'Visitor Report PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        # docids contains the wizard ID — fetch visits directly from the wizard
        wizards = self.env['fo.visit.report.wizard'].browse(docids)
        wizard = wizards[0] if wizards else self.env['fo.visit.report.wizard']
        visits = wizard._get_visits() if wizard else self.env['fo.visit']
        return {
            'doc_ids': docids,
            'doc_model': 'fo.visit.report.wizard',
            'docs': visits,
            'date_from': fields.Date.to_string(wizard.date_from) if wizard and wizard.date_from else False,
            'date_to': fields.Date.to_string(wizard.date_to) if wizard and wizard.date_to else False,
        }


class VisitReportWizard(models.TransientModel):
    _name = 'fo.visit.report.wizard'
    _description = 'Visitor Report Wizard'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    def _get_visits(self):
        # Build domain based on selected date range.
        # Draft records have no check_in_date (null), so we use OR to include them.
        domain = []
        if self.date_from and self.date_to:
            domain = [
                '|',
                ('check_in_date', '=', False),
                '&',
                ('check_in_date', '>=', self.date_from),
                ('check_in_date', '<=', self.date_to),
            ]
        elif self.date_from:
            domain = [
                '|',
                ('check_in_date', '=', False),
                ('check_in_date', '>=', self.date_from),
            ]
        elif self.date_to:
            domain = [
                '|',
                ('check_in_date', '=', False),
                ('check_in_date', '<=', self.date_to),
            ]
        visits = self.env['fo.visit'].search(domain, order='check_in_date asc')
        return visits

    def action_print_pdf(self):
        visits = self._get_visits()
        # Show warning if no records found for the selected date range
        if not visits:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Records Found',
                    'message': 'No visitor records found for the selected date range.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        # Pass the wizard itself as docids so _get_report_values can fetch visits directly
        return self.env.ref(
            'front_office_management.action_report_all_visits'
        ).report_action(self)

    def action_export_excel(self):
        visits = self._get_visits()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Visitor Report')

        # Header row style
        header_style = workbook.add_format({
            'bold': True,
            'bg_color': '#6C7E7F',
            'font_color': '#FFFFFF',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        # Data cell style
        cell_style = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })
        # Title style
        title_style = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
        })

        # Title row
        sheet.merge_range('A1:G1', 'Visitor Report', title_style)
        sheet.set_row(0, 25)

        # Date range row
        date_info = ''
        if self.date_from or self.date_to:
            date_info = 'Period: %s to %s' % (
                fields.Date.to_string(self.date_from) if self.date_from else '',
                fields.Date.to_string(self.date_to) if self.date_to else '',
            )
        sheet.merge_range('A2:G2', date_info, workbook.add_format({'align': 'center'}))

        # Column headers and widths
        headers = ['Date', 'Visitor', 'Purpose of Visit', 'Contact No.', 'Meeting With', 'State', 'Duration']
        col_widths = [15, 20, 25, 18, 20, 15, 15]
        for col, (header, width) in enumerate(zip(headers, col_widths)):
            sheet.write(3, col, header, header_style)
            sheet.set_column(col, col, width)
        sheet.set_row(3, 20)

        # Write visit data rows
        row = 4
        for visit in visits:
            date_val = visit.check_in_date.strftime('%d-%m-%Y') if visit.check_in_date else '-'
            purpose = ', '.join(visit.reason_ids.mapped('name')) if visit.reason_ids else '-'
            state_map = {
                'draft': 'Draft',
                'check_in': 'Checked In',
                'check_out': 'Checked Out',
                'cancel': 'Cancelled',
            }
            state = state_map.get(visit.state, '-')

            # Calculate visit duration
            if visit.check_in_date and visit.check_out_date:
                delta = visit.check_out_date - visit.check_in_date
                total_minutes = int(delta.total_seconds() // 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                duration = '%dh %dm' % (hours, minutes)
            elif visit.check_in_date and not visit.check_out_date:
                duration = 'In Progress'
            else:
                duration = '-'

            sheet.write(row, 0, date_val, cell_style)
            sheet.write(row, 1, visit.visitor_id.name or '-', cell_style)
            sheet.write(row, 2, purpose, cell_style)
            sheet.write(row, 3, visit.phone or '-', cell_style)
            sheet.write(row, 4, visit.employee_id.name or '-', cell_style)
            sheet.write(row, 5, state, cell_style)
            sheet.write(row, 6, duration, cell_style)
            row += 1

        workbook.close()
        output.seek(0)

        # Encode as base64 and create an attachment for download
        xlsx_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': 'Visitor_Report.xlsx',
            'type': 'binary',
            'datas': xlsx_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'new',
        }
