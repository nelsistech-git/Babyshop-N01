# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentMaterialAlternative(models.Model):
    """Alternative Material Management (SRS section 14) —
    garment.material.alternative."""
    _name = 'garment.material.alternative'
    _description = 'Garment Alternative Material'
    _order = 'sequence'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    main_material = fields.Char(string='Main Material', required=True)
    alternative_material = fields.Char(string='Alternative Material', required=True)
    reason = fields.Text(string='Reason')
    cost_difference = fields.Monetary(string='Cost Difference', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='bom_id.currency_id', store=True)
    buyer_approval_required = fields.Boolean(string='Buyer Approval Required', default=True)
    buyer_approved = fields.Boolean(string='Buyer Approved')
    approval_status = fields.Selection([
        ('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Approval Status', default='draft')
    effective_date = fields.Date(string='Effective Date')
