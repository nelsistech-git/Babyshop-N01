# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with the AI Tech Pack
Assistant (SRS section 25): automatic tech pack reading, missing
information detection, specification validation and historical
comparison. Every capability degrades gracefully to a safe, transparent
rule-based fallback when no external AI provider or parsing library is
available — never blocks the workflow, and extracted data is always
flagged for mandatory human verification before use.
"""
import base64
import io
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineTechpackExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # 25.1 Automatic Tech Pack Reading
    # ------------------------------------------------------------------
    def extract_techpack_data(self, attachment):
        """Best-effort text extraction from a buyer-provided file
        (garment.tech.attachment). Returns a text report; never raises."""
        if not attachment.file:
            return 'No file attached.'

        raw_text = ''
        try:
            data = base64.b64decode(attachment.file)
            if attachment.source == 'pdf' or (attachment.filename or '').lower().endswith('.pdf'):
                raw_text = self._extract_pdf_text(data)
            else:
                raw_text = ''
        except Exception as exc:  # noqa: BLE001 - never break the UI on a bad file
            _logger.warning('Garment AI Engine: tech pack extraction failed (%s).', exc)
            raw_text = ''

        if not raw_text:
            return ('Automatic text extraction was not available for this file type/content. '
                    'Please enter the technical data manually — an AI-assisted OCR/parsing library '
                    '(e.g. pdfplumber) can be added later for richer extraction.')

        found = self._heuristic_field_scan(raw_text)
        lines = ['AI extraction (requires human verification before use):']
        for label, value in found.items():
            lines.append('- %s: %s' % (label, value if value else 'Not found — please fill in manually.'))
        return '\n'.join(lines)

    def _extract_pdf_text(self, data):
        try:
            import pypdf  # type: ignore
        except ImportError:
            try:
                import PyPDF2 as pypdf  # type: ignore
            except ImportError:
                return ''
        try:
            reader = pypdf.PdfReader(io.BytesIO(data))
            return '\n'.join((page.extract_text() or '') for page in reader.pages)
        except Exception:  # noqa: BLE001
            return ''

    def _heuristic_field_scan(self, text):
        import re
        patterns = {
            'Style Number': r'(?i)style\s*(?:no\.?|number)\s*[:\-]?\s*([A-Za-z0-9\-\/]+)',
            'Fabric Composition': r'(?i)(?:fabric|composition)\s*[:\-]?\s*([0-9]{1,3}%\s*[A-Za-z\s\/]+)',
            'GSM': r'(?i)gsm\s*[:\-]?\s*([0-9]{2,4})',
            'Color': r'(?i)colou?r\s*[:\-]?\s*([A-Za-z\s]+)',
            'Size Range': r'(?i)size\s*range\s*[:\-]?\s*([A-Za-z0-9\-\/,\s]+)',
        }
        results = {}
        for label, pattern in patterns.items():
            match = re.search(pattern, text)
            results[label] = match.group(1).strip() if match else None
        return results

    # ------------------------------------------------------------------
    # 25.2 Missing Information Detection
    # ------------------------------------------------------------------
    def detect_missing_techpack_fields(self, techpack):
        missing = []
        if not techpack.measurement_sheet_ids:
            missing.append('Missing measurements (no measurement sheet linked)')
        if not techpack.artwork_ids:
            missing.append('Missing artwork')
        if not techpack.construction_detail_ids:
            missing.append('Missing construction details')
        if not techpack.style_id.fabric_line_ids:
            missing.append('Missing fabric information on the linked Style')
        if not techpack.packaging_spec_ids:
            missing.append('Missing packaging specification')
        if not techpack.label_spec_ids:
            missing.append('Missing label specification')
        if not any(cert for cert in (
                techpack.buyer_id.cert_bsci, techpack.buyer_id.cert_sedex, techpack.buyer_id.cert_wrap,
                techpack.buyer_id.cert_gots, techpack.buyer_id.cert_oeko_tex)):
            missing.append('No compliance certificates on file for this buyer — verify compliance requirements')
        return '\n'.join('- %s' % m for m in missing) if missing else 'No missing mandatory information detected.'

    # ------------------------------------------------------------------
    # 25.3 Specification Validation
    # ------------------------------------------------------------------
    def validate_techpack_specification(self, techpack):
        issues = []
        for sheet in techpack.measurement_sheet_ids:
            if sheet.measurement_chart_id:
                for line in sheet.measurement_chart_id.line_ids:
                    if not line.tolerance_plus and not line.tolerance_minus:
                        issues.append('Measurement point "%s" has no tolerance defined' % line.description)
        for artwork in techpack.artwork_ids:
            if artwork.artwork_type == 'print' and not artwork.print_method:
                issues.append('Print artwork "%s" is missing a print method' % artwork.artwork_number)
            if artwork.artwork_type == 'embroidery' and not artwork.stitch_count:
                issues.append('Embroidery artwork "%s" is missing stitch count' % artwork.artwork_number)
        fabric_lines = techpack.style_id.fabric_line_ids
        if fabric_lines and any(not f.gsm for f in fabric_lines):
            issues.append('One or more fabric lines on the Style are missing GSM')
        return '\n'.join('- %s' % i for i in issues) if issues else 'No specification inconsistencies detected.'

    # ------------------------------------------------------------------
    # 25.4 Historical Comparison
    # ------------------------------------------------------------------
    def find_similar_techpacks(self, techpack, limit=5):
        candidates = self.env['garment.techpack'].search([
            ('id', '!=', techpack.id),
            ('style_category_id', '=', techpack.style_category_id.id),
        ], limit=50) if techpack.style_category_id else self.env['garment.techpack'].search(
            [('id', '!=', techpack.id)], limit=50)

        scored = []
        for candidate in candidates:
            score = 0
            if candidate.buyer_id == techpack.buyer_id:
                score += 20
            if candidate.construction_method and candidate.construction_method == techpack.construction_method:
                score += 25
            if candidate.fit_type and candidate.fit_type == techpack.fit_type:
                score += 15
            if candidate.garment_type and candidate.garment_type == techpack.garment_type:
                score += 20
            if score > 0:
                scored.append((score, candidate))
        scored.sort(key=lambda t: t[0], reverse=True)
        top = scored[:limit]
        similar = self.env['garment.techpack'].browse([c.id for _s, c in top])
        insight = ('Found %d comparable historical tech pack(s) by buyer/construction/fit match.' % len(top)
                    if top else 'No closely comparable historical tech packs found yet.')
        return similar, insight
