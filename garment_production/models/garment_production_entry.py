# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models, _


class GarmentProductionEntry(models.Model):
    """Shop-floor Production Entry — the unified real-time data-capture
    document used across Cutting/Sewing/Washing/Finishing/Packing (manual,
    tablet, barcode scan or IoT machine data). Drives hourly production
    monitoring, line efficiency and operator performance. See Production
    Management SRS s.32-34/37, Planning & MES SRS s.19/26, MES SRS s.9/12-13,
    Shop Floor SRS s.17/21."""
    _name = 'garment.production.entry'
    _description = 'Garment Production Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, hour desc'
    _rec_name = 'name'

    name = fields.Char(string='Entry Reference', copy=False, readonly=True, default=lambda s: _('New'))
    production_order_id = fields.Many2one('garment.production.order', string='Production Order',
                                           required=True, tracking=True)
    work_order_id = fields.Many2one('garment.work.order', string='Work Order')
    routing_line_id = fields.Many2one('garment.operation.routing.line', string='Operation')
    line_id = fields.Many2one('garment.production.line', string='Production Line', tracking=True)
    work_center_id = fields.Many2one('garment.work.center', string='Work Center')
    department = fields.Selection([
        ('cutting', 'Cutting'), ('sewing', 'Sewing'), ('washing', 'Washing'),
        ('finishing', 'Finishing'), ('packing', 'Packing'),
    ], string='Department', required=True, default='sewing', tracking=True)

    employee_id = fields.Many2one('garment.hr.employee', string='Operator')
    bundle_id = fields.Many2one('garment.cutting.bundle', string='Bundle')

    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    hour = fields.Selection([(str(h), '%02d:00' % h) for h in range(24)], string='Hour Slot')
    shift = fields.Selection([
        ('morning', 'Morning'), ('evening', 'Evening'), ('night', 'Night'), ('general', 'General'),
    ], string='Shift', default='general')

    entry_method = fields.Selection([
        ('manual', 'Manual Entry'), ('tablet', 'Tablet App'), ('barcode', 'Barcode Scan'),
        ('iot', 'IoT Machine Data'),
    ], string='Entry Method', default='manual')

    target_qty = fields.Float(string='Target Quantity (PCS)')
    input_qty = fields.Float(string='Input Quantity (PCS)')
    output_qty = fields.Float(string='Output Quantity (PCS)')
    reject_qty = fields.Float(string='Reject Quantity (PCS)')
    rework_qty = fields.Float(string='Rework Quantity (PCS)')

    smv = fields.Float(string='SMV (Minutes)', digits=(6, 3))
    manpower = fields.Integer(string='Manpower', default=1)
    working_minutes = fields.Float(string='Working Minutes', default=60.0)

    efficiency_pct = fields.Float(string='Efficiency (%)', compute='_compute_efficiency', store=True)
    achievement_pct = fields.Float(string='Target Achievement (%)', compute='_compute_efficiency', store=True)
    quality_score = fields.Float(string='Quality Score (%)', compute='_compute_efficiency', store=True)

    status = fields.Selection([
        ('draft', 'Draft'), ('confirmed', 'Confirmed'), ('approved', 'Approved'),
    ], string='Status', default='draft', tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('output_qty', 'target_qty', 'smv', 'manpower', 'working_minutes', 'reject_qty', 'input_qty')
    def _compute_efficiency(self):
        for rec in self:
            # Line Efficiency % = (SAM x Output) / (Manpower x Working Minutes) x 100
            denominator = (rec.manpower or 0) * (rec.working_minutes or 0)
            if rec.smv and denominator:
                rec.efficiency_pct = min(999.9, (rec.smv * rec.output_qty) / denominator * 100.0)
            elif rec.target_qty:
                rec.efficiency_pct = min(999.9, rec.output_qty / rec.target_qty * 100.0)
            else:
                rec.efficiency_pct = 0.0
            rec.achievement_pct = (rec.output_qty / rec.target_qty * 100.0) if rec.target_qty else 0.0
            checked_qty = rec.output_qty + rec.reject_qty
            rec.quality_score = ((rec.output_qty / checked_qty) * 100.0) if checked_qty else 100.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garment.production.entry') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'status': 'confirmed'})

    def action_approve(self):
        self.write({'status': 'approved', 'approved_by_id': self.env.user.id})
