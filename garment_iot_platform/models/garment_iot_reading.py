# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""Generic IoT Reading Log (SRS s.38 Sensor Data model, s.51 IoT Data
Storage).

SCOPE / LIMITATION — NOT a time-series database
-------------------------------------------------
This model is a deliberately lightweight, generic reading log: one row per
reading, stored in a plain PostgreSQL table via the normal ORM. It is
suitable for periodic snapshots (e.g. one temperature/humidity reading
every few minutes), event-style readings (an RFID scan, a barcode scan, a
machine status change) and the handful of readings around an alert. It is
explicitly **NOT** meant to hold true high-frequency telemetry (sub-second
vibration/speed samples from hundreds of machine sensors) as a long-term
relational log — that volume belongs in a dedicated time-series store
(InfluxDB / TimescaleDB / a message queue with downstream aggregation) with
only periodic aggregates or threshold-exception readings forwarded into
this table via the ingestion API. See IMPLEMENTATION_NOTES.md.

Relationship to garment_maintenance
-------------------------------------
This is NOT a duplicate of ``garment.maintenance.iot.reading``
(garment_maintenance). That model is the maintenance-side machine-condition
reading HISTORY (temperature/vibration/speed/power with maintenance-specific
thresholds) that directly creates CMMS breakdown Work Orders. This model is
the broader, cross-device-type ingestion log (RFID/barcode/environment/
energy/machine sensor/counter) fed by the factory-wide gateway/device
registry in THIS module. A Machine Sensor device reading that indicates a
machine-condition problem is expected to be relayed into a
``garment.maintenance.iot.reading`` row (e.g. from an
``garment.iot.alert.rule`` "Call Method" action) rather than this module
re-implementing CMMS alerting logic."""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 365


class GarmentIotReading(models.Model):
    _name = 'garment.iot.reading'
    _description = 'Garment IoT Reading (Generic Sensor/Device Log)'
    _order = 'timestamp desc, id desc'

    device_id = fields.Many2one('garment.iot.device', string='Device', required=True,
                                 ondelete='cascade', index=True)
    device_type = fields.Selection(related='device_id.device_type', string='Device Type', store=True)
    gateway_id = fields.Many2one(related='device_id.gateway_id', string='Gateway', store=True)
    machine_id = fields.Many2one(related='device_id.machine_id', string='Machine', store=True)
    location_id = fields.Many2one(related='device_id.location_id', string='Location', store=True)

    reading_type = fields.Selection([
        ('temperature', 'Temperature'),
        ('humidity', 'Humidity'),
        ('vibration', 'Vibration'),
        ('air_quality', 'Air Quality'),
        ('water', 'Water'),
        ('energy', 'Energy Consumption'),
        ('speed', 'Speed / RPM'),
        ('count', 'Production Count'),
        ('status', 'Machine Status'),
        ('rfid_scan', 'RFID Scan'),
        ('barcode_scan', 'Barcode Scan'),
        ('other', 'Other'),
    ], string='Reading Type', required=True, index=True)

    value = fields.Float(string='Value', digits=(16, 4))
    unit = fields.Char(string='Unit', help='e.g. °C, %, kWh, RPM, PCS.')
    text_value = fields.Char(string='Text / Tag Value',
                              help='Non-numeric payload, e.g. an RFID tag UID or barcode value, or a '
                                   'machine status string.')
    timestamp = fields.Datetime(string='Reading Time', required=True, default=fields.Datetime.now, index=True)
    raw_payload = fields.Text(string='Raw Payload (JSON)',
                               help='The raw JSON body received on /api/iot/ingest, kept for audit/replay.')

    alert_log_ids = fields.One2many('garment.iot.alert.log', 'reading_id', string='Alerts Triggered')
    alert_count = fields.Integer(string='Alerts', compute='_compute_alert_count')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('alert_log_ids')
    def _compute_alert_count(self):
        for rec in self:
            rec.alert_count = len(rec.alert_log_ids)

    def evaluate_alert_rules(self):
        """Match this reading against active alert rules (device-specific
        rules first, then device-type + reading-type rules) and fire any
        that trip. Called automatically by the ingestion controller / the
        garment.iot.device.record_reading() helper right after a reading is
        created; safe to call again manually (e.g. from a re-evaluation
        wizard/cron)."""
        AlertRule = self.env['garment.iot.alert.rule']
        for rec in self:
            if not rec.device_id:
                continue
            rules = AlertRule.search([
                ('active', '=', True),
                ('reading_type', '=', rec.reading_type),
                '|',
                ('device_id', '=', rec.device_id.id),
                '&', ('device_id', '=', False), ('device_type', '=', rec.device_type),
            ])
            for rule in rules:
                rule.check_and_fire(rec)
        return True

    @api.model
    def _cron_prune_old_readings(self):
        """SRS s.51 Data Retention: "Real-Time Data: 1 Year". This is the
        real implementation of that retention rule for THIS lightweight
        relational log (see the module-level docstring on why it is not a
        time-series store to begin with) — readings older than the
        retention window are deleted in batches. Alerts already fired
        (``garment.iot.alert.log``) are kept indefinitely per SRS s.51
        "Audit Data: Permanent" since their reading_id simply goes null
        (ondelete='set null')."""
        days = int(self.env['ir.config_parameter'].sudo().get_param(
            'garment_iot_platform.reading_retention_days', DEFAULT_RETENTION_DAYS))
        if days <= 0:
            return
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        stale = self.search([('timestamp', '<', cutoff)], limit=5000)
        if stale:
            _logger.info('IoT reading retention: pruning %s reading(s) older than %s days.', len(stale), days)
            stale.unlink()
