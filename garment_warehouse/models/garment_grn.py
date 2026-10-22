# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentGrn(models.Model):
    """Gate Entry + Goods Receipt + Material Inspection Integration
    (SRS sections 10-12) — garment.grn. Linked to Module 9's Purchase
    Order / Delivery rather than duplicating supplier or PO data."""
    _name = 'garment.grn'
    _description = 'Garment Goods Receipt Note'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'arrival_datetime desc'

    grn_number = fields.Char(string='GRN Number', copy=False, readonly=True, default=lambda s: _('New'))
    purchase_order_id = fields.Many2one('garment.purchase.order', string='Purchase Order')
    purchase_delivery_id = fields.Many2one('garment.purchase.delivery', string='Purchase Delivery')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    warehouse_id = fields.Many2one('garment.warehouse', string='Receiving Warehouse', required=True)

    # Gate Entry
    vehicle_number = fields.Char(string='Vehicle Number')
    driver_name = fields.Char(string='Driver Name')
    arrival_datetime = fields.Datetime(string='Arrival Time', default=fields.Datetime.now)
    gate_status = fields.Selection([
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], string='Gate Status', default='pending')

    line_ids = fields.One2many('garment.grn.line', 'grn_id', string='GRN Lines')

    status = fields.Selection([
        ('draft', 'Draft'), ('gate_entry', 'Gate Entry'), ('quality_inspection', 'Quality Inspection'),
        ('putaway', 'Putaway'), ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    # Receiving Performance KPI (SRS section 52 "Warehouse Performance
    # Analytics" — Receiving KPI: GRN Processing Time).
    completed_date = fields.Datetime(string='Completed Date', readonly=True, copy=False)
    processing_hours = fields.Float(string='Processing Time (Hours)', compute='_compute_processing_hours', store=True)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('arrival_datetime', 'completed_date')
    def _compute_processing_hours(self):
        for rec in self:
            if rec.arrival_datetime and rec.completed_date:
                delta = rec.completed_date - rec.arrival_datetime
                rec.processing_hours = round(delta.total_seconds() / 3600.0, 2)
            else:
                rec.processing_hours = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('grn_number', _('New')) == _('New'):
                vals['grn_number'] = self.env['ir.sequence'].next_by_code('garment.grn') or _('New')
        return super().create(vals_list)

    def action_approve_gate(self):
        self.write({'gate_status': 'approved', 'status': 'gate_entry'})

    def action_complete_putaway(self):
        """Creates a stock.move receipt for each accepted GRN line, posted
        directly to the assigned location — this is what actually updates
        garment.material.on_hand_qty."""
        Move = self.env['garment.stock.move']
        for rec in self:
            for line in rec.line_ids:
                if line.accepted_qty > 0:
                    Move.create({
                        'material_id': line.material_id.id,
                        'warehouse_id': rec.warehouse_id.id,
                        'location_id': line.putaway_location_id.id,
                        'move_type': 'receipt',
                        'quantity': line.accepted_qty,
                        'move_date': fields.Date.context_today(rec),
                        'reference': rec.grn_number,
                        'state': 'done',
                    })
            rec.write({'status': 'completed', 'completed_date': fields.Datetime.now()})
        return True
