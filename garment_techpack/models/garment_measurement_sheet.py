# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models, _


class GarmentMeasurementSheet(models.Model):
    """Measurement Integration (SRS section 15) — garment.measurement.sheet.
    Connects the Tech Pack directly with the Style Library, its Measurement
    Chart, Size Specification (Size Set) and Pattern, and supports:
    Import Measurement Chart, Compare Revision, Track Tolerance,
    Approve Measurements, Generate Measurement Sheet."""
    _name = 'garment.measurement.sheet'
    _description = 'Garment Tech Pack Measurement Sheet'
    _order = 'sequence'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    measurement_chart_id = fields.Many2one('garment.measurement.chart', string='Measurement Chart',
                                            domain="[('style_id', '=', style_id)]")
    style_id = fields.Many2one('garment.style', string='Style', related='techpack_id.style_id', store=True)
    size_set_id = fields.Many2one('garment.size.set', string='Size Specification (Size Set)')
    pattern_id = fields.Many2one('garment.pattern', string='Pattern', domain="[('style_id', '=', style_id)]")
    imported_date = fields.Date(string='Imported Date', default=fields.Date.context_today)
    tolerance_tracked = fields.Boolean(string='Tolerance Tracked', default=True)
    status = fields.Selection([
        ('draft', 'Draft'), ('under_review', 'Under Review'), ('approved', 'Approved'),
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')

    # Version Comparison support (SRS sections 15 "Compare Revision" & 19)
    compare_sheet_id = fields.Many2one('garment.measurement.sheet', string='Compare Against',
                                        domain="[('style_id', '=', style_id), ('id', '!=', id)]")
    comparison_result = fields.Text(string='Comparison Result', readonly=True)

    def action_import_from_style(self):
        """Import Measurement Chart action (SRS section 15 feature list)."""
        for rec in self:
            if not rec.measurement_chart_id:
                chart = self.env['garment.measurement.chart'].search(
                    [('style_id', '=', rec.style_id.id)], limit=1, order='chart_number desc')
                if chart:
                    rec.measurement_chart_id = chart.id
                else:
                    rec.notes = _('No measurement chart found for style %s.') % rec.style_id.style_name
        return True

    def action_submit_review(self):
        self.write({'status': 'under_review'})

    def action_approve(self):
        """Approve Measurements (SRS section 15 feature list)."""
        self.write({'status': 'approved'})

    def action_compare_revision(self):
        """Compare Revision (SRS section 15 / 19): tolerance-point diff between
        this sheet's measurement chart and the one on `compare_sheet_id`."""
        for rec in self:
            if not rec.compare_sheet_id:
                rec.comparison_result = _('Select a measurement sheet to compare against first.')
                continue
            chart_a = rec.measurement_chart_id
            chart_b = rec.compare_sheet_id.measurement_chart_id
            if not chart_a or not chart_b:
                rec.comparison_result = _('Both measurement sheets need a linked Measurement Chart to compare.')
                continue
            points_a = {line.description: line for line in chart_a.line_ids}
            points_b = {line.description: line for line in chart_b.line_ids}
            added = sorted(set(points_a) - set(points_b))
            removed = sorted(set(points_b) - set(points_a))
            modified = []
            for key in sorted(set(points_a) & set(points_b)):
                a, b = points_a[key], points_b[key]
                if (a.tolerance_plus, a.tolerance_minus) != (b.tolerance_plus, b.tolerance_minus):
                    modified.append('%s: tolerance +%s/-%s -> +%s/-%s' % (
                        key, b.tolerance_plus, b.tolerance_minus, a.tolerance_plus, a.tolerance_minus))
            lines = ['Comparing %s (%s) vs %s (%s)' % (
                chart_a.chart_number, chart_a.version, chart_b.chart_number, chart_b.version)]
            lines.append('Added points: %s' % (', '.join(added) if added else 'None'))
            lines.append('Removed points: %s' % (', '.join(removed) if removed else 'None'))
            lines.append('Modified tolerance: %s' % ('; '.join(modified) if modified else 'None'))
            rec.comparison_result = '\n'.join(lines)
        return True
