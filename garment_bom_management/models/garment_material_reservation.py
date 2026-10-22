# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentMaterialReservation(models.Model):
    """Material Reservation (SRS section 27) — garment.material.reservation.
    Reserves Fabric/Trim/Packaging materials against a specific order ahead
    of production, and raises a Shortage Alert when reserved/available
    quantity cannot cover the requirement.

    Note: no hard dependency on garment_order_management or garment_warehouse
    (both already depend on garment_bom_management — depending on them back
    would create a circular dependency), so 'order_reference' is a free-text
    field and stock quantities are entered manually. See
    IMPLEMENTATION_NOTES.md."""
    _name = 'garment.material.reservation'
    _description = 'Garment Material Reservation'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    bom_id = fields.Many2one('garment.bom', string='BOM', required=True, ondelete='cascade')
    style_id = fields.Many2one('garment.style', string='Style', related='bom_id.style_id', store=True)
    order_reference = fields.Char(string='Order Number')
    material_type = fields.Selection([
        ('fabric', 'Fabric'), ('trim', 'Trim'), ('packaging', 'Packaging'),
    ], string='Material Type', required=True)
    fabric_bom_id = fields.Many2one('garment.fabric.bom', string='Fabric Line',
                                     domain="[('bom_id', '=', bom_id)]")
    trim_bom_id = fields.Many2one('garment.trim.bom', string='Trim Line',
                                   domain="[('bom_id', '=', bom_id)]")
    packaging_bom_id = fields.Many2one('garment.packaging.bom', string='Packaging Line',
                                        domain="[('bom_id', '=', bom_id)]")
    material_name = fields.Char(string='Material')
    required_qty = fields.Float(string='Required Quantity')
    reserved_qty = fields.Float(string='Reserved Quantity')
    available_qty = fields.Float(string='Available Quantity')
    shortage_qty = fields.Float(string='Shortage Quantity', compute='_compute_shortage', store=True)
    state = fields.Selection([
        ('draft', 'Draft'), ('reserved', 'Reserved'), ('shortage', 'Shortage'), ('fulfilled', 'Fulfilled'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('required_qty', 'reserved_qty', 'available_qty')
    def _compute_shortage(self):
        for rec in self:
            covered = min(rec.reserved_qty or 0.0, rec.available_qty or 0.0) if rec.available_qty else (rec.reserved_qty or 0.0)
            rec.shortage_qty = max((rec.required_qty or 0.0) - covered, 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_shortage_alert()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('required_qty', 'reserved_qty', 'available_qty')):
            self._check_shortage_alert()
        return res

    def _check_shortage_alert(self):
        """Automatic Shortage Alert notification (SRS section 27 / 45)."""
        for rec in self:
            if rec.shortage_qty > 0 and rec.state != 'shortage':
                rec.state = 'shortage'
                rec.message_post(body=_('Shortage Alert: "%s" is short by %.2f (Order %s).') % (
                    rec.material_name or rec.material_type, rec.shortage_qty, rec.order_reference or '-'))
                rec.bom_id.message_post(body=_('Material shortage on reservation "%s": short by %.2f.') % (
                    rec.material_name or rec.material_type, rec.shortage_qty))
            elif rec.shortage_qty <= 0 and rec.state == 'shortage':
                rec.state = 'reserved' if rec.reserved_qty else 'fulfilled'
