# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentStyleDocumentTag(models.Model):
    """Self-contained tag master for Digital Asset Management (SRS section 14 —
    'Tags'). Kept local to this module rather than depending on Odoo's
    standard 'crm' app (which this suite does not otherwise use)."""
    _name = 'garment.style.document.tag'
    _description = 'Garment Style Document Tag'
    _order = 'name'

    name = fields.Char(required=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A tag with this name already exists!'),
    ]
