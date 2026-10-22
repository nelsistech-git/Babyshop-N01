# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentLocation(models.Model):
    """Warehouse Location Management (SRS section 6) — garment.location.
    Zone -> Rack -> Shelf -> Bin hierarchy under one warehouse, kept as a
    single model with hierarchy fields rather than four separate models."""
    _name = 'garment.location'
    _description = 'Garment Warehouse Location'
    _order = 'warehouse_id, zone, rack, shelf, bin'

    warehouse_id = fields.Many2one('garment.warehouse', string='Warehouse', required=True, ondelete='cascade')
    zone = fields.Char(string='Zone')
    rack = fields.Char(string='Rack')
    shelf = fields.Char(string='Shelf')
    bin = fields.Char(string='Bin')
    location_code = fields.Char(string='Location Code', compute='_compute_location_code', store=True)
    location_type = fields.Selection([
        ('zone', 'Zone'), ('rack', 'Rack'), ('shelf', 'Shelf'), ('bin', 'Bin'),
    ], string='Location Level', default='bin',
       help='Which level of the Zone -> Rack -> Shelf -> Bin hierarchy this record represents.')
    location_purpose = fields.Selection([
        ('storage', 'Storage'), ('gate', 'Gate / Dock (RFID Gate Tracking)'),
        ('quality_hold', 'Quality Hold Area'), ('staging', 'Staging / Dispatch'),
    ], string='Purpose', default='storage')
    capacity = fields.Float(string='Capacity')
    capacity_uom = fields.Char(string='Capacity UoM')
    occupied_qty = fields.Float(string='Occupied Qty (approx.)', compute='_compute_occupied_qty',
                                 help='Net quantity currently posted to this location from the stock ledger. '
                                      'Bins holding more than one material/UoM are summed as raw quantity — '
                                      'an operational indicator, not an exact multi-UoM figure.')
    utilization_percent = fields.Float(string='Utilization %', compute='_compute_occupied_qty')
    active = fields.Boolean(default=True)

    @api.depends('warehouse_id.code', 'zone', 'rack', 'shelf', 'bin')
    def _compute_location_code(self):
        for rec in self:
            parts = [rec.warehouse_id.code] + [p for p in (rec.zone, rec.rack, rec.shelf, rec.bin) if p]
            rec.location_code = '-'.join(filter(None, parts))

    def _compute_occupied_qty(self):
        in_types = ('receipt', 'return', 'adjustment_in', 'transfer_in')
        out_types = ('issue', 'transfer_out', 'adjustment_out')
        for rec in self:
            if not rec.id:
                rec.occupied_qty = 0.0
                rec.utilization_percent = 0.0
                continue
            moves = self.env['garment.stock.move'].search([
                ('location_id', '=', rec.id), ('state', '=', 'done'),
            ])
            qty = sum(m.quantity for m in moves if m.move_type in in_types)
            qty -= sum(m.quantity for m in moves if m.move_type in out_types)
            rec.occupied_qty = qty
            rec.utilization_percent = (qty / rec.capacity * 100.0) if rec.capacity else 0.0
