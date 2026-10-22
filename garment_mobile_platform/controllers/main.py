# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Mobile JSON REST API (SRS s.21-22, s.51 — Mobile API Architecture / API
Communication Standards / Mobile API Documentation).

AUTH SCHEME — pragmatic API-key auth, not JWT/OAuth2
-----------------------------------------------------
The SRS calls for OAuth 2.0 / JWT. This environment has no external
identity-provider/JWT-signing infrastructure to stand one up against, so a
pragmatic, working alternative is implemented instead: each
``garment.mobile.device`` row (see models/garment_mobile_device.py) carries
a server-generated ``api_key``. The client:

1. Calls ``POST /api/mobile/auth/login`` once with the user's normal Odoo
   credentials — this authenticates the user, registers/updates the
   calling device, opens a ``garment.mobile.session`` audit row, and
   returns that device's ``api_key``.
2. Sends that key on every subsequent call, either as the
   ``X-Mobile-Api-Key`` header or an ``api_key`` field in the request body
   / query string.

All routes below run under ``auth='public'`` (no native Odoo web-session
cookie is required) and perform their own authorization by resolving the
key to an active ``garment.mobile.device`` and executing the ERP call as
that device's linked ``res.users`` (``request.env(user=...)``), never as
the public/portal user. An invalid, missing or blocked-device key is
rejected with ``401``.

