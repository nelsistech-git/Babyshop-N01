# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import fields, models


class GarmentBarcode(models.Model):
    """Barcode Management System (SRS sections 13, 41-43) —
    garment.barcode."""
    _name = 'garment.barcode'
    _description = 'Garment Barcode'
    _order = 'generated_date desc'

    barcode_value = fields.Char(string='Barcode Value', required=True, copy=False)
    usage_type = fields.Selection([
        ('material', 'Material/Product'), ('roll', 'Fabric Roll'), ('carton', 'Carton'),
        ('location', 'Location/Bin'), ('batch', 'Batch'),
    ], string='Barcode Use', default='material', required=True,
       help='What this barcode identifies (SRS "Barcode Types": Product, Roll, Carton, Location, Batch Barcode).')
    material_id = fields.Many2one('garment.material', string='Material')
    fabric_roll_id = fields.Many2one('garment.fabric.roll', string='Fabric Roll')
    location_id = fields.Many2one('garment.location', string='Location',
                                   help='Set when Barcode Use = Location/Bin.')
    barcode_type = fields.Selection([
        ('code128', 'Code 128'), ('ean13', 'EAN-13'), ('qr', 'QR Code'),
    ], string='Barcode Type', default='code128')
    generated_date = fields.Datetime(string='Generated Date', default=fields.Datetime.now)
    printed = fields.Boolean(string='Printed')
    last_scanned_date = fields.Datetime(string='Last Scanned Date')
    last_scanned_by_id = fields.Many2one('res.users', string='Last Scanned By')
    last_scanned_location_id = fields.Many2one('garment.location', string='Last Scanned Location')

    _sql_constraints = [
        ('barcode_value_uniq', 'unique(barcode_value)', 'Barcode value must be unique!'),
    ]

    def action_mark_printed(self):
        self.write({'printed': True})

    def action_scan(self, scanned_location_id=None):
        """Mobile Barcode Scanning (SRS section 43/28 "Scan -> Stock
        Update"). When a location is scanned alongside a fabric-roll
        barcode, the roll's tracked location is updated too, so scanning
        during a putaway/transfer actually moves the roll in the system."""
        vals = {'last_scanned_date': fields.Datetime.now(), 'last_scanned_by_id': self.env.user.id}
        if scanned_location_id:
            vals['last_scanned_location_id'] = scanned_location_id
        self.write(vals)
        if scanned_location_id:
            for rec in self:
                if rec.fabric_roll_id:
                    rec.fabric_roll_id.write({'location_id': scanned_location_id})
        return True
