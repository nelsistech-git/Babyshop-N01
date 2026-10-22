# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentDocumentVersion(models.Model):
    """Document version history (SRS section 12) — one immutable snapshot
    per check-in / file update, oldest first by sequence."""
    _name = 'garment.document.version'
    _description = 'Document Version'
    _order = 'document_id, sequence desc'

    document_id = fields.Many2one('garment.document', string='Document', required=True,
                                   ondelete='cascade', index=True)
    sequence = fields.Integer(string='Version No.', default=1)
    version_label = fields.Char(string='Version', required=True)
    file = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    file_size = fields.Integer(string='File Size (bytes)', compute='_compute_file_size', store=True)
    created_by_id = fields.Many2one('res.users', string='Created By', readonly=True)
    create_date = fields.Datetime(string='Created On', readonly=True)
    note = fields.Char(string='Change Note')
    is_current = fields.Boolean(string='Current Version', compute='_compute_is_current', store=True)

    @api.depends('file')
    def _compute_file_size(self):
        for rec in self:
            rec.file_size = len(rec.file) if rec.file else 0

    @api.depends('sequence', 'document_id.version_ids.sequence')
    def _compute_is_current(self):
        for rec in self:
            latest = rec.document_id.version_ids.sorted('sequence', reverse=True)[:1]
            rec.is_current = rec.id == latest.id if latest else False

    def action_restore(self):
        """Restore this historic version's file as the document's current
        file (creates a new version rather than deleting history)."""
        for rec in self:
            rec.document_id.with_context(skip_lock_check=True).write({
                'file': rec.file, 'file_name': rec.file_name,
            })
