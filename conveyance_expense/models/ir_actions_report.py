import io
import logging

from odoo import models
from odoo.tools.pdf import PdfFileReader, merge_pdf

from .conveyance_sheet_line import _amount_to_words_bdt

_logger = logging.getLogger(__name__)

CONVEYANCE_REPORT_NAME = 'conveyance_expense.report_conveyance_sheet_template'
CUSTOM_EXPENSE_TEMPLATE = 'conveyance_expense.report_expense_sheet_custom'
PAPERFORMAT_XMLID = 'conveyance_expense.paperformat_expense_report'

# A4 at 150 dpi, used to place image attachments on a full page
_A4_PX = (1240, 1754)
_MARGIN_PX = 60
_IMAGE_MIMETYPES = ('image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp',
                    'image/webp', 'image/tiff')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    # ------------------------------------------------------------------ which report is it?
    @staticmethod
    def _conveyance_is_std_expense_report(report):
        """Odoo's standard "Expenses Report": the PDF report of hr.expense.sheet that ships with
        hr_expense. Detected by model + module prefix, so it does not depend on its XML ids."""
        return (report.model == 'hr.expense.sheet'
                and report.report_type == 'qweb-pdf'
                and (report.report_name or '').startswith('hr_expense.'))

    # ------------------------------------------------------------------ standard report -> our template
    def _render_qweb_html(self, report_ref, docids, data=None):
        report = self._get_report(report_ref)
        if self._conveyance_is_std_expense_report(report):
            self = self.with_context(conveyance_swap_template=report.report_name)
        return super(IrActionsReport, self)._render_qweb_html(report_ref, docids, data=data)

    def _render_template(self, template, values=None):
        if template and template == self.env.context.get('conveyance_swap_template'):
            template = CUSTOM_EXPENSE_TEMPLATE
        return super()._render_template(template, values=values)

    def get_paperformat(self):
        """Expenses Report page format: letterhead header/footer fit and the title sits 0.04 in under the header."""
        self.ensure_one()
        if self._conveyance_is_std_expense_report(self):
            paperformat = self.env.ref(PAPERFORMAT_XMLID, raise_if_not_found=False)
            if paperformat:
                return paperformat
        return super().get_paperformat()

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        if (report.report_name == CONVEYANCE_REPORT_NAME
                or self._conveyance_is_std_expense_report(report)):
            data['conveyance_rows'] = self._conveyance_rows
            data['bdt_words'] = _amount_to_words_bdt
        return data

    # ------------------------------------------------------------------ table rows of the Expenses Report
    @staticmethod
    def _conveyance_rows(sheet):
        """One row (Date, Reference No., Name, Purpose, Amount) per conveyance line of each expense; an expense without conveyance lines is shown
        as a single row. SL is sequential over the whole report."""
        def fmt(d):
            return d.strftime('%d-%b-%Y') if d else ''

        rows = []
        for expense in sheet.expense_line_ids:
            clines = expense.conveyance_sheet_id.line_ids
            if clines:
                for line in clines:
                    rows.append({
                        'date': fmt(line.date),
                        'reference': line.x_receipt_reference or '',
                        'name': line.category_id.name or expense.name or '',
                        'purpose': line.purpose or '',
                        'amount': line.total_amount,
                    })
            else:
                rows.append({
                    'date': fmt(expense.date),
                    'reference': '',
                    'name': expense.name or '',
                    'purpose': '',
                    'amount': expense.total_amount,
                })
        for number, row in enumerate(rows, start=1):
            row['sl'] = number
        return rows

    # ------------------------------------------------------------------ attachments appended to the PDF
    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """Conveyance Bill and Expenses Report: after the report pages of each record, append the PDF /
        image attachments linked to it. Every other report is untouched."""
        report = self._get_report(report_ref)
        if (not (report.report_name == CONVEYANCE_REPORT_NAME
                 or self._conveyance_is_std_expense_report(report))
                or not res_ids
                or self.env.context.get('conveyance_skip_attachments')):
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        # Render record by record so each record's attachments follow its own report pages
        pdf_parts = []
        for record in self.env[report.model].browse(res_ids):
            main_pdf, _fmt = super()._render_qweb_pdf(report_ref, res_ids=[record.id], data=data)
            pdf_parts.append(main_pdf)
            pdf_parts.extend(self._conveyance_attachment_pdfs(self._conveyance_attachments(record)))
        if len(pdf_parts) == 1:
            return pdf_parts[0], 'pdf'
        return merge_pdf(pdf_parts), 'pdf'

    # ------------------------------------------------------------------ collecting attachments
    def _conveyance_attachments(self, record):
        """Attachments of a conveyance sheet or an expense report, in print order, de-duplicated.
        Conveyance sheet: line receipts, sheet files, linked expense files.
        Expense report:   report files, then for every expense its files followed by the receipts and
                          files of its conveyance sheet."""
        Attachment = self.env['ir.attachment'].sudo()
        record = record.sudo()
        found = Attachment.browse()
        if record._name == 'conveyance.sheet':
            found |= self._conveyance_sheet_attachments(record)
            if record.expense_id:
                found |= self._plain_attachments('hr.expense', record.expense_id.id)
        elif record._name == 'hr.expense.sheet':
            found |= self._plain_attachments('hr.expense.sheet', record.id)
            for expense in record.expense_line_ids:
                found |= self._plain_attachments('hr.expense', expense.id)
                for csheet in expense.conveyance_sheet_ids:
                    found |= self._conveyance_sheet_attachments(csheet)
        ordered, seen = [], set()
        for att in found:
            if att.id not in seen:
                seen.add(att.id)
                ordered.append(att)
        return ordered

    def _plain_attachments(self, res_model, res_id):
        return self.env['ir.attachment'].sudo().search([
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
            ('res_field', '=', False),
        ], order='id')

    def _conveyance_sheet_attachments(self, sheet):
        Attachment = self.env['ir.attachment'].sudo()
        found = Attachment.browse()
        for line in sheet.sudo().line_ids:
            found |= Attachment.search([
                ('res_model', '=', 'conveyance.sheet.line'),
                ('res_id', '=', line.id),
                ('res_field', '=', 'x_receipt_attachment'),
            ], order='id')
            found |= line.attachment_ids
        found |= self._plain_attachments('conveyance.sheet', sheet.id)
        return found

    def _conveyance_attachment_pdfs(self, attachments):
        """PDF bytes (one entry per usable attachment). Unreadable files are skipped and logged so one
        bad file never blocks printing."""
        result = []
        for att in attachments:
            try:
                raw = att.raw
                if not raw:
                    continue
                mimetype = (att.mimetype or '').lower()
                if mimetype == 'application/pdf' or raw[:5] == b'%PDF-':
                    pdf = self._conveyance_checked_pdf(raw)
                elif mimetype in _IMAGE_MIMETYPES:
                    pdf = self._conveyance_image_to_pdf(raw)
                else:
                    continue
                if pdf:
                    result.append(pdf)
            except Exception:  # noqa: BLE001 - skip a broken file, keep printing
                _logger.warning('Conveyance report: skipped attachment %s (%s)',
                                att.id, att.name, exc_info=True)
        return result

    @staticmethod
    def _conveyance_checked_pdf(raw):
        """Return the PDF bytes if they can be read and are not password protected, else None."""
        reader = PdfFileReader(io.BytesIO(raw), strict=False)
        if reader.isEncrypted:
            _logger.warning('Conveyance report: encrypted PDF attachment skipped.')
            return None
        if not reader.getNumPages():
            return None
        return raw

    @staticmethod
    def _conveyance_image_to_pdf(raw):
        """Place an image on a white A4 page (scaled down to fit, never enlarged) and return it as PDF."""
        from PIL import Image, ImageOps  # Pillow ships with Odoo

        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGBA')
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        else:
            image = image.convert('RGB')
        max_w, max_h = _A4_PX[0] - 2 * _MARGIN_PX, _A4_PX[1] - 2 * _MARGIN_PX
        scale = min(max_w / image.width, max_h / image.height, 1.0)
        if scale < 1.0:
            image = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))),
                                 Image.LANCZOS)
        page = Image.new('RGB', _A4_PX, (255, 255, 255))
        page.paste(image, ((_A4_PX[0] - image.width) // 2, _MARGIN_PX))
        out = io.BytesIO()
        page.save(out, format='PDF', resolution=150.0)
        return out.getvalue()
