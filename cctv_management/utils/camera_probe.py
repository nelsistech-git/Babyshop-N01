# -*- coding: utf-8 -*-
"""Read the real stream settings (bitrate, fps, resolution, model) from a camera / NVR.

Pure python (requests + stdlib) so it can be unit-tested without Odoo.
Order of attempts: brand API (Hikvision ISAPI / Dahua CGI) -> ONVIF media service -> ffprobe on the RTSP URL.
Every function returns a plain dict; on failure it raises ProbeError with a human readable message.
"""
import base64
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

_logger = logging.getLogger(__name__)
TIMEOUT = 6


class ProbeError(Exception):
    pass


# ----------------------------------------------------------------------------- helpers
def resolution_bucket(width, height):
    """Map a pixel size to the cctv.camera.resolution selection keys."""
    height = int(height or 0)
    if not height:
        return False
    if height <= 720:
        return '720p'
    if height <= 1088:
        return '1080p'
    if height < 2000:
        return '4mp'
    return '4k'


def split_target(rtsp_url, ip_address, username, password):
    """Return (host, user, password, rtsp_path) from the camera record values."""
    host, user, pwd, path = ip_address or '', username or '', password or '', ''
    if rtsp_url:
        p = urlparse(rtsp_url)
        host = host or (p.hostname or '')
        user = user or unquote(p.username or '')
        pwd = pwd or unquote(p.password or '')
        path = p.path + (('?' + p.query) if p.query else '')
    if not host:
        raise ProbeError('No IP address / RTSP host configured.')
    return host, user, pwd, path


def _strip_ns(root):
    for el in root.iter():
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
    return root


