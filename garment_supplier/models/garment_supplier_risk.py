# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentSupplierRisk(models.Model):
    """Supplier Risk Management (SRS section 29) — garment.supplier.risk."""
    _name = 'garment.supplier.risk'
    _description = 'Garment Supplier Risk'
    _inherit = ['mail.thread']
    _order = 'risk_level desc'

    supplier_id = fields.Many2one('garment.supplier', string='Supplier', required=True, ondelete='cascade')
    risk_factor = fields.Selection([
        ('late_delivery', 'Late Delivery'), ('quality_failure', 'Quality Failure'),
        ('price_increase', 'Price Increase'), ('document_expiry', 'Document Expiry'),
        ('low_capacity', 'Low Capacity'), ('compliance_failure', 'Compliance Failure'),
    ], string='Risk Factor', required=True)
    description = fields.Text(string='Description')
    risk_level = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], string='Risk Level', default='medium', tracking=True)
    identified_date = fields.Date(string='Identified Date', default=fields.Date.context_today)
    mitigation_plan = fields.Text(string='Mitigation Plan')
    status = fields.Selection([
        ('open', 'Open'), ('mitigating', 'Mitigating'), ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)

    def action_close(self):
        self.write({'status': 'closed'})
