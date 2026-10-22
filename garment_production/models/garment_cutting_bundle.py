# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentCuttingBundle(models.Model):
    """Cutting Bundle — panels grouped into bundles after cutting, tracked
    with barcode through Sewing/Finishing/Packing. See Production
    Management SRS s.26, Planning & MES SRS s.17, MES SRS s.33-35 (Bundle /
    RFID Tracking), Shop Floor SRS s.15/28 (Bundle Movement)."""
    _name = 'garment.cutting.bundle'
    _description = 'Garment Cutting Bundle'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Bundle Number', copy=False, readonly=True, default=lambda s: _('New'))
    cutting_order_id = fields.Many2one('garment.cutting.order', string='Cutting Order',
                                       required=True, ondelete='cascade')
    style_id = fields.Many2one('garment.style', related='cutting_order_id.style_id', string='Style', store=True)
    size = fields.Char(string='Size')
    color = fields.Char(string='Color')
    quantity = fields.Float(string='Quantity (PCS)', required=True)
    barcode = fields.Char(string='Barcode', copy=False)
    rfid_tag_id = fields.Many2one('garment.rfid.tag', string='RFID Tag')

    destination_line_id = fields.Many2one('garment.production.line', string='Destination Line')
    current_line_id = fields.Many2one('garment.production.line', string='Current Location (Line)')
    current_operation = fields.Char(string='Current Operation')

    status = fields.Selection([
        ('cutting', 'Cutting'), ('numbering', 'Numbering'), ('bundling', 'Bundled'),
        ('sewing', 'In Sewing'), ('finishing', 'In Finishing'), ('packing', 'In Packing'), ('completed', 'Completed'),
    ], string='Status', default='bundling', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.cutting.bundle') or _('New')
            if not vals.get('barcode'):
                vals['barcode'] = vals.get('name')
        return super().create(vals_list)

    def action_scan_move(self, line_id=False, operation=False, status=False):
        """Barcode scan handler used by shop floor / mobile MES to move a
        bundle to its next station."""
        vals = {}
        if line_id:
            vals['current_line_id'] = line_id
        if operation:
            vals['current_operation'] = operation
        if status:
            vals['status'] = status
        if vals:
            self.write(vals)