def _get(url, user, pwd):
    """GET with Digest first (what Hikvision/Dahua use), Basic as fallback."""
    last = None
    for auth in (HTTPDigestAuth(user, pwd), HTTPBasicAuth(user, pwd)):
        try:
            r = requests.get(url, auth=auth, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise ProbeError('Cannot reach %s: %s' % (url.split('?')[0], exc))
        if r.status_code == 401:
            last = r
            continue
        return r
    raise ProbeError('Camera rejected the username/password (HTTP 401).')


# ----------------------------------------------------------------------------- Hikvision
def probe_hikvision(host, user, pwd, rtsp_path, http_port=80):
    m = re.search(r'/Streaming/[Cc]hannels/(\d+)', rtsp_path or '')
    channel = m.group(1) if m else '101'
    base = 'http://%s:%s' % (host, http_port or 80)
    r = _get(base + '/ISAPI/Streaming/channels/%s' % channel, user, pwd)
    if r.status_code != 200:
        raise ProbeError('Hikvision ISAPI answered HTTP %s for channel %s.' % (r.status_code, channel))
    try:
        root = _strip_ns(ET.fromstring(r.content))
    except ET.ParseError:
        raise ProbeError('Hikvision ISAPI returned something that is not XML.')
    video = root.find('Video')
    if video is None:
        raise ProbeError('No <Video> block in the Hikvision channel answer.')

    def num(tag):
        el = video.find(tag)
        try:
            return int(float(el.text)) if el is not None and el.text else 0
        except ValueError:
            return 0

    out = {'width': num('videoResolutionWidth'), 'height': num('videoResolutionHeight')}
    mfr = num('maxFrameRate')                      # hundredths of a frame/s (2500 = 25 fps)
    out['fps'] = int(round(mfr / 100.0)) if mfr > 200 else mfr
    out['bitrate_kbps'] = num('constantBitRate') or num('vbrUpperCap')
    audio = root.find('Audio/enabled')
    if audio is not None and audio.text:
        out['audio'] = audio.text.strip().lower() == 'true'
    try:
        di = _get(base + '/ISAPI/System/deviceInfo', user, pwd)
        if di.status_code == 200:
            dr = _strip_ns(ET.fromstring(di.content))
            model = dr.find('model')
            if model is not None and model.text:
                out['model'] = model.text.strip()
    except (ProbeError, ET.ParseError):
        pass
    out['source'] = 'Hikvision ISAPI (channel %s)' % channel
    return out


# ----------------------------------------------------------------------------- Dahua
def probe_dahua(host, user, pwd, rtsp_path, http_port=80):
    m = re.search(r'channel=(\d+)', rtsp_path or '')
    idx = max(int(m.group(1)) - 1, 0) if m else 0
    sub = re.search(r'subtype=(\d+)', rtsp_path or '')
    main = 'MainFormat' if not sub or sub.group(1) == '0' else 'ExtraFormat'
    base = 'http://%s:%s' % (host, http_port or 80)
    r = _get(base + '/cgi-bin/configManager.cgi?action=getConfig&name=Encode', user, pwd)
    if r.status_code != 200:
        raise ProbeError('Dahua CGI answered HTTP %s.' % r.status_code)
    prefix = 'table.Encode[%d].%s[0].' % (idx, main)
    vals = {}
    for line in r.text.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            vals[k.strip()] = v.strip()
    out = {}
    res = vals.get(prefix + 'Video.resolution') or vals.get(prefix + 'Video.Resolution')
    if res and 'x' in res.lower():
        w, h = re.split('[xX]', res)[:2]
        out['width'], out['height'] = int(w), int(h)
    if vals.get(prefix + 'Video.FPS'):
        out['fps'] = int(float(vals[prefix + 'Video.FPS']))
    if vals.get(prefix + 'Video.BitRate'):
        out['bitrate_kbps'] = int(float(vals[prefix + 'Video.BitRate']))
    if not out:
        raise ProbeError('Dahua answer did not contain Encode[%d] video settings.' % idx)
    out['source'] = 'Dahua CGI (channel %d)' % (idx + 1)
    return out


# ----------------------------------------------------------------------------- ONVIF (any brand)
_SOAP = ('<?xml version="1.0" encoding="utf-8"?>'
         '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">%s<s:Body>%s</s:Body></s:Envelope>')


def _wsse(user, pwd):
    nonce = os.urandom(16)
    created = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    digest = base64.b64encode(hashlib.sha1(nonce + created.encode() + pwd.encode()).digest()).decode()
    return ('<s:Header><Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">'
            '<UsernameToken><Username>%s</Username>'
            '<Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">%s</Password>'
            '<Nonce>%s</Nonce>'
            '<Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">%s</Created>'
            '</UsernameToken></Security></s:Header>') % (user, digest, base64.b64encode(nonce).decode(), created)


def probe_onvif(host, user, pwd, rtsp_path, http_port=80):
    body = '<GetProfiles xmlns="http://www.onvif.org/ver10/media/wsdl"/>'
    xml = _SOAP % (_wsse(user, pwd), body)
    last = 'no ONVIF media service answered'
    for path in ('/onvif/media_service', '/onvif/Media', '/onvif/media'):
        url = 'http://%s:%s%s' % (host, http_port or 80, path)
        try:
            r = requests.post(url, data=xml.encode(), timeout=TIMEOUT,
                              headers={'Content-Type': 'application/soap+xml; charset=utf-8'})
        except requests.RequestException as exc:
            last = str(exc)
            continue
        if r.status_code != 200:
            last = 'HTTP %s on %s' % (r.status_code, path)
            continue
        try:
            root = _strip_ns(ET.fromstring(r.content))
        except ET.ParseError:
            continue
        profiles = [p for p in root.iter('Profiles')]
        best = None
        for prof in profiles:
            enc = prof.find('VideoEncoderConfiguration')
            if enc is None:
                continue
            w = enc.findtext('Resolution/Width')
            h = enc.findtext('Resolution/Height')
            if not (w and h):
                continue
            cand = {'width': int(w), 'height': int(h),
                    'fps': int(float(enc.findtext('RateControl/FrameRateLimit') or 0)),
                    'bitrate_kbps': int(float(enc.findtext('RateControl/BitrateLimit') or 0))}
            if best is None or cand['width'] * cand['height'] > best['width'] * best['height']:
                best = cand            # the main stream is the biggest profile
        if best:
            best['source'] = 'ONVIF media profile'
            return best
    raise ProbeError('ONVIF probe failed: %s' % last)


# ----------------------------------------------------------------------------- ffprobe fallback
def probe_ffprobe(rtsp_url):
    exe = shutil.which('ffprobe')
    if not exe:
        raise ProbeError('ffprobe is not installed on the Odoo server.')
    if not rtsp_url:
        raise ProbeError('No RTSP URL for ffprobe.')
    try:
        proc = subprocess.run(
            [exe, '-v', 'error', '-rtsp_transport', 'tcp', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height,avg_frame_rate,bit_rate', '-of', 'json', rtsp_url],
            capture_output=True, timeout=20, text=True)
    except subprocess.TimeoutExpired:
        raise ProbeError('ffprobe timed out opening the RTSP stream.')
    if proc.returncode != 0:
        raise ProbeError('ffprobe failed: %s' % (proc.stderr or '').strip()[:200])
    streams = json.loads(proc.stdout or '{}').get('streams') or []
    if not streams:
        raise ProbeError('ffprobe found no video stream.')
    s = streams[0]
    out = {'width': int(s.get('width') or 0), 'height': int(s.get('height') or 0), 'source': 'ffprobe (RTSP)'}
    afr = s.get('avg_frame_rate') or '0/1'
    try:
        n, d = afr.split('/')
        out['fps'] = int(round(float(n) / float(d))) if float(d) else 0
    except (ValueError, ZeroDivisionError):
        pass
    if s.get('bit_rate') and str(s['bit_rate']).isdigit():
        out['bitrate_kbps'] = int(int(s['bit_rate']) / 1000)
    return out


# ----------------------------------------------------------------------------- entry point
def probe(brand, rtsp_url, ip_address, username, password, http_port=80):
    """Try the best method for the brand, then the generic ones. Returns the first success."""
    host, user, pwd, path = split_target(rtsp_url, ip_address, username, password)
    attempts = []
    if brand == 'hikvision':
        attempts.append(lambda: probe_hikvision(host, user, pwd, path, http_port))
    elif brand == 'dahua':
        attempts.append(lambda: probe_dahua(host, user, pwd, path, http_port))
    attempts.append(lambda: probe_onvif(host, user, pwd, path, http_port))
    attempts.append(lambda: probe_ffprobe(rtsp_url))
    errors = []
    for fn in attempts:
        try:
            result = fn()
            if result.get('bitrate_kbps') or result.get('fps') or result.get('width'):
                return result
        except ProbeError as exc:
            errors.append(str(exc))
        except Exception as exc:                      # never let a camera quirk break the cron
            _logger.exception('camera probe crashed')
            errors.append('%s: %s' % (type(exc).__name__, exc))
    raise ProbeError(' | '.join(errors) or 'Camera did not answer.')
