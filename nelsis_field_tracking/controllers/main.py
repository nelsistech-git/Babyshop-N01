"""Secure REST API used by the Nelsis Expense mobile app (Flutter).

* Every call is HTTPS JSON.  Authentication: `Authorization: Bearer <token>` (opaque, hashed at rest,
  revocable per device).  Database: `X-Odoo-Db` header (checked against dbfilter) or the single DB of the server.
  `GET /nelsis/api/v1/info` is public and lets the app discover the server / database from just an IP or URL.
* Idempotent writes (`uuid` generated on the phone) so an offline queue can safely retry.
* Business errors -> HTTP 400 {ok:false, error, message}; auth errors -> 401; rate limit -> 429.
"""
import functools
import inspect
import json
import logging
import threading
import time

import odoo
from odoo import api, http, SUPERUSER_ID, fields
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)
API = '/nelsis/api/v1'

_FAILS = {}
_LOCK = threading.Lock()
MAX_FAILS, WINDOW = 6, 900
IP_MAX_FAILS = 30          # one phone/IP guessing many usernames


def _throttled(key, limit=MAX_FAILS):
    with _LOCK:
        now = time.time()
        hits = [t for t in _FAILS.get(key, []) if now - t < WINDOW]
        _FAILS[key] = hits
        return len(hits) >= limit


def _fail(key):
    with _LOCK:
        now = time.time()
        if len(_FAILS) > 5000:  # never let the table grow without bound
            for k in [k for k, v in _FAILS.items() if not v or now - v[-1] >= WINDOW]:
                _FAILS.pop(k, None)
        _FAILS.setdefault(key, []).append(now)


def _json(data, status=200):
    return request.make_json_response(data, status=status, headers=[('Cache-Control', 'no-store')])


def _err(code, message, status=400):
    return _json({'ok': False, 'error': code, 'message': message}, status)


def _body():
    raw = request.httprequest.get_data()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


_DB_CACHE = {'t': 0.0, 'v': []}


def _allowed_dbs():
    """Databases this host may serve (respects dbfilter / db_name). Cached 60 s: the app calls often."""
    now = time.time()
    if now - _DB_CACHE['t'] < 60:
        return _DB_CACHE['v']
    try:
        dbs = odoo.service.db.list_dbs(True)   # force: needed internally, names are only *published* if list_db is on
    except Exception:  # noqa: BLE001
        dbs = []
    try:
        dbs = http.db_filter(dbs)
    except Exception:  # noqa: BLE001
        pass
    _DB_CACHE.update(t=now, v=list(dbs))
    return _DB_CACHE['v']


def _resolve_db():
    """-> (db, error_code).  Header X-Odoo-Db (validated against dbfilter), else the only database."""
    hdr = (request.httprequest.headers.get('X-Odoo-Db') or '').strip()
    allowed = _allowed_dbs()
    if hdr:
        # A caller-supplied name must never open a registry that dbfilter hides.
        return (hdr, None) if hdr in allowed else (None, 'bad_database')
    if request.db and (not allowed or request.db in allowed):
        return request.db, None
    if len(allowed) == 1:
        return allowed[0], None
    cfg = (odoo.tools.config['db_name'] or '').split(',')
    cfg = [d.strip() for d in cfg if d.strip()]
    if len(cfg) == 1:
        return cfg[0], None
    return None, 'no_database'


def _publish_db_names():
    """Only list database names when the admin allows it (Odoo `list_db`)."""
    if not odoo.tools.config['list_db']:
        return []
    return _allowed_dbs()


def _bearer():
    h = request.httprequest.headers.get('Authorization', '')
    return h[7:].strip() if h.lower().startswith('bearer ') else ''


