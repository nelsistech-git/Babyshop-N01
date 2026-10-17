# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import fields, models


class NelsisCommercialDocumentType(models.Model):
    _name = 'nelsis.commercial.document.type'
    _description = 'Commercial Document Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    description = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Document type code must be unique.'),
    ]
