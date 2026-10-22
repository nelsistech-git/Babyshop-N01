# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""IoT Threshold Alert Rules (SRS s.28 Smart Andon System, s.48 Real-Time
Alert Management, IOT-005). A rule is either device-specific (device_id
set) or applies to every device of a given device_type; it compares every
matching incoming garment.iot.reading's value against a threshold and, when
tripped, logs a garment.iot.alert.log row and runs one configured action."""

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

OPERATORS = [
    ('>', 'Greater Than (>)'),
    ('>=', 'Greater Than or Equal (>=)'),
    ('<', 'Less Than (<)'),
    ('<=', 'Less Than or Equal (<=)'),
    ('==', 'Equal (==)'),
    ('!=', 'Not Equal (!=)'),
]

_OP_FUNCS = {
    '>': lambda a, b: a > b,
    '>=': lambda a, b: a >= b,
    '<': lambda a, b: a < b,
    '<=': lambda a, b: a <= b,
    '==': lambda a, b: a == b,
    '!=': lambda a, b: a != b,
}


class GarmentIotAlertRule(models.Model):
    _name = 'garment.iot.alert.rule'
    _description = 'Garment IoT Alert Rule'
    _order = 'severity desc, name'

    name = fields.Char(string='Rule Name', required=True,
                        help='e.g. "Sewing Floor Temperature Critical", "Generator Overload".')
    active = fields.Boolean(default=True)

    device_id = fields.Many2one('garment.iot.device', string='Specific Device', ondelete='cascade',
                                 help='Leave empty to apply this rule to every device of Device Type below.')
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
    ], string='Applies To Device Type', help='Used only when Specific Device is empty.')
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
    ], string='Reading Type', required=True)

    operator = fields.Selection(OPERATORS, string='Operator', required=True, default='>')
    threshold_value = fields.Float(string='Threshold Value', required=True, digits=(16, 4))

    severity = fields.Selection([
        ('info', 'Info / Green'),
        ('warning', 'Warning / Yellow'),
        ('critical', 'Critical / Red'),
    ], string='Severity', required=True, default='warning',
        help='Mirrors the SRS Smart Andon Green/Yellow/Red alert levels.')

    action_type = fields.Selection([
        ('create_activity', 'Create Activity (Odoo To-Do)'),
        ('post_message', 'Post Message on Device Chatter'),
        ('call_method', 'Call Method on Another Model'),
    ], string='Action', required=True, default='post_message')
    action_summary = fields.Char(string='Message / Activity Summary',
                                  help='Template text; {device}, {value}, {unit}, {threshold} are substituted.')
    target_user_id = fields.Many2one('res.users', string='Assign Activity To')
    action_model_id = fields.Many2one('ir.model', string='Target Model',
                                       help='Used only for the "Call Method" action, e.g. '
                                            'garment.maintenance.iot.reading to relay a Machine Sensor '
                                            'reading into the CMMS alerting log.')
    action_method = fields.Char(string='Method Name',
                                 help='Model method to call. Called as: env[model].sudo().<method>(reading) '
                                      'with the triggering garment.iot.reading record as the argument. The '
                                      'method must exist and accept that signature — configuration is '
                                      'validated on save where possible; a bad method name fails safely and '
                                      'is logged on the fired alert.')

    cooldown_minutes = fields.Integer(string='Cooldown (Minutes)', default=15,
                                       help='Do not fire this rule again for the same device within this '
                                            'many minutes of its last firing, to avoid alert flooding from '
                                            'rapid repeated readings. 0 = no cooldown.')

    alert_log_ids = fields.One2many('garment.iot.alert.log', 'rule_id', string='Fired Alerts')
    alert_count = fields.Integer(string='Alerts Fired', compute='_compute_alert_count')

    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('alert_log_ids')
    def _compute_alert_count(self):
        for rec in self:
            rec.alert_count = len(rec.alert_log_ids)

    @api.constrains('device_id', 'device_type')
    def _check_scope(self):
        for rec in self:
            if not rec.device_id and not rec.device_type:
                raise UserError(_('Set either a Specific Device or an "Applies To Device Type" for rule "%s".')
                                 % rec.name)

    @api.constrains('action_type', 'action_model_id', 'action_method')
    def _check_call_method_config(self):
        for rec in self:
            if rec.action_type == 'call_method' and not (rec.action_model_id and rec.action_method):
                raise UserError(_('Rule "%s" uses the "Call Method" action and needs both a Target Model '
                                   'and a Method Name.') % rec.name)

    def _is_tripped(self, value):
        self.ensure_one()
        return _OP_FUNCS[self.operator](value, self.threshold_value)

    def _in_cooldown(self, device):
        self.ensure_one()
        if not self.cooldown_minutes:
            return False
        last = self.env['garment.iot.alert.log'].search([
            ('rule_id', '=', self.id), ('device_id', '=', device.id),
        ], order='triggered_datetime desc', limit=1)
        if not last or not last.triggered_datetime:
            return False
        elapsed = fields.Datetime.now() - last.triggered_datetime
        return elapsed.total_seconds() < (self.cooldown_minutes * 60)

    def check_and_fire(self, reading):
        """Evaluate this rule against one garment.iot.reading; if tripped
        and not in cooldown, log the alert and run the configured action.
        Returns the created garment.iot.alert.log record, or an empty
        recordset when the rule did not fire."""
        self.ensure_one()
        AlertLog = self.env['garment.iot.alert.log']
        if not self._is_tripped(reading.value):
            return AlertLog.browse()
        if self._in_cooldown(reading.device_id):
            return AlertLog.browse()

        action_taken = self._run_action(reading)
        return AlertLog.sudo().create({
            'rule_id': self.id,
            'reading_id': reading.id,
            'device_id': reading.device_id.id,
            'severity': self.severity,
            'value': reading.value,
            'triggered_datetime': fields.Datetime.now(),
            'action_taken': action_taken,
        })

    def _format_message(self, reading):
        self.ensure_one()
        template = self.action_summary or _('{device}: {reading_type} reading {value} {unit} '
                                              '{operator} threshold {threshold}')
        try:
            return template.format(
                device=reading.device_id.name or '', reading_type=reading.reading_type or '',
                value=reading.value, unit=reading.unit or '', operator=self.operator,
                threshold=self.threshold_value)
        except (KeyError, IndexError):
            return template

    def _run_action(self, reading):
        """Executes the configured action and returns a short human-readable
        description of what happened, stored on the alert log. Never raises
        — a failure in the configured action must not block the reading
        that was already saved from being ingested."""
        self.ensure_one()
        message = self._format_message(reading)
        try:
            if self.action_type == 'post_message':
                reading.device_id.sudo().message_post(body=message)
                return _('Message posted on device "%s".') % reading.device_id.name

            if self.action_type == 'create_activity':
                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                reading.device_id.sudo().activity_schedule(
                    activity_type_id=activity_type.id if activity_type else False,
                    summary=message,
                    user_id=self.target_user_id.id or self.env.user.id,
                )
                return _('Activity created on device "%s" for %s.') % (
                    reading.device_id.name, self.target_user_id.name or self.env.user.name)

            if self.action_type == 'call_method':
                model_name = self.action_model_id.model
                target = self.env[model_name].sudo()
                method = getattr(target, self.action_method, None)
                if not callable(method):
                    return _('Configuration error: method "%s" not found on model "%s".') % (
                        self.action_method, model_name)
                method(reading)
                return _('Called %s.%s(reading) for device "%s".') % (
                    model_name, self.action_method, reading.device_id.name)

            return _('No action configured.')
        except Exception as exc:  # noqa: BLE001 — alert firing must never raise into the ingestion flow
            _logger.exception('IoT alert rule "%s" action failed for device %s', self.name, reading.device_id.name)
            return _('Action failed: %s') % exc
