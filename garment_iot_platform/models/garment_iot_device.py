# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""IoT Device Management (SRS s.6, s.18, s.37 — IoT Device model). Central
register of every connected sensor/device: RFID readers, barcode scanners,
environmental sensors, energy meters, machine sensors and counters. A
device of type ``machine_sensor`` may be linked to a
``garment.production.machine`` (garment_production); any device may be
linked to a ``garment.location`` (garment_warehouse) for factory-floor
placement."""

import secrets

from odoo import api, fields, models, _

DEFAULT_OFFLINE_THRESHOLD_MINUTES = 30


class GarmentIotDevice(models.Model):
    _name = 'garment.iot.device'
    _description = 'Garment IoT Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    device_code = fields.Char(string='Device Code', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Device Name', required=True, tracking=True,
                        help='e.g. "IoT Sensor-001", "RFID Gate Reader-Fabric Store".')

    device_type = fields.Selection([
        ('rfid_reader', 'RFID Reader'),
        ('barcode_scanner', 'Barcode Scanner'),
        ('temperature_sensor', 'Temperature Sensor'),
        ('humidity_sensor', 'Humidity Sensor'),
        ('vibration_sensor', 'Vibration Sensor'),
        ('air_quality_sensor', 'Air Quality Sensor'),
        ('water_sensor', 'Water Sensor'),
        ('energy_meter', 'Energy Meter'),
        ('machine_sensor', 'Machine Sensor (Speed/Status/Counter)'),
        ('counter', 'Production Counter'),
        ('plc_node', 'PLC Node'),
        ('other', 'Other'),
    ], string='Device Type', required=True, tracking=True)

    manufacturer = fields.Char(string='Manufacturer')
    model_reference = fields.Char(string='Model')
    serial_number = fields.Char(string='Serial Number')

    gateway_id = fields.Many2one('garment.iot.gateway', string='IoT Gateway', required=True,
                                  tracking=True, ondelete='restrict')
    machine_id = fields.Many2one('garment.production.machine', string='Production Machine',
                                  help='Set when this device (typically a Machine Sensor) monitors a '
                                       'specific machine from garment_production.')
    location_id = fields.Many2one('garment.location', string='Location',
                                   help='Warehouse/factory location this device is installed in.')
    location_note = fields.Char(string='Location Description',
                                 help='Free-text placement, e.g. "Sewing Floor-2", when there is no '
                                      'garment.location record for it.')

    ip_address = fields.Char(string='IP Address')
    mac_address = fields.Char(string='MAC Address')
    default_unit = fields.Char(string='Default Reading Unit',
                                help='Pre-filled unit suggested on incoming readings, e.g. °C, %, kWh, RPM, PCS.')

    api_key = fields.Char(string='Device API Key', copy=False, readonly=True,
                           help='Generated on creation. Sent by the gateway/ingestion script as the '
                                'X-IoT-Api-Key header (or api_key body field) on every call to '
                                '/api/iot/ingest. See controllers/main.py.')

    connection_status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
    ], string='Connection Status', default='offline', tracking=True)
    last_communication = fields.Datetime(string='Last Communication')
    installed_date = fields.Date(string='Installed On')

    reading_ids = fields.One2many('garment.iot.reading', 'device_id', string='Readings')
    reading_count = fields.Integer(string='Readings', compute='_compute_counts')
    alert_rule_ids = fields.One2many('garment.iot.alert.rule', 'device_id', string='Alert Rules (Device-Specific)')
    alert_rule_count = fields.Integer(string='Alert Rules', compute='_compute_counts')
    last_reading_value = fields.Float(string='Last Reading Value', readonly=True)
    last_reading_unit = fields.Char(string='Last Reading Unit', readonly=True)

    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('device_code_uniq', 'unique(device_code, company_id)', 'Device Code must be unique per company!'),
        ('api_key_uniq', 'unique(api_key)', 'Device API Key must be unique!'),
    ]

    @api.depends('reading_ids', 'alert_rule_ids')
    def _compute_counts(self):
        for rec in self:
            rec.reading_count = len(rec.reading_ids)
            rec.alert_rule_count = len(rec.alert_rule_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('device_code', _('New')) == _('New'):
                vals['device_code'] = self.env['ir.sequence'].next_by_code('garment.iot.device') or _('New')
            if not vals.get('api_key'):
                vals['api_key'] = self._generate_api_key()
        return super().create(vals_list)

    @api.model
    def _generate_api_key(self):
        return secrets.token_hex(20)

    def action_generate_api_key(self):
        """Rotate the API key — the ingestion script must be updated with the new key."""
        for rec in self:
            rec.api_key = self._generate_api_key()

    def action_mark_online(self):
        self.write({'connection_status': 'online', 'last_communication': fields.Datetime.now()})

    def action_mark_offline(self):
        self.write({'connection_status': 'offline'})

    def action_view_readings(self):
        self.ensure_one()
        return {
            'name': _('Readings'), 'type': 'ir.actions.act_window', 'res_model': 'garment.iot.reading',
            'view_mode': 'tree,form', 'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
        }

    def action_view_alert_rules(self):
        self.ensure_one()
        return {
            'name': _('Alert Rules'), 'type': 'ir.actions.act_window', 'res_model': 'garment.iot.alert.rule',
            'view_mode': 'tree,form', 'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
        }

    def record_reading(self, reading_type, value=0.0, unit=False, text_value=False, timestamp=False,
                        raw_payload=False):
        """Convenience helper used by the ingestion controller (and callable
        from any other module/script running server-side) to log a reading
        and evaluate alert rules in one call. Returns the created
        garment.iot.reading record."""
        self.ensure_one()
        Reading = self.env['garment.iot.reading']
        reading = Reading.create({
            'device_id': self.id,
            'reading_type': reading_type,
            'value': value,
            'unit': unit or self.default_unit,
            'text_value': text_value,
            'timestamp': timestamp or fields.Datetime.now(),
            'raw_payload': raw_payload,
        })
        self.write({
            'connection_status': 'online',
            'last_communication': fields.Datetime.now(),
            'last_reading_value': value,
            'last_reading_unit': unit or self.default_unit,
        })
        reading.evaluate_alert_rules()
        return reading

    @api.model
    def _cron_flag_stale_devices(self):
        """SRS s.47 IoT Device Report ("Connected Devices" / "Offline
        Devices"). A device that has not called /api/iot/ingest within the
        configured threshold is flipped to Offline so the device report and
        dashboards reflect reality even when the gateway/device stopped
        sending data without an explicit disconnect."""
        minutes = int(self.env['ir.config_parameter'].sudo().get_param(
            'garment_iot_platform.device_offline_threshold_minutes', DEFAULT_OFFLINE_THRESHOLD_MINUTES))
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), minutes=minutes)
        stale = self.search([
            ('connection_status', '=', 'online'),
            '|', ('last_communication', '<', cutoff), ('last_communication', '=', False),
        ])
        if stale:
            stale.write({'connection_status': 'offline'})
