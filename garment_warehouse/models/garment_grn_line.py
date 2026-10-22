# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentGrnLine(models.Model):
    _name = 'garment.grn.line'
    _description = 'Garment GRN Line'
    _order = 'sequence'

    grn_id = fields.Many2one('garment.grn', string='GRN', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    material_id = fields.Many2one('garment.material', string='Material', required=True)
    received_qty = fields.Float(string='Received Quantity', required=True)
    accepted_qty = fields.Float(string='Accepted Quantity')
    rejected_qty = fields.Float(string='Rejected Quantity', compute='_compute_rejected_qty', store=True)
    quality_status = fields.Selection([
        ('pending', 'Pending Inspection'), ('on_hold', 'Quality Hold'), ('passed', 'Passed'),
        ('failed', 'Failed'), ('conditional', 'Conditional'),
    ], string='Quality Status', default='pending')
    hold_reason = fields.Char(string='Hold Reason', help='e.g. shade checking (SRS "Material Quality Hold System").')
    putaway_location_id = fields.Many2one('garment.location', string='Putaway Location',
                                           domain="[('warehouse_id', '=', parent.warehouse_id)]")

    @api.depends('received_qty', 'accepted_qty')
    def _compute_rejected_qty(self):
        for rec in self:
            rec.rejected_qty = max(0.0, (rec.received_qty or 0.0) - (rec.accepted_qty or 0.0))
