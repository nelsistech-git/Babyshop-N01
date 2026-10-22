# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentWipTracking(models.Model):
    """Work In Progress tracking by department stage. See Shop Floor SRS
    s.27 (WIP Management)."""
    _name = 'garment.wip.tracking'
    _description = 'Garment WIP Tracking'
    _order = 'as_of_date desc'

    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, ondelete='cascade')
    department = fields.Selection([
        ('cutting', 'Cutting WIP'), ('sewing', 'Sewing WIP'),
        ('washing', 'Washing WIP'), ('finishing', 'Finishing WIP'), ('packing', 'Packing WIP'),
    ], string='Department', required=True)
    as_of_date = fields.Date(string='As Of Date', default=fields.Date.context_today, required=True)

    received_qty = fields.Float(string='Received Quantity (PCS)')
    completed_qty = fields.Float(string='Completed Quantity (PCS)')
    wip_qty = fields.Float(string='WIP Quantity (PCS)', compute='_compute_wip', store=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('received_qty', 'completed_qty')
    def _compute_wip(self):
        for rec in self:
            rec.wip_qty = (rec.received_qty or 0.0) - (rec.completed_qty or 0.0)
