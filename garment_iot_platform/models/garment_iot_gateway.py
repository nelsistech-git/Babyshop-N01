# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""IoT Gateway Management (SRS s.7, s.36 — IoT Gateway model). The gateway
is the physical hub that sits between factory devices and Odoo in the
SRS's own architecture diagram: Machine -> Sensor -> IoT Gateway ->
API/MQTT -> Odoo ERP."""

import secrets

from odoo import api, fields, models, _


class GarmentIotGateway(models.Model):
    _name = 'garment.iot.gateway'
    _description = 'Garment IoT Gateway'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    gateway_code = fields.Char(string='Gateway Code', copy=False, readonly=True, default=lambda s: _('New'))
    name = fields.Char(string='Gateway Name', required=True, tracking=True,
                        help='e.g. "Sewing Floor-2 Gateway", "Cutting Section Hub".')

    protocol = fields.Selection([
        ('mqtt', 'MQTT'),
        ('modbus', 'Modbus'),
        ('http', 'HTTP / REST'),
        ('opc_ua', 'OPC-UA'),
        ('other', 'Other'),
    ], string='Communication Protocol', required=True, default='mqtt', tracking=True)

    location_id = fields.Many2one('garment.location', string='Warehouse Location',
                                   help='Set when the gateway sits inside a warehouse-tracked location.')
    location_note = fields.Char(string='Location / Floor',
                                 help='Free-text factory location, e.g. "Sewing Floor-2", when there is '
                                      'no garment.location record for it.')
    warehouse_id = fields.Many2one('garment.warehouse', string='Warehouse')

    ip_address = fields.Char(string='IP Address')
    port = fields.Integer(string='Port')
    mac_address = fields.Char(string='MAC Address')
    broker_endpoint = fields.Char(string='Broker / Endpoint URL',
                                   help='MQTT broker URL, Modbus host:port, or HTTP base URL this gateway '
                                        'reports through.')

    connection_status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
    ], string='Connection Status', default='offline', tracking=True)
    last_heartbeat = fields.Datetime(string='Last Heartbeat')
    installed_date = fields.Date(string='Installed On')

    api_key = fields.Char(string='Gateway API Key', copy=False, readonly=True,
                           help='Generated on creation. Sent by the gateway as the X-IoT-Gateway-Api-Key '
                                'header on POST /api/iot/gateway/heartbeat. See controllers/main.py.')

    device_ids = fields.One2many('garment.iot.device', 'gateway_id', string='Devices')
    device_count = fields.Integer(string='Devices', compute='_compute_device_count')
    online_device_count = fields.Integer(string='Devices Online', compute='_compute_device_count')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    _sql_constraints = [
        ('gateway_code_uniq', 'unique(gateway_code, company_id)', 'Gateway Code must be unique per company!'),
        ('api_key_uniq', 'unique(api_key)', 'Gateway API Key must be unique!'),
    ]

    @api.depends('device_ids.connection_status')
    def _compute_device_count(self):
        for rec in self:
            rec.device_count = len(rec.device_ids)
            rec.online_device_count = len(rec.device_ids.filtered(lambda d: d.connection_status == 'online'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('gateway_code', _('New')) == _('New'):
                vals['gateway_code'] = self.env['ir.sequence'].next_by_code('garment.iot.gateway') or _('New')
            if not vals.get('api_key'):
                vals['api_key'] = self._generate_api_key()
        return super().create(vals_list)

    @api.model
    def _generate_api_key(self):
        return secrets.token_hex(20)

    def action_generate_api_key(self):
        for rec in self:
            rec.api_key = self._generate_api_key()

    def action_mark_online(self):
        self.write({'connection_status': 'online', 'last_heartbeat': fields.Datetime.now()})

    def action_mark_offline(self):
        self.write({'connection_status': 'offline'})

    def action_view_devices(self):
        self.ensure_one()
        return {
            'name': _('Devices'), 'type': 'ir.actions.act_window', 'res_model': 'garment.iot.device',
            'view_mode': 'tree,form', 'domain': [('gateway_id', '=', self.id)],
            'context': {'default_gateway_id': self.id},
        }