def api_route(path, methods=('POST',), auth=True):
    """Route decorator: opens a cursor, authenticates the token and calls
    fn(self, env, employee, body, **url_params) -> dict (merged into {'ok': True, ...})."""
    def deco(fn):
        accepted = set(inspect.signature(fn).parameters)

        @http.route(API + path, type='http', auth='none', methods=list(methods), csrf=False)
        @functools.wraps(fn)
        def wrapper(self, **kw):
            # Cache-busters / future params from newer apps must never crash an older route handler.
            kw = {k: v for k, v in kw.items() if k in accepted}
            db, why = _resolve_db()
            if not db:
                if why == 'bad_database':
                    return _err('bad_database', 'Unknown database.', 404)
                return _err('no_database', 'Please choose a database.')
            try:
                registry = odoo.registry(db)
            except Exception:  # noqa: BLE001
                return _err('bad_database', 'Unknown database.', 404)
            try:
                with registry.cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    ip = request.httprequest.remote_addr
                    employee = env['hr.employee']
                    if auth:
                        user = env['nelsis.api.token'].verify(_bearer(), ip)
                        if not user:
                            return _err('unauthorized', 'Session expired. Please sign in again.', 401)
                        env = api.Environment(cr, user.id, {
                            'lang': user.lang, 'tz': user.tz,
                            'allowed_company_ids': user.company_ids.ids})
                        employee = env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
                        if not employee:
                            return _err('no_employee', 'Your user is not linked to an employee record.', 403)
                        # Day boundaries (today, month, week chart) must follow the employee's own time zone.
                        if employee.tz and employee.tz != user.tz:
                            env = env(context=dict(env.context, tz=employee.tz))
                            employee = employee.with_env(env)
                        ver = request.httprequest.headers.get('X-App-Version')
                        if ver and employee.nl_last_app_version != ver:
                            employee.sudo().write({'nl_last_app_version': ver[:20]})
                    result = fn(self, env, employee, _body(), **kw)
                    if not isinstance(result, dict):
                        return result
                    result.setdefault('ok', True)
                    result['server_time'] = fields.Datetime.to_string(fields.Datetime.now()).replace(' ', 'T') + 'Z'
                    return _json(result)
            except AccessDenied:
                return _err('unauthorized', 'Access denied.', 401)
            except AccessError as e:
                return _err('forbidden', str(e), 403)
            except (UserError, ValidationError) as e:
                return _err('business', e.args[0] if e.args else str(e), 400)
            except Exception:  # noqa: BLE001
                _logger.exception('Nelsis API error on %s', path)
                return _err('server_error', 'Unexpected server error.', 500)
        return wrapper
    return deco


