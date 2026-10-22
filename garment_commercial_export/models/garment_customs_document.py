# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Customs Documentation Management (SRS section 29) —
garment.customs.document. Bill of Entry (import), Bill of Export and
Customs Declaration, HS-Code and duty linked, tied to the shipment/export
reference."""
from odoo import api, fields, models, _


class GarmentCustomsDocument(models.Model):
    _name = 'garment.customs.document'
    _description = 'Garment Customs Document'
    _inherit = ['mail.thread']
    _order = 'submission_date desc'

    document_number = fields.Char(string='Document Number', copy=False, readonly=True, default=lambda s: _('New'))
    document_type = fields.Selection([
        ('bill_of_entry', 'Bill of Entry'), ('bill_of_export', 'Bill of Export'),
        ('customs_declaration', 'Customs Declaration'),
    ], string='Document Type', required=True, tracking=True)

    shipment_id = fields.Many2one('garment.shipment', string='Shipment')
    import_permission_id = fields.Many2one('garment.import.permission', string='Import Permission (IP)')
    hs_code_id = fields.Many2one('garment.hs.code', string='HS Code')
    customs_office = fields.Char(string='Customs Office / Station')

    declared_value = fields.Monetary(string='Declared Value', currency_field='currency_id')
    duty_amount = fields.Monetary(string='Duty Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    submission_date = fields.Date(string='Submission Date', default=fields.Date.context_today)
    clearance_date = fields.Date(string='Clearance Date')

    status = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('under_assessment', 'Under Assessment'),
        ('cleared', 'Cleared'), ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    file = fields.Binary(string='File', attachment=True)
    filename = fields.Char(string='Filename')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('document_number', _('New')) == _('New'):
                vals['document_number'] = self.env['ir.sequence'].next_by_code(
                    'garment.customs.document') or _('New')
        return super().create(vals_list)
