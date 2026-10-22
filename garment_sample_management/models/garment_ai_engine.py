# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Extends garment.ai.engine (garment_buyer_crm) with the AI Sample Assistant
(SRS section 19 / 33): image comparison, measurement verification against
the Tech Pack / Style measurement chart, and approval-probability
prediction. As with the other AI extensions, everything degrades to a
transparent, deterministic fallback when no external provider or image
library is configured — it never blocks the sample workflow.
"""
import base64
import io
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class GarmentAIEngineSampleExtension(models.AbstractModel):
    _inherit = 'garment.ai.engine'

    # ------------------------------------------------------------------
    # AI Image Comparison
    # ------------------------------------------------------------------
    def compare_sample_images(self, sample):
        if not sample.approved_image or not sample.developed_sample_image:
            return ('Image comparison needs both an Approved Reference Image and a Developed '
                    'Sample Image — please upload both.')
        try:
            from PIL import Image
        except ImportError:
            return ('Image comparison library not available on this server. Please compare the '
                    'Approved Reference Image and Developed Sample Image visually.')
        try:
            img_a = Image.open(io.BytesIO(base64.b64decode(sample.approved_image))).convert('RGB')
            img_b = Image.open(io.BytesIO(base64.b64decode(sample.developed_sample_image))).convert('RGB')
            size = (100, 100)
            img_a = img_a.resize(size)
            img_b = img_b.resize(size)
            avg_a = self._average_color(img_a)
            avg_b = self._average_color(img_b)
            color_diff = sum(abs(a - b) for a, b in zip(avg_a, avg_b)) / 3.0
            if color_diff < 8:
                verdict = 'Color match looks close.'
            elif color_diff < 25:
                verdict = 'Minor color difference detected — visually verify against Pantone standard.'
            else:
                verdict = 'Significant color difference detected — flag for review.'
            return ('AI Image Comparison (heuristic average-color check, not shape/construction '
                    'analysis): %s (delta=%.1f/255).') % (verdict, color_diff)
        except Exception as exc:  # noqa: BLE001
            _logger.warning('Garment AI Engine: sample image comparison failed (%s).', exc)
            return 'Image comparison could not be completed automatically — please compare visually.'

    def _average_color(self, img):
        pixels = list(img.getdata())
        n = len(pixels)
        r = sum(p[0] for p in pixels) / n
        g = sum(p[1] for p in pixels) / n
        b = sum(p[2] for p in pixels) / n
        return (r, g, b)

    # ------------------------------------------------------------------
    # AI Measurement Verification
    # ------------------------------------------------------------------
    def verify_sample_measurements(self, sample):
        latest_qc = self.env['garment.sample.qc'].search(
            [('sample_id', '=', sample.id)], order='qc_date desc', limit=1)
        if not latest_qc:
            return 'No Sample QC record found yet — record measurements on a Sample QC to enable verification.'

        chart = self.env['garment.measurement.chart'].search(
            [('style_id', '=', sample.style_id.id)], limit=1, order='chart_number desc')
        if not chart:
            return 'No measurement chart found for this style — cannot verify tolerance.'

        point_map = {
            'Body Length': latest_qc.measured_body_length, 'Chest': latest_qc.measured_chest,
            'Sleeve Length': latest_qc.measured_sleeve_length, 'Collar': latest_qc.measured_collar,
            'Waist': latest_qc.measured_waist, 'Hip': latest_qc.measured_hip,
        }
        issues = []
        for line in chart.line_ids:
            for label, measured in point_map.items():
                if label.lower() in (line.description or '').lower() and measured:
                    low = line.base_size_value - (line.tolerance_minus or 0)
                    high = line.base_size_value + (line.tolerance_plus or 0)
                    if not (low <= measured <= high):
                        issues.append('%s: measured %.2f is outside tolerance [%.2f, %.2f]' % (
                            label, measured, low, high))
        if issues:
            return 'AI Measurement Verification — deviations found:\n' + '\n'.join('- %s' % i for i in issues)
        return 'AI Measurement Verification — all recorded measurements are within tolerance.'

    # ------------------------------------------------------------------
    # AI Approval Prediction
    # ------------------------------------------------------------------
    def predict_sample_approval(self, sample):
        probability = 50.0
        notes = []

        history = self.env['garment.sample'].search([
            ('buyer_id', '=', sample.buyer_id.id),
            ('id', '!=', sample.id),
            ('status', 'in', ('approved', 'bulk_production', 'rejected')),
        ], limit=50)
        if history:
            approved = len(history.filtered(lambda s: s.status in ('approved', 'bulk_production')))
            rate = approved / len(history) * 100.0
            probability = rate
            notes.append('Buyer historical approval rate: %.0f%% (%d/%d prior samples).' % (
                rate, approved, len(history)))
        else:
            notes.append('No prior sample history for this buyer — using baseline 50% estimate.')

        open_comments = sample.comment_ids.filtered(lambda c: c.completion_status != 'completed')
        if open_comments:
            probability -= min(20, len(open_comments) * 5)
            notes.append('%d unresolved buyer comment(s) reduce approval likelihood.' % len(open_comments))

        if sample.ai_measurement_note and 'deviations found' in (sample.ai_measurement_note or ''):
            probability -= 15
            notes.append('Measurement deviations detected — likely objection point.')

        if sample.revision_ids:
            probability -= min(15, len(sample.revision_ids) * 5)
            notes.append('%d revision(s) already made on this sample.' % len(sample.revision_ids))

        probability = max(0.0, min(100.0, probability))
        return probability, '\n'.join('- %s' % n for n in notes)

    # ------------------------------------------------------------------
    # AI Sample Similarity Search (SRS section 33)
    # ------------------------------------------------------------------
    def find_similar_samples(self, sample):
        """Heuristic similarity search: same style category / buyer / sample type, most recent
        first. Returns (recordset of similar samples, human-readable notes including previous
        approval history and comments) since no image-embedding library is guaranteed on this
        server — this mirrors the same transparent-fallback approach as the other AI helpers."""
        domain = [('id', '!=', sample.id)]
        if sample.style_category_id:
            domain.append(('style_category_id', '=', sample.style_category_id.id))
        similar = self.env['garment.sample'].search(domain, order='create_date desc', limit=10)

        if not similar and sample.buyer_id:
            similar = self.env['garment.sample'].search(
                [('id', '!=', sample.id), ('buyer_id', '=', sample.buyer_id.id)],
                order='create_date desc', limit=10)

        notes = []
        if not similar:
            notes.append('No similar prior samples found (matched by product category, then buyer).')
        else:
            notes.append('Found %d similar prior sample(s), most recent first:' % len(similar))
            for s in similar:
                approval_note = dict(s._fields['status'].selection).get(s.status, s.status)
                comment_count = len(s.comment_ids)
                notes.append('- %s (Style: %s, Buyer: %s) — Status: %s, Buyer comments: %d' % (
                    s.sample_number, s.style_id.display_name, s.buyer_id.name, approval_note, comment_count))
        return similar, '\n'.join(notes)
