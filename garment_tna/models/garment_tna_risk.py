# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentTnaRisk(models.Model):
    """TNA Risk Management (SRS section 28) — garment.tna.risk."""
    _name = 'garment.tna.risk'
    _description = 'Garment TNA Risk'
    _inherit = ['mail.thread']
    _order = 'risk_level desc'

    tna_id = fields.Many2one('garment.tna', string='TNA', required=True, ondelete='cascade')
    risk_type = fields.Selection([
        ('material', 'Material Availability'), ('capacity', 'Production Capacity'),
        ('buyer_approval', 'Buyer Approval'), ('supplier', 'Supplier Performance'),
        ('logistics', 'Logistics/Shipping'), ('compliance', 'Compliance'), ('other', 'Other'),
    ], string='Risk Type', required=True)
    description = fields.Text(string='Description')
    probability_pct = fields.Float(string='Probability (%)')
    impact = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
    ], string='Impact', default='medium')
    risk_level = fields.Selection([
        ('normal', 'Normal'), ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Risk Level', default='medium', tracking=True)
    mitigation_plan = fields.Text(string='Mitigation Plan')
    status = fields.Selection([
        ('open', 'Open'), ('mitigating', 'Mitigating'), ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)

    def action_close(self):
        self.write({'status': 'closed'})
