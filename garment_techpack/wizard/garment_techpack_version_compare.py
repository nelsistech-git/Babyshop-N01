# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Version Comparison (SRS section 19) — side-by-side comparison between two
Tech Pack revisions. This compares the descriptive Revision Information
recorded on each garment.techpack.version (Technical/Material/Visual change
classification is only as granular as the linked Tech Change Requests, since
per-field historical snapshots of measurements/artwork/BOM are not stored by
the Tech Pack data model — an intentional scope decision documented in
IMPLEMENTATION_NOTES.md)."""

from odoo import api, fields, models, _


class GarmentTechpackVersionCompare(models.TransientModel):
    _name = 'garment.techpack.version.compare'
    _description = 'Garment Tech Pack Version Comparison Wizard'

    techpack_id = fields.Many2one('garment.techpack', string='Tech Pack', required=True)
    version_from_id = fields.Many2one('garment.techpack.version', string='Version (Older)', required=True,
                                       domain="[('techpack_id', '=', techpack_id)]")
    version_to_id = fields.Many2one('garment.techpack.version', string='Version (Newer)', required=True,
                                     domain="[('techpack_id', '=', techpack_id)]")
    comparison_result = fields.Html(string='Comparison Result', readonly=True)

    def action_compare(self):
        self.ensure_one()
        a, b = self.version_from_id, self.version_to_id

        def row(label, val_a, val_b):
            status = 'Modified' if val_a != val_b else 'Unchanged'
            return '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                label, val_a or '-', val_b or '-', status)

        fields_to_compare = [
            ('Revision Type', dict(a._fields['revision_type'].selection).get(a.revision_type),
             dict(b._fields['revision_type'].selection).get(b.revision_type)),
            ('Impact Level', dict(a._fields['impact_level'].selection).get(a.impact_level),
             dict(b._fields['impact_level'].selection).get(b.impact_level)),
            ('Approval Status', dict(a._fields['approval_status'].selection).get(a.approval_status),
             dict(b._fields['approval_status'].selection).get(b.approval_status)),
            ('Buyer Reference', a.buyer_reference, b.buyer_reference),
            ('Effective Date', a.effective_date, b.effective_date),
            ('Change Reason', a.change_reason, b.change_reason),
        ]
        rows = ''.join(row(*f) for f in fields_to_compare)

        changes = self.env['garment.tech.change'].search([
            ('techpack_id', '=', self.techpack_id.id),
            ('request_date', '>=', a.revision_date or a.create_date),
            ('request_date', '<=', b.revision_date or b.create_date),
        ])
        change_rows = ''.join(
            '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                c.change_number, c.revision_type, c.request_date, c.change_reason or '-')
            for c in changes
        ) or '<tr><td colspan="4">No Tech Change Requests recorded between these two versions.</td></tr>'

        self.comparison_result = _(
            '<h5>Version %s (Responsible: %s, Changed: %s) vs Version %s (Responsible: %s, Changed: %s)</h5>'
            '<table class="table table-sm table-bordered">'
            '<thead><tr><th>Field</th><th>%s</th><th>%s</th><th>Status</th></tr></thead>'
            '<tbody>%s</tbody></table>'
            '<h5>Change Requests In Between</h5>'
            '<table class="table table-sm table-bordered">'
            '<thead><tr><th>Change #</th><th>Type</th><th>Date</th><th>Reason</th></tr></thead>'
            '<tbody>%s</tbody></table>'
        ) % (a.version_number, a.changed_by_id.name or '-', a.revision_date or '-',
             b.version_number, b.changed_by_id.name or '-', b.revision_date or '-',
             a.version_number, b.version_number, rows, change_rows)

        return {
            'name': _('Compare Tech Pack Versions'), 'type': 'ir.actions.act_window',
            'res_model': 'garment.techpack.version.compare', 'res_id': self.id,
            'view_mode': 'form', 'target': 'new',
        }
