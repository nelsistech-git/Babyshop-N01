#!/usr/bin/env python3
"""
QuickCRM AMI Bridge
------------------------------------------------------------------
Standalone daemon that holds the persistent Asterisk Manager
Interface (AMI) connection, listens to the live event stream, and
forwards the events that matter (ring/answer/hold/hangup/recording)
to the crm_omnichannel_voip_asterisk Odoo module's webhook as JSON.

Run this as its own process (pm2 / systemd / docker) next to Odoo -
NOT inside an Odoo worker, since AMI needs one connection held open
indefinitely and Odoo's HTTP workers are request/response, not
long-lived.

Usage:
    pip install requests
    AMI_HOST=pbx.yourdomain.com AMI_PORT=5038 \
    AMI_USERNAME=quickcrm AMI_SECRET=secret \
    ODOO_WEBHOOK_URL=https://yourcrm.example.com/omni/webhook/asterisk \
    ODOO_WEBHOOK_SECRET=same-as-ami_webhook_secret-on-the-channel \
    CHANNEL_NAME="IP Calling" \
    HEALTH_PORT=8088 \
    python3 ami_bridge.py

HEALTH_PORT (optional, default 8088): serves GET /health as
{"ok": true, "ami_connected": true|false} on a plain HTTP server so
Odoo (crm_omnichannel_connect_center's Settings > Connections screen)
can tell "the bridge process is running" apart from "the bridge is
actually connected to Asterisk right now" - both can silently drift
out of sync with the underlying AMI socket otherwise.
"""
import json
import logging
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO'),
                     format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('ami_bridge')

AMI_HOST = os.environ['AMI_HOST']
AMI_PORT = int(os.environ.get('AMI_PORT', 5038))
AMI_USERNAME = os.environ['AMI_USERNAME']
AMI_SECRET = os.environ['AMI_SECRET']
ODOO_WEBHOOK_URL = os.environ['ODOO_WEBHOOK_URL']
ODOO_WEBHOOK_SECRET = os.environ['ODOO_WEBHOOK_SECRET']
CHANNEL_NAME = os.environ.get('CHANNEL_NAME', '')
HEALTH_PORT = int(os.environ.get('HEALTH_PORT', 8088))

_TERMINATOR = '\r\n\r\n'

# Flipped by connect_and_listen()/run_forever() below; read by the health
# HTTP handler on every request - simple enough not to need a lock for a
# single bool written from one thread and read from another.
_STATE = {'ami_connected': False}


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.rstrip('/') != '/health':
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({'ok': True, 'ami_connected': _STATE['ami_connected']}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # keep the health-check pings out of the main log


def start_health_server():
    server = HTTPServer(('0.0.0.0', HEALTH_PORT), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    log.info('Health endpoint listening on :%s/health', HEALTH_PORT)


def post_event(event_vals):
    body = dict(event_vals)
    if CHANNEL_NAME:
        body['channel_name'] = CHANNEL_NAME
    try:
        resp = requests.post(
            ODOO_WEBHOOK_URL, json=body,
            headers={'X-Bridge-Api-Key': ODOO_WEBHOOK_SECRET, 'Content-Type': 'application/json'},
            timeout=10,
        )
        if resp.status_code >= 400:
            log.warning('Odoo webhook returned HTTP %s: %s', resp.status_code, resp.text[:300])
    except requests.exceptions.RequestException as exc:
        log.warning('Failed to POST event to Odoo: %s', exc)


def parse_block(block):
    """Parse one AMI text block (Event: ...\\r\\nKey: value\\r\\n...) into a dict,
    lower-casing keys so downstream code doesn't care about Asterisk's
    inconsistent capitalization across versions."""
    result = {}
    for line in block.split('\r\n'):
        if ':' in line:
            key, _, value = line.partition(':')
            result[key.strip().lower()] = value.strip()
    return result


def translate_and_forward(ami_event):
    """Map a subset of raw AMI events to the small vocabulary our webhook
    understands. Extend this as you enable more Asterisk event types."""
    event_name = ami_event.get('event', '')
    uniqueid = ami_event.get('uniqueid')
    quickcrm_call_id = None
    # We tag originated calls with Variable: QUICKCRM_CALL_ID=<id>; Asterisk
    # echoes channel variables back on many events depending on config -
    # if present, use it so we update the exact record we created.
    for key, value in ami_event.items():
        if key.startswith('variable') and 'QUICKCRM_CALL_ID' in value:
            quickcrm_call_id = value.split('=', 1)[-1].strip()

    if event_name == 'Newchannel' and ami_event.get('channelstatedesc') == 'Ring':
        post_event({'event': 'ring', 'uniqueid': uniqueid,
                    'caller_number': ami_event.get('calleridnum'),
                    'quickcrm_call_id': quickcrm_call_id})
    elif event_name == 'Bridge' or (event_name == 'Newstate' and ami_event.get('channelstatedesc') == 'Up'):
        post_event({'event': 'answer', 'uniqueid': uniqueid, 'quickcrm_call_id': quickcrm_call_id})
    elif event_name == 'Hold':
        post_event({'event': 'hold', 'uniqueid': uniqueid, 'quickcrm_call_id': quickcrm_call_id})
    elif event_name == 'Unhold':
        post_event({'event': 'unhold', 'uniqueid': uniqueid, 'quickcrm_call_id': quickcrm_call_id})
    elif event_name == 'Hangup':
        post_event({'event': 'hangup', 'uniqueid': uniqueid, 'quickcrm_call_id': quickcrm_call_id})
    elif event_name == 'MonitorStop' and ami_event.get('recordingfile'):
        # Adjust this URL scheme to wherever your recordings are actually
        # served from (Asterisk local disk via nginx, S3, etc.).
        recording_url = os.environ.get('RECORDING_BASE_URL', '') + ami_event['recordingfile']
        post_event({'event': 'recording_ready', 'uniqueid': uniqueid,
                    'quickcrm_call_id': quickcrm_call_id, 'recording_url': recording_url})


def run_forever():
    while True:
        try:
            connect_and_listen()
        except Exception as exc:
            _STATE['ami_connected'] = False
            log.warning('AMI connection lost/failed (%s); reconnecting in 5s.', exc)
            time.sleep(5)


def connect_and_listen():
    with socket.create_connection((AMI_HOST, AMI_PORT), timeout=15) as sock:
        sock.settimeout(60)
        banner = sock.recv(1024)
        log.info('Connected: %s', banner.decode(errors='replace').strip())

        login = f'Action: Login\r\nUsername: {AMI_USERNAME}\r\nSecret: {AMI_SECRET}\r\nEvents: on\r\n\r\n'
        sock.sendall(login.encode('utf-8'))
        _STATE['ami_connected'] = True

        buf = ''
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                continue  # just a keepalive-ish poll interval, connection is fine
            if not chunk:
                _STATE['ami_connected'] = False
                raise ConnectionError('AMI closed the connection.')
            buf += chunk.decode('utf-8', errors='replace')
            while _TERMINATOR in buf:
                block, _, buf = buf.partition(_TERMINATOR)
                parsed = parse_block(block)
                if parsed.get('event'):
                    log.debug('AMI event: %s', parsed)
                    try:
                        translate_and_forward(parsed)
                    except Exception:
                        log.exception('Failed translating/forwarding AMI event: %s', parsed)


if __name__ == '__main__':
    log.info('Starting QuickCRM AMI bridge against %s:%s', AMI_HOST, AMI_PORT)
    start_health_server()
    run_forever()
