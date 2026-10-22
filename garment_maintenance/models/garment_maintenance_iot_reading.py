# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
IoT Machine Monitoring Integration (Maintenance & Asset Mgmt SRS sec.
35, 49-50, CMMS SRS sec. 34) — a time-series sensor reading log used to
trigger maintenance alerts. ``garment.production.machine`` (from
garment_production) already carries the latest-known IoT snapshot
fields (last_speed / last_vibration / last_energy_consumption /
last_data_sync) used for shop-floor MES display; this model is the
maintenance-side reading HISTORY and threshold-alerting log feeding
those same machines (or other registered assets), not a duplicate of
the snapshot fields themselves. See IMPLEMENTATION_NOTES.md.
"""
from odoo import api, fields, models, _


class GarmentMaintenanceIotReading(models.Model):
    _name = 'garment.maintenance.iot.reading'
    _description = 'Garment Maintenance IoT Sensor Reading'
    _order = 'reading_datetime desc'

    equipment_type = fields.Selection([
        ('machine', 'Production Machine'),
        ('asset', 'Other Asset'),
    ], string='Equipment Type', default='machine', required=True)
    machine_id = fields.Many2one('garment.production.machine', string='Machine')
    asset_id = fields.Many2one('garment.asset', string='Asset')
    equipment_name = fields.Char(string='Equipment', compute='_compute_equipment_name', store=True)

    reading_datetime = fields.Datetime(string='Reading Time', default=fields.Datetime.now, required=True)
    running_status = fields.Selection([
        ('running', 'Running'), ('idle', 'Idle'), ('stopped', 'Stopped'), ('error', 'Error'),
    ], string='Running Status', default='running')
    speed = fields.Float(string='Speed (RPM)')
    temperature = fields.Float(string='Temperature (°C)')
    vibration = fields.Float(string='Vibration')
    power_consumption = fields.Float(string='Power Consumption (kWh)')
    error_code = fields.Char(string='Error Code')

    condition = fields.Selection([
        ('normal', 'Normal'), ('warning', 'Warning'), ('critical', 'Critical'),
    ], string='Condition', compute='_compute_condition', store=True)
    alert_triggered = fields.Boolean(string='Maintenance Alert Triggered')
    workorder_id = fields.Many2one('garment.maintenance.workorder', string='Alert Work Order')

    # Configurable thresholds (simple defaults; a real deployment would
    # source these per machine type from the IoT gateway configuration).
    temperature_warning = fields.Float(string='Temperature Warning Threshold', default=60.0)
    temperature_critical = fields.Float(string='Temperature Critical Threshold', default=75.0)
    vibration_warning = fields.Float(string='Vibration Warning Threshold', default=5.0)
    vibration_critical = fields.Float(string='Vibration Critical Threshold', default=8.0)

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('machine_id.name', 'machine_id.machine_number', 'asset_id.name', 'asset_id.asset_code')
    def _compute_equipment_name(self):
        for rec in self:
            if rec.equipment_type == 'machine' and rec.machine_id:
                rec.equipment_name = rec.machine_id.name or rec.machine_id.machine_number
            elif rec.equipment_type == 'asset' and rec.asset_id:
                rec.equipment_name = '%s [%s]' % (rec.asset_id.name, rec.asset_id.asset_code)
            else:
                rec.equipment_name = False

    @api.depends('temperature', 'vibration', 'running_status', 'error_code')
    def _compute_condition(self):
        for rec in self:
            if rec.running_status == 'error' or rec.error_code or \
                    rec.temperature >= rec.temperature_critical or rec.vibration >= rec.vibration_critical:
                rec.condition = 'critical'
            elif rec.temperature >= rec.temperature_warning or rec.vibration >= rec.vibration_warning:
                rec.condition = 'warning'
            else:
                rec.condition = 'normal'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.condition == 'critical' and not rec.alert_triggered:
                rec._create_maintenance_alert()
        return records

    def _create_maintenance_alert(self):
        self.ensure_one()
        wo = self.env['garment.maintenance.workorder'].create({
            'wo_type': 'breakdown',
            'equipment_type': self.equipment_type,
            'machine_id': self.machine_id.id,
            'asset_id': self.asset_id.id,
            'priority': 'high',
            'problem_description': _('IoT alert: %s reading out of safe range (temp=%.1f, vibration=%.2f, status=%s).')
            % (self.equipment_name or '', self.temperature, self.vibration, self.running_status),
        })
        self.write({'alert_triggered': True, 'workorder_id': wo.id})
        return wo
