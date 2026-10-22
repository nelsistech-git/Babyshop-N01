# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentDocumentAccessLog(models.Model):
    """Audit trail of every action on a document (SRS section 31 — Who
    Viewed / Edited / Downloaded / Approved, Date & Time). Rows are created
    exclusively from Python (see garment.document._log_access) — never
    editable by end users, only readable, so the trail stays trustworthy."""
    _name = 'garment.document.access.log'
    _description = 'Document Access Log'
    _order = 'create_date desc'

    document_id = fields.Many2one('garment.document', string='Document', required=True,
                                   ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda s: s.env.user)
    action = fields.Selection([
        ('view', 'Viewed'),
        ('download', 'Downloaded'),
        ('edit', 'Edited'),
        ('checkout', 'Checked Out'),
        ('checkin', 'Checked In'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
    ], string='Action', required=True)
    action_date = fields.Datetime(string='Date & Time', default=fields.Datetime.now, required=True)
    ip_address = fields.Char(string='IP Address')
    note = fields.Char(string='Note')
