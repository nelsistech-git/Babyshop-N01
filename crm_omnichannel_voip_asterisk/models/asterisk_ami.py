# -*- coding: utf-8 -*-
"""
Minimal, dependency-free Asterisk Manager Interface (AMI) client.

AMI is a simple line-based, colon-separated text protocol over a plain
TCP socket - no external library is needed for the handful of actions
we use here (Login / Originate / Logoff), so this avoids pulling in a
heavier async AMI dependency just for synchronous click-to-call use
from inside an Odoo request.

For *receiving* the full live event stream (ring/answer/hangup) you
still want a persistent connection, which is what bridge/ami_bridge.py
(a separate long-running process) is for - this class is only used for
short-lived synchronous actions like "originate one call and return".
"""
import logging
import socket
import time

_logger = logging.getLogger(__name__)

_TERMINATOR = b'\r\n\r\n'


class AsteriskAMIError(Exception):
    pass


class AsteriskAMI:
    """Usage:
        with AsteriskAMI(host, port, username, secret) as ami:
            ami.originate(channel='PJSIP/1001', context='from-internal',
                           extension='+8801XXXXXXXXX', priority=1,
                           caller_id='QuickCRM <1001>')
    """

    def __init__(self, host, port, username, secret, timeout=10):
        self.host = host
        self.port = port or 5038
        self.username = username
        self.secret = secret
        self.timeout = timeout
        self._sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.settimeout(self.timeout)
        banner = self._sock.recv(1024)  # e.g. "Asterisk Call Manager/x.x.x\r\n"
        if not banner.startswith(b'Asterisk Call Manager'):
            self.close()
            raise AsteriskAMIError('Unexpected AMI banner: %r' % banner)
        response = self._send_action({
            'Action': 'Login',
            'Username': self.username,
            'Secret': self.secret,
        })
        if response.get('Response') != 'Success':
            self.close()
            raise AsteriskAMIError('AMI login failed: %s' % response.get('Message', 'unknown error'))

    def close(self):
        if self._sock:
            try:
                self._send_action({'Action': 'Logoff'}, expect_response=False)
            except Exception:
                pass
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def originate(self, channel, context, extension, priority=1, caller_id=None,
                  variables=None, timeout_ms=30000, async_=True):
        """Ask Asterisk to bridge `channel` (e.g. PJSIP/1001, the agent's
        extension) into the dialplan at context/extension/priority (the
        customer's number). Asterisk itself places both legs; Odoo just
        requests it and moves on (async_=True -> events come back later
        via ami_bridge.py, not on this connection)."""
        action = {
            'Action': 'Originate',
            'Channel': channel,
            'Context': context,
            'Exten': extension,
            'Priority': str(priority),
            'Timeout': str(timeout_ms),
            'Async': 'true' if async_ else 'false',
        }
        if caller_id:
            action['CallerID'] = caller_id
        if variables:
            for i, (key, value) in enumerate(variables.items()):
                action[f'Variable'] = f'{key}={value}' if i == 0 else action.get('Variable', '') + f',{key}={value}'
        response = self._send_action(action)
        if response.get('Response') not in ('Success',):
            raise AsteriskAMIError('Originate failed: %s' % response.get('Message', 'unknown error'))
        return response

    def hangup(self, channel):
        response = self._send_action({'Action': 'Hangup', 'Channel': channel})
        if response.get('Response') != 'Success':
            raise AsteriskAMIError('Hangup failed: %s' % response.get('Message', 'unknown error'))
        return response

    # =====================================================================
    # INTERNAL
    # =====================================================================
    def _send_action(self, fields_dict, expect_response=True):
        if not self._sock:
            raise AsteriskAMIError('Not connected.')
        lines = ''.join(f'{k}: {v}\r\n' for k, v in fields_dict.items())
        self._sock.sendall((lines + '\r\n').encode('utf-8'))
        if not expect_response:
            return {}
        return self._read_response()

    def _read_response(self, deadline_seconds=None):
        deadline_seconds = deadline_seconds or self.timeout
        start = time.time()
        buf = b''
        while _TERMINATOR not in buf:
            if time.time() - start > deadline_seconds:
                raise AsteriskAMIError('Timed out waiting for AMI response.')
            chunk = self._sock.recv(4096)
            if not chunk:
                raise AsteriskAMIError('AMI connection closed unexpectedly.')
            buf += chunk
        block, _, _rest = buf.partition(_TERMINATOR)
        result = {}
        for line in block.decode('utf-8', errors='replace').split('\r\n'):
            if ':' in line:
                key, _, value = line.partition(':')
                result[key.strip()] = value.strip()
        return result
