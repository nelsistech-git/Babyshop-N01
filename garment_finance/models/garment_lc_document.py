# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentLcDocument(models.Model):
    """LC Document Management (SRS section 24) — garment.lc.document."""
    _name = 'garment.lc.document'
    _description = 'Garment LC Document'
    _order = 'sequence'

    lc_id = fields.Many2one('garment.lc', string='LC', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    document_type = fields.Selection([
        ('lc_copy', 'LC Copy'), ('amendment', 'Amendment Document'), ('invoice', 'Invoice'),
        ('packing_list', 'Packing List'), ('bl_copy', 'BL Copy'), ('insurance', 'Insurance Document'),
        ('certificate', 'Certificate'),
    ], string='Document Type', required=True)
    file = fields.Binary(string='File', attachment=True)
    filename = fields.Char(string='Filename')
    is_submitted = fields.Boolean(string='Submitted')
    submitted_date = fields.Date(string='Submitted Date')