class NelsisApi(http.Controller):

    # ---------------------------------------------------------------- public
    @api_route('/health', methods=('GET',), auth=False)
    def health(self, env, employee, body):
        return {'service': 'nelsis', 'version': '1.0'}

    @http.route(API + '/info', type='http', auth='none', methods=['GET'], csrf=False)
    def info(self, **kw):
        """Public discovery call used by the app's "connect by IP / URL" step.
        Needs no database and no login. Returns only what the login screen needs."""
        db, _why = _resolve_db()
        return _json({
            'ok': True, 'service': 'nelsis', 'version': '1.1', 'brand': 'Nelsis Tech',
            'databases': _publish_db_names(),
            # True -> the server can pick the database itself, the app need not send one.
            'db_auto': bool(db),
            'default_db': db or '',
        })

    @api_route('/auth/login', auth=False)
    def login(self, env, employee, body):
        login, password = (body.get('login') or '').strip(), body.get('password') or ''
        ip = request.httprequest.remote_addr
        key = '%s|%s' % (login.lower(), ip)
        if not login or not password:
            return _err('invalid', 'Login and password are required.')
        if _throttled(key) or _throttled('ip|%s' % ip, IP_MAX_FAILS):
            return _err('too_many_attempts', 'Too many attempts. Try again in 15 minutes.', 429)
        try:
            res = env['res.users'].authenticate(env.cr.dbname, login, password, {'interactive': False})
            uid = res['uid'] if isinstance(res, dict) else res
        except AccessDenied:
            _fail(key)
            _fail('ip|%s' % ip)
            return _err('bad_credentials', 'Wrong login or password.', 401)
        user = env['res.users'].browse(uid)
        if user.share:
            return _err('forbidden', 'This account type cannot use the app.', 403)
        # Two-factor (auth_totp): the password alone must never be enough. The app asks for the 6-digit code
        # after the server answers `otp_required`, then sends the same request again with `otp`.
        mfa = getattr(user, '_mfa_url', None)
        if mfa and mfa():
            otp = str(body.get('otp') or '').strip().replace(' ', '')
            if not otp:
                return _err('otp_required', 'Enter the 6-digit code from your authenticator app.', 401)
            check = getattr(user, '_totp_check', None)
            try:
                if not (check and otp.isdigit()):
                    raise AccessDenied()
                check(int(otp))
            except AccessDenied:
                _fail(key)
                _fail('ip|%s' % ip)
                return _err('bad_otp', 'Wrong or expired code. Try again.', 401)
        emp = env['hr.employee'].search([('user_id', '=', uid)], limit=1)
        if not emp:
            return _err('no_employee', 'Your user is not linked to an employee record.', 403)
        token = env['nelsis.api.token'].issue(user, body.get('device') or {}, ip)
        svc = env['nelsis.app.service'].with_user(user)
        return {'token': token, 'db': env.cr.dbname, 'profile': svc.profile(emp),
                'config': env['nelsis.config'].app_config()}

    @api_route('/auth/logout')
    def logout(self, env, employee, body):
        env['nelsis.api.token'].revoke(_bearer())
        return {}

    # ---------------------------------------------------------------- profile / config
    @api_route('/me', methods=('GET',))
    def me(self, env, employee, body):
        svc = env['nelsis.app.service']
        return {'profile': svc.profile(employee), 'config': env['nelsis.config'].app_config()}

    @api_route('/dashboard', methods=('GET',))
    def dashboard(self, env, employee, body):
        return env['nelsis.app.service'].dashboard(employee)

    @api_route('/sites', methods=('GET',))
    def sites(self, env, employee, body):
        sites = env['hr.attendance']._nl_sites_for(employee)
        return {'sites': [{'id': s.id, 'name': s.name, 'lat': s.latitude, 'lng': s.longitude,
                           'radius': s.radius_m} for s in sites]}

    # ---------------------------------------------------------------- announcements / push
    @api_route('/announcements', methods=('GET',))
    def announcements(self, env, employee, body, limit='30'):
        """Announcements written in Odoo (Field Force > Announcements) that this employee may see."""
        Ann = env['nelsis.announcement'].sudo()
        recs = Ann.search(Ann.visible_domain(employee), order='sent_date desc, id desc',
                          limit=max(1, min(int(limit or 30), 100)))
        iso = lambda d: fields.Datetime.to_string(d).replace(' ', 'T') + 'Z' if d else None
        return {'items': [{'id': a.id, 'title': a.name, 'body': a.body or '', 'date': iso(a.sent_date),
                           'expires': iso(a.expire_date), 'by': a.sent_by_id.name or ''} for a in recs]}

    @api_route('/push/register')
    def push_register(self, env, employee, body):
        env['nelsis.api.token'].set_push_token(_bearer(), body.get('fcm_token'))
        return {}

    # ---------------------------------------------------------------- manager: team status
    @api_route('/team', methods=('GET',))
    def team(self, env, employee, body, date=''):
        """Who is punched in / online right now. Managers only (group Field Force / Administrator)."""
        if not env.user.has_group('nelsis_field_tracking.group_nelsis_manager'):
            return _err('forbidden', 'Only Field Force administrators can see the team.', 403)
        data = env['nelsis.location.log'].get_live_map_data({'date': date or False})
        keep = ('id', 'name', 'job', 'department', 'lat', 'lng', 'battery', 'last_seen', 'online',
                'attendance', 'check_in', 'check_out', 'distance_km', 'flags')
        return {
            'summary': data.get('summary', {}),
            'date': data.get('date'),
            'items': [{k: e.get(k) for k in keep} for e in data.get('employees', [])],
        }

    # ---------------------------------------------------------------- attendance
    @api_route('/attendance/status', methods=('GET',))
    def att_status(self, env, employee, body):
        att = env['hr.attendance'].sudo().search([('employee_id', '=', employee.id)], order='check_in desc', limit=1)
        svc = env['nelsis.app.service']
        return {'punched_in': bool(att and not att.check_out), 'last': svc.att_dict(att) if att else None}

    @api_route('/attendance/punch')
    def att_punch(self, env, employee, body):
        kind = body.get('type')
        if kind not in ('in', 'out'):
            return _err('invalid', 'type must be "in" or "out".')
        att = env['hr.attendance'].nl_punch(employee, kind, body)
        return {'attendance': env['nelsis.app.service'].att_dict(att), 'punched_in': not att.check_out}

    @api_route('/attendance/history', methods=('GET',))
    def att_history(self, env, employee, body, limit='30', offset='0'):
        limit = max(1, min(int(limit), 100))
        recs = env['hr.attendance'].sudo().search([('employee_id', '=', employee.id)],
                                                  order='check_in desc', limit=limit, offset=int(offset))
        svc = env['nelsis.app.service']
        return {'items': [svc.att_dict(a) for a in recs]}

    # ---------------------------------------------------------------- tracking
    @api_route('/location/batch')
    def loc_batch(self, env, employee, body):
        if not employee.nl_tracking_enabled:
            return {'accepted': [], 'duplicates': [], 'rejected': [], 'tracking': False}
        points = (body.get('points') or [])[:500]
        res = env['nelsis.location.log'].ingest(employee, points)
        if body.get('events'):
            res['events'] = env['nelsis.presence.log'].ingest(employee, body['events'][:200])
        res['tracking'] = True
        return res
