# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentFinishingOrder(models.Model):
    """Finishing Order — Thread Cutting, Ironing, Measurement Check,
    Folding, Tagging. See Production Management SRS s.45-48, Planning & MES
    SRS s.41."""
    _name = 'garment.finishing.order'
    _description = 'Garment Finishing Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Finishing Number', copy=False, readonly=True, default=lambda s: _('New'))
    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, tracking=True)
    style_id = fields.Many2one('garment.style', string='Style', required=True)
    quantity = fields.Float(string='Quantity (PCS)', required=True)
    completed_qty = fields.Float(string='Completed Quantity (PCS)', compute='_compute_completed', store=True)
    completion_pct = fields.Float(string='Completion (%)', compute='_compute_completed', store=True)

    operation_line_ids = fields.One2many('garment.finishing.operation.line', 'finishing_order_id', string='Operations')
    measurement_check_ids = fields.One2many('garment.measurement.check', 'finishing_order_id', string='Measurement Checks')

    status = fields.Selection([
        ('draft', 'Draft'), ('running', 'Running'), ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('operation_line_ids.quantity', 'operation_line_ids.status', 'quantity')
    def _compute_completed(self):
        for rec in self:
            done = sum(rec.operation_line_ids.filtered(lambda l: l.status == 'completed').mapped('quantity'))
            rec.completed_qty = done
            rec.completion_pct = min(100.0, (done / rec.quantity * 100.0)) if rec.quantity else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.finishing.order') or _('New')
        return super().create(vals_list)


class GarmentFinishingOperationLine(models.Model):
    """Finishing operation line: Thread Trimming, Ironing, Spot Cleaning,
    Measurement, Folding, Tag Attachment. See Production Management SRS
    s.46-47 (also captures Ironing temperature/machine)."""
    _name = 'garment.finishing.operation.line'
    _description = 'Garment Finishing Operation Line'
    _order = 'sequence'

    finishing_order_id = fields.Many2one('garment.finishing.order', string='Finishing Order',
                                         required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    operation = fields.Selection([
        ('thread_trimming', 'Thread Trimming'), ('ironing', 'Ironing'), ('spot_cleaning', 'Spot Cleaning'),
        ('measurement', 'Measurement'), ('folding', 'Folding'), ('tag_attachment', 'Tag Attachment'),
    ], string='Operation', required=True)
    operator_id = fields.Many2one('garment.hr.employee', string='Operator')
    quantity = fields.Float(string='Quantity (PCS)')
    defect_qty = fields.Float(string='Defect Quantity (PCS)')
    # Ironing-specific (SRS s.47)
    machine_id = fields.Many2one('garment.production.machine', string='Machine')
    temperature = fields.Float(string='Temperature (°C)')
    status = fields.Selection([
        ('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'),
    ], string='Status', default='pending')
