# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Asset Master Management (Maintenance & Asset Mgmt SRS sec. 6-10). Covers
NON-PRODUCTION assets only: Utility Assets (Generator, Compressor,
Transformer, Chiller, HVAC, Boiler) and Facility Assets (Building,
Vehicle, Computer, Furniture, Quality/Testing Instrument used for
calibration). Production machinery (Sewing/Cutting/Embroidery/Printing/
Washing/Dryer etc.) already has a complete register in garment_production
as ``garment.production.machine`` — it is intentionally NOT duplicated
here. See IMPLEMENTATION_NOTES.md.
"""
from datetime import timedelta

from odoo import api, fields, models, _


class GarmentAsset(models.Model):
    _name = 'garment.asset'
    _description = 'Garment Non-Production Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'asset_code'

    asset_code = fields.Char(string='Asset Code', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Asset Name', required=True, tracking=True)
    category = fields.Selection([
        ('utility_generator', 'Generator'),
        ('utility_compressor', 'Compressor'),
        ('utility_transformer', 'Transformer'),
        ('utility_chiller', 'Chiller'),
        ('utility_hvac', 'HVAC System'),
        ('utility_boiler', 'Boiler'),
        ('facility_building', 'Building'),
        ('facility_vehicle', 'Vehicle'),
        ('facility_computer', 'Computer'),
        ('facility_furniture', 'Furniture'),
        ('quality_instrument', 'Quality / Testing Instrument'),
        ('other', 'Other'),
    ], string='Asset Category', required=True, tracking=True)
    brand = fields.Char(string='Brand')
    model_reference = fields.Char(string='Model')
    serial_number = fields.Char(string='Serial Number')

    # Technical specification (SRS sec. 9 CMMS)
    motor_power = fields.Char(string='Motor Power')
    voltage = fields.Char(string='Voltage')
    capacity = fields.Char(string='Capacity')
    speed = fields.Char(string='Speed')
    manual_document = fields.Binary(string='Manufacturer Manual', attachment=True)
    manual_filename = fields.Char(string='Manual Filename')

    # Location hierarchy (SRS sec. 8: Factory -> Floor -> Department -> Line -> Machine)
    factory = fields.Char(string='Factory')
    floor = fields.Char(string='Floor')
    department_id = fields.Many2one('garment.hr.department', string='Department')
    line_position = fields.Char(string='Line / Position')

    # Purchase & lifecycle (SRS sec. 7, 9 Part1)
    supplier_id = fields.Many2one('garment.supplier', string='Supplier')
    purchase_date = fields.Date(string='Purchase Date', tracking=True)
    installation_date = fields.Date(string='Installation Date')
    purchase_value = fields.Monetary(string='Purchase Value', currency_field='currency_id')
    maintenance_cost_total = fields.Monetary(
        string='Cumulative Maintenance Cost', compute='_compute_maintenance_cost_total',
        store=True, currency_field='currency_id')
    current_value = fields.Monetary(string='Current Value', currency_field='currency_id',
                                     help='Manually updated net book value after depreciation.')
    currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('installed', 'Installed'),
        ('active', 'Active / Operating'),
        ('under_maintenance', 'Under Maintenance'),
        ('breakdown', 'Breakdown'),
        ('disposed', 'Disposed'),
    ], string='Lifecycle Status', default='draft', tracking=True)

    # Warranty (SRS sec. 10)
    warranty_start_date = fields.Date(string='Warranty Start Date')
    warranty_end_date = fields.Date(string='Warranty End Date', tracking=True)
    warranty_terms = fields.Text(string='Warranty Terms')
    warranty_expiring_soon = fields.Boolean(string='Warranty Expiring Soon',
                                             compute='_compute_warranty_expiring_soon', store=True)

    responsible_technician_id = fields.Many2one('garment.hr.employee', string='Responsible Technician',
                                                  domain=[('is_maintenance_technician', '=', True)])

    plan_ids = fields.One2many('garment.maintenance.plan', 'asset_id', string='Preventive Maintenance Plans')
    plan_count = fields.Integer(compute='_compute_related_counts')
    workorder_ids = fields.One2many('garment.maintenance.workorder', 'asset_id', string='Work Orders')
    workorder_count = fields.Integer(compute='_compute_related_counts')
    calibration_ids = fields.One2many('garment.calibration', 'asset_id', string='Calibration Records')
    calibration_count = fields.Integer(compute='_compute_related_counts')

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('asset_code_uniq', 'unique(asset_code, company_id)', 'Asset Code must be unique per company!'),
    ]

    @api.depends('workorder_ids.total_cost', 'workorder_ids.state')
    def _compute_maintenance_cost_total(self):
        for rec in self:
            done = rec.workorder_ids.filtered(lambda w: w.state in ('completed', 'closed'))
            rec.maintenance_cost_total = sum(done.mapped('total_cost'))

    @api.depends('warranty_end_date')
    def _compute_warranty_expiring_soon(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.warranty_expiring_soon = bool(rec.warranty_end_date and rec.warranty_end_date <= today + timedelta(days=30)
                                               and rec.warranty_end_date >= today)

    def _compute_related_counts(self):
        for rec in self:
            rec.plan_count = len(rec.plan_ids)
            rec.workorder_count = len(rec.workorder_ids)
            rec.calibration_count = len(rec.calibration_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('asset_code', _('New')) == _('New'):
                vals['asset_code'] = self.env['ir.sequence'].next_by_code('garment.asset') or _('New')
        return super().create(vals_list)

    def action_view_workorders(self):
        self.ensure_one()
        return {
            'name': _('Work Orders'), 'type': 'ir.actions.act_window', 'res_model': 'garment.maintenance.workorder',
            'view_mode': 'tree,form', 'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id, 'default_equipment_type': 'asset'},
        }

    def action_view_plans(self):
        self.ensure_one()
        return {
            'name': _('PM Plans'), 'type': 'ir.actions.act_window', 'res_model': 'garment.maintenance.plan',
            'view_mode': 'tree,form', 'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id, 'default_equipment_type': 'asset'},
        }

    def action_view_calibrations(self):
        self.ensure_one()
        return {
            'name': _('Calibration Records'), 'type': 'ir.actions.act_window', 'res_model': 'garment.calibration',
            'view_mode': 'tree,form', 'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }
