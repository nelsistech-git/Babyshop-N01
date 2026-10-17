# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import fields, models


class NelsisLcDocumentType(models.Model):
    """Configurable document checklist item.

    'Required by default' decides which documents are auto-loaded into an LC
    checklist.  The module ships these as NOT required: the mandatory list
    depends on the LC and the applicable rules and must be set by the company.
    """
    _name = 'nelsis.lc.document.type'
    _description = 'LC Document Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    scope = fields.Selection([
        ('lc', 'Per LC'),
        ('shipment', 'Per Shipment'),
    ], default='shipment', required=True)
    lc_type = fields.Selection([
        ('import', 'Import LC'),
        ('back_to_back', 'Back-to-Back LC'),
        ('export', 'Export LC (reference)'),
        ('other', 'Other'),
    ], string='Only for LC Type', help='Leave empty to apply to all LC types.')
    required_default = fields.Boolean('Required by Default',
                                      help='Auto-loaded as a required item by "Load Required Documents".')
    compliance_ref_id = fields.Many2one('nelsis.lc.compliance.ref', string='Compliance Reference')
    description = fields.Text()
    active = fields.Boolean(default=True)
