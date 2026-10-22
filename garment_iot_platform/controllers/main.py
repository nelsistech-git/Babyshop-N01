# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""IoT Data Ingestion Controller (SRS s.39 IoT API Architecture: POST
/api/iot/sensor/data; IOT-001/IOT-002/IOT-005 test cases).

AUTH SCHEME — pragmatic device API-key auth, matching garment_mobile_platform
--------------------------------------------------------------------------------
The SRS calls for encrypted communication / API token security (s.40) but,
like the Mobile Platform module, there is no external identity-provider/
JWT-signing infrastructure in this environment to stand a full OAuth2
server up against. The same pragmatic pattern used by
``garment_mobile_platform`` is reused here: each ``garment.iot.device``
(and ``garment.iot.gateway``) carries a server-generated ``api_key``. The
ingestion script running on (or next to) the physical gateway sends that
key on every call, either as the ``X-IoT-Api-Key`` header (device calls) /
``X-IoT-Gateway-Api-Key`` header (gateway calls) or an ``api_key`` field in
the request body.

All routes run under ``auth='public'`` (no native Odoo web-session cookie
required) and perform their own authorization by resolving the key to an
active ``garment.iot.device`` / ``garment.iot.gateway`` record and running
the ERP call with ``sudo()`` scoped to that one record's writes — never as
an arbitrary logged-in user. An invalid or missing key is rejected with
401.

Every route returns plain JSON (not the JSON-RPC envelope) so any HTTP
client — a real gateway/MQTT-bridge script, curl, Postman — can call it
directly."""

import json
import logging

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

VALID_READING_TYPES = (
    'temperature', 'humidity', 'vibration', 'air_quality', 'water', 'energy',
    'speed', 'count', 'status', 'rfid_scan', 'barcode_scan', 'other',
)


class GarmentIotIngestionController(http.Controller):

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _json_response(payload, status=200):
        return request.make_response(
            json.dumps(payload, default=str),
            status=status,
            headers=[('Content-Type', 'application/json')],
        )

    @staticmethod
    def _get_json_body():
        try:
            raw = request.httprequest.get_data()
            return json.loads(raw.decode('utf-8')) if raw else {}
        except (ValueError, UnicodeDecodeError):
            return {}

    @staticmethod
    def _get_device(body=None):
        """Resolve the calling garment.iot.device from the X-IoT-Api-Key
        header, falling back to an api_key body/query field. Returns an
        empty recordset if the key is missing or unknown. Devices are not
        gated on connection_status here — an offline/never-seen device is
        exactly the normal case for its very first ingest call."""
        api_key = request.httprequest.headers.get('X-IoT-Api-Key')
        if not api_key:
            api_key = request.params.get('api_key')
        if not api_key and body:
            api_key = body.get('api_key')
        if not api_key:
            return request.env['garment.iot.device'].sudo().browse()
        return request.env['garment.iot.device'].sudo().search([('api_key', '=', api_key)], limit=1)

    @staticmethod
    def _get_gateway(body=None):
        api_key = request.httprequest.headers.get('X-IoT-Gateway-Api-Key')
        if not api_key:
            api_key = request.params.get('api_key')
        if not api_key and body:
            api_key = body.get('api_key')
        if not api_key:
            return request.env['garment.iot.gateway'].sudo().browse()
        return request.env['garment.iot.gateway'].sudo().search([('api_key', '=', api_key)], limit=1)

    # ------------------------------------------------------------------
    # 1. POST /api/iot/ingest  (SRS s.39 Sensor Data API; IOT-002 "Receive
    #    sensor data -> Data stored"; IOT-005 "IoT alert -> Notification
    #    generated")
    #    Real, working endpoint: authenticates the device by API key,
    #    creates a garment.iot.reading and evaluates alert rules against it.
    # ------------------------------------------------------------------
    @http.route('/api/iot/ingest', type='http', auth='public', methods=['POST'], csrf=False)
    def iot_ingest(self, **kwargs):
        body = self._get_json_body()
        device = self._get_device(body)
        if not device:
            return self._json_response({'success': False, 'error': 'Invalid or missing device API key'}, status=401)

        reading_type = body.get('reading_type')
        if not reading_type:
            return self._json_response({'success': False, 'error': 'reading_type is required'}, status=400)
        if reading_type not in VALID_READING_TYPES:
            return self._json_response(
                {'success': False, 'error': 'reading_type must be one of: %s' % ', '.join(VALID_READING_TYPES)},
                status=400)

        try:
            value = float(body.get('value') or 0.0)
        except (TypeError, ValueError):
            return self._json_response({'success': False, 'error': 'value must be numeric'}, status=400)

        timestamp = False
        if body.get('timestamp'):
            try:
                timestamp = fields.Datetime.to_datetime(body['timestamp'])
            except Exception:
                return self._json_response(
                    {'success': False, 'error': 'timestamp must be "YYYY-MM-DD HH:MM:SS"'}, status=400)

        try:
            reading = device.sudo().record_reading(
                reading_type=reading_type,
                value=value,
                unit=body.get('unit'),
                text_value=body.get('text_value'),
                timestamp=timestamp,
                raw_payload=json.dumps(body),
            )
            alerts = reading.alert_log_ids
            return self._json_response({
                'success': True,
                'reading_id': reading.id,
                'device_id': device.id,
                'device_code': device.device_code,
                'connection_status': device.connection_status,
                'alerts_fired': [{
                    'alert_id': a.id,
                    'name': a.name,
                    'rule': a.rule_id.name,
                    'severity': a.severity,
                    'action_taken': a.action_taken,
                } for a in alerts],
            })
        except Exception:
            _logger.exception('IoT ingest failed for device %s', device.device_code)
            return self._json_response({'success': False, 'error': 'Internal error'}, status=500)

    # ------------------------------------------------------------------
    # 2. POST /api/iot/gateway/heartbeat  (SRS s.7 Gateway "Connection
    #    Status"; IOT-001 "Connect device -> Device online")
    #    Real, working endpoint: authenticates the gateway by API key and
    #    marks it online with a fresh last_heartbeat timestamp.
    # ------------------------------------------------------------------
    @http.route('/api/iot/gateway/heartbeat', type='http', auth='public', methods=['POST'], csrf=False)
    def iot_gateway_heartbeat(self, **kwargs):
        body = self._get_json_body()
        gateway = self._get_gateway(body)
        if not gateway:
            return self._json_response(
                {'success': False, 'error': 'Invalid or missing gateway API key'}, status=401)

        try:
            gateway.sudo().write({
                'connection_status': body.get('status') or 'online',
                'last_heartbeat': fields.Datetime.now(),
            })
            return self._json_response({
                'success': True,
                'gateway_id': gateway.id,
                'gateway_code': gateway.gateway_code,
                'connection_status': gateway.connection_status,
                'last_heartbeat': gateway.last_heartbeat,
            })
        except Exception:
            _logger.exception('IoT gateway heartbeat failed for gateway %s', gateway.gateway_code)
            return self._json_response({'success': False, 'error': 'Internal error'}, status=500)
