# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from datetime import timedelta

from odoo import api, fields, models


class GarmentHrDocument(models.Model):
    """Employee Document Management (SRS section 11) — garment.hr.document."""
    _name = 'garment.hr.document'
    _description = 'Garment Employee Document'
    _order = 'expiry_date'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    document_type = fields.Selection([
        ('nid', 'National ID'), ('birth_certificate', 'Birth Certificate'), ('education_certificate', 'Education Certificate'),
        ('experience_letter', 'Experience Letter'), ('appointment_letter', 'Appointment Letter'),
        ('medical_certificate', 'Medical Certificate'), ('photo', 'Photo'), ('other', 'Other'),
    ], string='Document Type', required=True)
    name = fields.Char(string='Document Name', required=True)
    file = fields.Binary(string='File', attachment=True, required=True)
    filename = fields.Char(string='Filename')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    is_expiring_soon = fields.Boolean(string='Expiring Soon', compute='_compute_is_expiring_soon', store=True)

    @api.depends('expiry_date')
    def _compute_is_expiring_soon(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expiring_soon = bool(rec.expiry_date and rec.expiry_date <= today + timedelta(days=30))
