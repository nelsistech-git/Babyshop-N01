# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Fabric Roll Management (SRS section 15) — garment.fabric.roll. Batch &
Lot Tracking and Roll Number Tracking (SRS sections 34-35) are folded in
here as fields rather than a separate model, since the official 8-model
DB design table lists only garment.fabric.roll for this area.
"""
from odoo import api, fields, models, _


class GarmentFabricRoll(models.Model):
    _name = 'garment.fabric.roll'
    _description = 'Garment Fabric Roll'
    _inherit = ['mail.thread']
    _order = 'received_date desc'

    roll_number = fields.Char(string='Roll Number', copy=False, readonly=True, default=lambda s: _('New'))
    batch_number = fields.Char(string='Batch Number')
    lot_number = fields.Char(string='Lot Number')
    material_id = fields.Many2one('garment.material', string='Fabric', required=True, domain="[('category', '=', 'fabric')]")
    color = fields.Char(string='Color')
    gsm = fields.Char(string='GSM')
    width = fields.Char(string='Width')
    meter_qty = fields.Float(string='Meter Quantity', required=True)
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    warehouse_id = fields.Many2one('garment.warehouse', string='Warehouse')
    location_id = fields.Many2one('garment.location', string='Location', domain="[('warehouse_id', '=', warehouse_id)]")
    received_date = fields.Date(string='Received Date', default=fields.Date.context_today)
    production_date = fields.Date(string='Production Date')
    expiry_date = fields.Date(string='Expiry Date')

    # Bangladesh Garment Warehouse Standards (SRS section 48 "Fabric Store
    # Requirements" — Shade, Relaxation Time, Inspection Status) and section
    # 12 "Fabric Shade Management".
    shade_number = fields.Char(string='Shade Number')
    shade_approval_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Shade Approval Status', default='pending')
    relaxation_time = fields.Float(string='Relaxation Time (Hours)',
                                    help='Fabric rest time before cutting, per Bangladesh knit-fabric practice.')
    inspection_status = fields.Selection([
        ('pending', 'Pending'), ('passed', 'Passed'), ('failed', 'Failed'), ('conditional', 'Conditional'),
    ], string='Inspection Status', default='pending', tracking=True)

    status = fields.Selection([
        ('in_stock', 'In Stock'), ('reserved', 'Reserved'), ('issued', 'Issued'),
        ('damaged', 'Damaged'), ('rejected', 'Rejected'), ('consumed', 'Consumed'),
    ], string='Status', default='in_stock', tracking=True)
    used_in_order = fields.Char(string='Used In Order')

    move_ids = fields.One2many('garment.stock.move', 'fabric_roll_id', string='Related Movements')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('roll_number', _('New')) == _('New'):
                vals['roll_number'] = self.env['ir.sequence'].next_by_code('garment.fabric.roll') or _('New')
        return super().create(vals_list)

    def action_mark_consumed(self):
        self.write({'status': 'consumed'})

    def action_mark_damaged(self):
        self.write({'status': 'damaged'})

    def action_mark_rejected(self):
        self.write({'status': 'rejected', 'inspection_status': 'failed'})