Every route returns plain JSON (not JSON-RPC envelope) so any HTTP client
(a real mobile app, curl, Postman) can call it directly.
"""

import json
import logging

from odoo import http, fields, _
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)


class GarmentMobileApiController(http.Controller):

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
        """Resolve the calling garment.mobile.device from the
        X-Mobile-Api-Key header, falling back to an api_key query/body
        field. Returns an empty recordset if the key is missing, unknown,
        or belongs to a blocked/inactive device."""
        api_key = request.httprequest.headers.get('X-Mobile-Api-Key')
        if not api_key:
            api_key = request.params.get('api_key')
        if not api_key and body:
            api_key = body.get('api_key')
        if not api_key:
            return request.env['garment.mobile.device'].sudo().browse()
        return request.env['garment.mobile.device'].sudo().search(
            [('api_key', '=', api_key), ('status', '=', 'active')], limit=1)

    @staticmethod
    def _authenticate_credentials(db, login, password):
        """Odoo 17.0 point releases have varied slightly in the exact
        ``res.users``/session authenticate signature (positional
        login/password vs. a credential dict). Try the modern form first
        and fall back to the classic one so this endpoint keeps working
        across 17.0 builds."""
        try:
            try:
                uid = request.session.authenticate(
                    db, {'login': login, 'password': password, 'type': 'password'})
            except TypeError:
                uid = request.session.authenticate(db, login, password)
        except AccessDenied:
            return False
        return uid

    # ------------------------------------------------------------------
    # 1. POST /api/mobile/auth/login  (SRS s.51 Authentication API)
    #    Real, working endpoint: authenticates the user, registers/updates
    #    the calling device, opens a session audit row, returns the API key.
    # ------------------------------------------------------------------
    @http.route('/api/mobile/auth/login', type='http', auth='public', methods=['POST'], csrf=False)
    def mobile_login(self, **kwargs):
        body = self._get_json_body()
        login = body.get('login')
        password = body.get('password')
        if not login or not password:
            return self._json_response(
                {'success': False, 'error': 'login and password are required'}, status=400)

        db = request.session.db or getattr(request, 'db', None)
        try:
            uid = self._authenticate_credentials(db, login, password)
        except Exception:
            _logger.exception('Mobile login authentication error for login=%s', login)
            uid = False
        if not uid:
            return self._json_response({'success': False, 'error': 'Invalid credentials'}, status=401)

        try:
            env = request.env(user=uid)
            user = env.user

            device_identifier = body.get('device_identifier')
            Device = env['garment.mobile.device'].sudo()
            domain = [('user_id', '=', uid)]
            if device_identifier:
                domain.append(('device_identifier', '=', device_identifier))
            device = Device.search(domain, limit=1)

            device_vals = {
                'name': body.get('device_name') or body.get('device_model') or (
                    '%s Device' % (user.name or login)),
                'user_id': uid,
                'app_type': body.get('app_type') or (device.app_type if device else 'production'),
                'platform': body.get('platform') or (device.platform if device else 'android'),
                'device_identifier': device_identifier or False,
                'device_model': body.get('device_model') or False,
                'os_version': body.get('os_version') or False,
                'app_version': body.get('app_version') or False,
                'push_token': body.get('push_token') or False,
                'status': 'active',
                'last_login': fields.Datetime.now(),
                'last_seen': fields.Datetime.now(),
                'last_ip': request.httprequest.remote_addr,
            }
            if device:
                device.write(device_vals)
            else:
                device = Device.create(device_vals)

            env['garment.mobile.session'].sudo().create({
                'device_id': device.id,
                'user_id': uid,
                'login_method': body.get('login_method') or 'password',
                'ip_address': request.httprequest.remote_addr,
            })

            employee = env['garment.hr.employee'].sudo().search([('user_id', '=', uid)], limit=1)

            return self._json_response({
                'success': True,
                'api_key': device.api_key,
                'device_id': device.id,
                'device_code': device.device_code,
                'user': {'id': user.id, 'name': user.name, 'login': user.login},
                'employee_id': employee.id if employee else False,
            })
        except Exception:
            _logger.exception('Mobile login post-authentication error for login=%s', login)
            return self._json_response({'success': False, 'error': 'Internal error'}, status=500)

    # ------------------------------------------------------------------
    # 2. GET /api/mobile/tna/tasks/today  (SRS s.12 Merchandising App —
    #    TNA Calendar; s.51 lists the pattern under Dashboard/Production API)
    #    Real, working endpoint against garment.tna.activity.
    # ------------------------------------------------------------------
    @http.route('/api/mobile/tna/tasks/today', type='http', auth='public', methods=['GET'], csrf=False)
    def mobile_tna_tasks_today(self, **kwargs):
        device = self._get_device()
        if not device:
            return self._json_response({'success': False, 'error': 'Invalid or missing API key'}, status=401)
        device.touch()

        try:
            env = request.env(user=device.user_id.id)
            Activity = env['garment.tna.activity'].sudo()
            today = fields.Date.context_today(Activity)

            domain = [
                ('planned_end_date', '=', today),
                ('status', 'in', ('pending', 'in_progress', 'delayed')),
            ]
            if not kwargs.get('all'):
                domain += ['|',
                           ('responsible_person_id', '=', device.user_id.id),
                           ('tna_id.merchandiser_id', '=', device.user_id.id)]

            activities = Activity.search(domain, order='priority desc, planned_end_date')

            data = [{
                'id': a.id,
                'tna_id': a.tna_id.id,
                'tna_number': a.tna_id.tna_number,
                'style': a.tna_id.style_id.style_name,
                'buyer': a.tna_id.buyer_id.name,
                'activity_name': a.activity_name,
                'category': a.category,
                'planned_end_date': a.planned_end_date.isoformat() if a.planned_end_date else False,
                'status': a.status,
                'progress_pct': a.progress_pct,
                'is_critical_path': a.is_critical_path,
            } for a in activities]

            return self._json_response(
                {'success': True, 'date': today.isoformat(), 'count': len(data), 'tasks': data})
        except Exception:
            _logger.exception('Mobile TNA tasks lookup failed for device %s', device.device_code)
            return self._json_response({'success': False, 'error': 'Internal error'}, status=500)

    # ------------------------------------------------------------------
    # 3. POST /api/mobile/production/entry  (SRS s.13-14 Production App /
    #    Line Supervisor "Enter Hourly Output"; s.24-25 Offline Production
    #    Entry sync)
    #    Real, working endpoint: creates a garment.production.entry and an
    #    offline-sync audit row.
    # ------------------------------------------------------------------
    @http.route('/api/mobile/production/entry', type='http', auth='public', methods=['POST'], csrf=False)
    def mobile_production_entry(self, **kwargs):
        body = self._get_json_body()
        device = self._get_device(body)
        if not device:
            return self._json_response({'success': False, 'error': 'Invalid or missing API key'}, status=401)
        device.touch()

        if not body.get('production_order_id'):
            return self._json_response(
                {'success': False, 'error': 'production_order_id is required'}, status=400)

        try:
            env = request.env(user=device.user_id.id)
            Entry = env['garment.production.entry'].sudo()

            vals = {
                'production_order_id': int(body['production_order_id']),
                'department': body.get('department') or 'sewing',
                'date': body.get('date') or fields.Date.to_string(fields.Date.context_today(Entry)),
                'shift': body.get('shift') or 'general',
                'entry_method': 'barcode' if body.get('barcode_scan') else 'tablet',
                'target_qty': float(body.get('target_qty') or 0.0),
                'output_qty': float(body.get('output_qty') or 0.0),
                'reject_qty': float(body.get('reject_qty') or 0.0),
                'rework_qty': float(body.get('rework_qty') or 0.0),
            }
            if body.get('work_order_id'):
                vals['work_order_id'] = int(body['work_order_id'])
            if body.get('line_id'):
                vals['line_id'] = int(body['line_id'])
            if body.get('employee_id'):
                vals['employee_id'] = int(body['employee_id'])
            elif device.employee_id:
                vals['employee_id'] = device.employee_id.id

            entry = Entry.create(vals)

            env['garment.mobile.offline.sync.log'].sudo().create({
                'device_id': device.id,
                'user_id': device.user_id.id,
                'sync_type': 'production_entry',
                'source_model': 'garment.production.entry',
                'source_res_id': entry.id,
                'offline_created_at': body.get('offline_created_at') or fields.Datetime.now(),
                'sync_status': 'synced',
                'payload': json.dumps(body),
            })

            return self._json_response({
                'success': True,
                'entry_id': entry.id,
                'entry_name': entry.name,
                'efficiency_pct': entry.efficiency_pct,
                'achievement_pct': entry.achievement_pct,
            })
        except (ValueError, TypeError) as exc:
            return self._json_response({'success': False, 'error': 'Invalid input: %s' % exc}, status=400)
        except Exception:
            _logger.exception('Mobile production entry failed for device %s', device.device_code)
            return self._json_response({'success': False, 'error': 'Internal error'}, status=500)

    # ------------------------------------------------------------------
    # 4. POST /api/mobile/qc/scan  (SRS s.15, s.28, s.41.4 — QC Mobile App /
    #    Barcode & QR System / QC Inspection Screen)
    #    Real, working endpoint: looks up the scanned garment.barcode,
    #    logs a garment.quality.inspection (+ defect line if any) and an
    #    offline-sync audit row.
    # ------------------------------------------------------------------
    @http.route('/api/mobile/qc/scan', type='http', auth='public', methods=['POST'], csrf=False)
    def mobile_qc_scan(self, **kwargs):
        body = self._get_json_body()
        device = self._get_device(body)
        if not device:
            return self._json_response({'success': False, 'error': 'Invalid or missing API key'}, status=401)
        device.touch()

        barcode_value = body.get('barcode_value')
        if not barcode_value:
            return self._json_response({'success': False, 'error': 'barcode_value is required'}, status=400)

        try:
            env = request.env(user=device.user_id.id)
            barcode = env['garment.barcode'].sudo().search(
                [('barcode_value', '=', barcode_value)], limit=1)
            if barcode:
                barcode.write({
                    'last_scanned_date': fields.Datetime.now(),
                    'last_scanned_by_id': device.user_id.id,
                })

            quantity = float(body.get('quantity') or 0.0)
            defect_qty = float(body.get('defect_qty') or 0.0)

            inspection_vals = {
                'inspection_type': body.get('inspection_type') or 'sewing_inline',
                'inspector_id': device.user_id.id,
                'quantity': quantity,
                'roll_number': barcode_value,
                'remarks': body.get('remarks') or False,
                'state': 'in_progress',
            }
            if barcode and barcode.material_id:
                inspection_vals['material_id'] = barcode.material_id.id
            if body.get('style_id'):
                inspection_vals['style_id'] = int(body['style_id'])

            Inspection = env['garment.quality.inspection'].sudo()
            inspection = Inspection.create(inspection_vals)

            if defect_qty:
                DefectCode = env['garment.quality.defect.code'].sudo()
                defect_code = (DefectCode.browse(int(body['defect_code_id']))
                                if body.get('defect_code_id') else DefectCode.search([], limit=1))
                if defect_code and defect_code.exists():
                    env['garment.quality.defect'].sudo().create({
                        'name': body.get('defect_name') or _('Mobile QC Scan Defect'),
                        'defect_code_id': defect_code.id,
                        'inspection_id': inspection.id,
                        'quantity': defect_qty,
                    })

            env['garment.mobile.offline.sync.log'].sudo().create({
                'device_id': device.id,
                'user_id': device.user_id.id,
                'sync_type': 'qc_inspection',
                'source_model': 'garment.quality.inspection',
                'source_res_id': inspection.id,
                'offline_created_at': body.get('offline_created_at') or fields.Datetime.now(),
                'sync_status': 'synced',
                'payload': json.dumps(body),
            })

            return self._json_response({
                'success': True,
                'inspection_id': inspection.id,
                'inspection_no': inspection.inspection_no,
                'barcode_found': bool(barcode),
                'quality_score': inspection.quality_score,
            })
        except (ValueError, TypeError) as exc:
            return self._json_response({'success': False, 'error': 'Invalid input: %s' % exc}, status=400)
        except Exception:
            _logger.exception('Mobile QC scan failed for device %s', device.device_code)
            return self._json_response({'success': False, 'error': 'Internal error'}, status=500)

    # ------------------------------------------------------------------
    # 5. GET /api/mobile/notifications  (SRS s.51 Notification API)
    #    Real, working endpoint over garment.mobile.push.notification —
    #    the log/queue this module owns. Delivery to the device (the actual
    #    push) is the documented stub, see garment_mobile_push_notification.py.
    # ------------------------------------------------------------------
    @http.route('/api/mobile/notifications', type='http', auth='public', methods=['GET'], csrf=False)
    def mobile_notifications(self, **kwargs):
        device = self._get_device()
        if not device:
            return self._json_response({'success': False, 'error': 'Invalid or missing API key'}, status=401)
        device.touch()

        try:
            env = request.env(user=device.user_id.id)
            Notification = env['garment.mobile.push.notification'].sudo()

            mark_read_id = kwargs.get('mark_read_id')
            if mark_read_id:
                notif = Notification.browse(int(mark_read_id))
                if notif.exists() and notif.user_id.id == device.user_id.id:
                    notif.action_mark_read()

            domain = [('user_id', '=', device.user_id.id)]
            if not kwargs.get('include_read'):
                domain.append(('state', '!=', 'read'))
            limit = int(kwargs.get('limit') or 50)
            notifications = Notification.search(domain, order='scheduled_date desc', limit=limit)

            data = [{
                'id': n.id,
                'notification_number': n.notification_number,
                'type': n.notification_type,
                'title': n.title,
                'body': n.body,
                'state': n.state,
                'scheduled_date': n.scheduled_date.isoformat() if n.scheduled_date else False,
                'related_model': n.related_model,
                'related_res_id': n.related_res_id,
            } for n in notifications]

            return self._json_response({'success': True, 'count': len(data), 'notifications': data})
        except (ValueError, TypeError) as exc:
            return self._json_response({'success': False, 'error': 'Invalid input: %s' % exc}, status=400)
        except Exception:
            _logger.exception('Mobile notifications lookup failed for device %s', device.device_code)
            return self._json_response({'success': False, 'error': 'Internal error'}, status=500)
