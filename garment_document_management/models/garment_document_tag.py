# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentDocumentTag(models.Model):
    """Free tagging for documents (SRS section 11 — search by Keyword)."""
    _name = 'garment.document.tag'
    _description = 'Document Tag'
    _order = 'name'

    name = fields.Char(string='Tag', required=True)
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A tag with this name already exists!'),
    ]
