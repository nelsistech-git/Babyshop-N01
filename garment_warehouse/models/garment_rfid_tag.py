# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentRfidTag(models.Model):
    """RFID Tracking + RFID Automation + RFID Gate Management (SRS
    sections 14, 44-45) — garment.rfid.tag."""
    _name = 'garment.rfid.tag'
    _description = 'Garment RFID Tag'
    _order = 'assigned_date desc'

    tag_id = fields.Char(string='RFID Tag ID', required=True, copy=False)
    material_id = fields.Many2one('garment.material', string='Material')
    fabric_roll_id = fields.Many2one('garment.fabric.roll', string='Fabric Roll')
    assigned_date = fields.Datetime(string='Assigned Date', default=fields.Datetime.now)
    status = fields.Selection([
        ('active', 'Active'), ('inactive', 'Inactive'), ('lost', 'Lost'),
    ], string='Status', default='active')
    last_scan_datetime = fields.Datetime(string='Last Scan Time')
    last_scan_location_id = fields.Many2one('garment.location', string='Last Scan Location')
    gate_event = fields.Selection([
        ('none', 'None'), ('entry', 'Gate Entry'), ('exit', 'Gate Exit'),
        ('unauthorized', 'Unauthorized Movement'),
    ], string='Last Gate Event', default='none')
    movement_authorized = fields.Boolean(
        string='Movement Authorized', default=True,
        help='Smart Warehouse Gate (SRS section 30/46): cleared automatically on a normal gate '
             'entry/exit, and set False by "Flag Unauthorized Movement" so the item stands out '
             'for a manager to review.')

    _sql_constraints = [
        ('tag_id_uniq', 'unique(tag_id)', 'RFID Tag ID must be unique!'),
    ]

    def action_record_gate_entry(self):
        self.write({'gate_event': 'entry', 'last_scan_datetime': fields.Datetime.now(), 'movement_authorized': True})

    def action_record_gate_exit(self):
        self.write({'gate_event': 'exit', 'last_scan_datetime': fields.Datetime.now(), 'movement_authorized': True})

    def action_flag_unauthorized(self):
        """Smart Warehouse Gate unauthorized-movement alert (SRS section 30
        "Automatic detects: Unauthorized movement")."""
        self.write({
            'gate_event': 'unauthorized', 'last_scan_datetime': fields.Datetime.now(),
            'movement_authorized': False,
        })
