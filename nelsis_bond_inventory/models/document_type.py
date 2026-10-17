# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from odoo import fields, models


class BondDocumentType(models.Model):
    _name = 'bond.inventory.document.type'
    _description = 'Bond Receipt Document Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    required_for_bonded = fields.Boolean(
        string='Required for Bonded Receipts',
        help='Configure only after the requirement has been confirmed by a qualified customs professional.')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'The document type code must be unique.'),
    ]
