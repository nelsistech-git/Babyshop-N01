import base64
import io
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from ..utils.geo import haversine_m, valid_coords
from ..utils.geocode import reverse_geocode
from .location_log import parse_dt

_logger = logging.getLogger(__name__)

MAX_OFFLINE_PUNCH_SEC = 3 * 86400


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    # --- check in
    nl_in_accuracy = fields.Float(string='In Accuracy (m)')
    nl_in_mock = fields.Boolean(string='In: Mock GPS')
    nl_in_offline = fields.Boolean(string='In: Punched Offline')
    nl_in_device_time = fields.Datetime(string='In: Phone Time')
    nl_in_trust = fields.Selection([('ok', 'On time'), ('delayed', 'Delayed (offline)'), ('drift', 'Clock mismatch')],
                                   string='In: Time Check')
    nl_in_site_id = fields.Many2one('nelsis.work.site', string='In: Matched Site')
    nl_in_distance_m = fields.Float(string='In: Distance to Site (m)')
    nl_in_address = fields.Char(string='In: Address')
    nl_in_photo = fields.Image(string='In: Selfie', max_width=640, max_height=640)
    nl_in_uuid = fields.Char(copy=False, index=True)
    nl_in_genuine = fields.Boolean(string='In: Genuine', compute='_compute_nl_genuine', store=True)
    # --- check out
    nl_out_accuracy = fields.Float(string='Out Accuracy (m)')
    nl_out_mock = fields.Boolean(string='Out: Mock GPS')
    nl_out_offline = fields.Boolean(string='Out: Punched Offline')
    nl_out_device_time = fields.Datetime(string='Out: Phone Time')
    nl_out_trust = fields.Selection([('ok', 'On time'), ('delayed', 'Delayed (offline)'), ('drift', 'Clock mismatch')],
                                    string='Out: Time Check')
    nl_out_site_id = fields.Many2one('nelsis.work.site', string='Out: Matched Site')
    nl_out_distance_m = fields.Float(string='Out: Distance to Site (m)')
    nl_out_address = fields.Char(string='Out: Address')
    nl_out_photo = fields.Image(string='Out: Selfie', max_width=640, max_height=640)
    nl_out_uuid = fields.Char(copy=False, index=True)
    nl_out_genuine = fields.Boolean(string='Out: Genuine', compute='_compute_nl_genuine', store=True)

    nl_geo_status = fields.Selection([
        ('none', 'No GPS (manual)'), ('inside', 'Inside work site'), ('field', 'Field staff'),
        ('outside', 'Outside work site'), ('no_site', 'No site configured'), ('mock', 'Mock GPS')],
        string='Location Check', compute='_compute_nl_geo_status', store=True)
    nl_is_app = fields.Boolean(string='Mobile Punch', compute='_compute_nl_geo_status', store=True)

    @api.depends('nl_in_mock', 'nl_in_trust', 'nl_out_mock', 'nl_out_trust', 'check_out')
    def _compute_nl_genuine(self):
        for a in self:
            a.nl_in_genuine = not a.nl_in_mock and a.nl_in_trust != 'drift'
            a.nl_out_genuine = not a.nl_out_mock and a.nl_out_trust != 'drift'

    @api.depends('in_latitude', 'in_longitude', 'nl_in_site_id', 'nl_in_distance_m', 'nl_in_mock',
                 'nl_out_mock', 'employee_id.nl_field_staff', 'nl_in_uuid', 'nl_in_device_time')
    def _compute_nl_geo_status(self):
        for a in self:
            a.nl_is_app = bool(a.nl_in_uuid or a.nl_in_device_time)
            if not a.nl_is_app:
                a.nl_geo_status = 'none'
            elif a.nl_in_mock or a.nl_out_mock:
                a.nl_geo_status = 'mock'
            elif a.employee_id.nl_field_staff:
                a.nl_geo_status = 'field'
            elif a.nl_in_site_id:
                a.nl_geo_status = 'inside'
            elif a.nl_in_distance_m and a.nl_in_distance_m > 0:
                a.nl_geo_status = 'outside'
            else:
                a.nl_geo_status = 'no_site'

    # ------------------------------------------------------------------ punch logic
    @api.model
    def _nl_sites_for(self, employee):
        """Work sites this employee may punch at: the ones assigned on the employee, otherwise every site of
        the employee's company that is open to all or lists the employee. Done in Python on purpose: a
        many2many `in [False, id]` domain does not reliably match 'no employee assigned'."""
        if employee.nl_site_ids:
            return employee.nl_site_ids
        sites = self.env['nelsis.work.site'].sudo().search(
            [('company_id', 'in', [False, employee.company_id.id])])
        return sites.filtered(lambda s: not s.employee_ids or employee in s.employee_ids)

    @api.model
    def _nl_match_site(self, employee, lat, lng, accuracy):
        sites = self._nl_sites_for(employee)
        if not sites:
            return None, 0.0, False
        best, best_d = None, None
        for s in sites:
            d = haversine_m(lat, lng, s.latitude, s.longitude)
            if best_d is None or d < best_d:
                best, best_d = s, d
        tolerance = min(accuracy or 0, 50)
        inside = best_d <= best.radius_m + tolerance
        return (best if inside else None), best_d, True

    @api.model
    def nl_punch(self, employee, kind, p):
        """Mobile punch. kind: 'in' | 'out'.  p: payload from the app. Returns the attendance record."""
        cfg = self.env['nelsis.config']
        if not valid_coords(p.get('lat'), p.get('lng')):
            raise UserError(_('A valid GPS location is required to punch.'))
        if p.get('mock') and cfg.bool_param('nelsis.block_mock'):
            raise UserError(_('Mock / fake GPS detected. Please disable it and try again.'))
        if cfg.bool_param('nelsis.require_photo_punch') and not p.get('photo'):
            raise UserError(_('A selfie is required to punch.'))
        lat, lng, acc = float(p['lat']), float(p['lng']), float(p.get('accuracy') or 0)
        uid = (p.get('uuid') or '')[:64]
        now = fields.Datetime.now()
        dev = parse_dt(p.get('device_time')) or now
        delta = (now - dev).total_seconds()
        tol = cfg.int_param('nelsis.time_tolerance_sec')
        offline = bool(p.get('offline'))
        if delta < -tol:
            trust, when = 'drift', now           # phone clock ahead: never trust it
        elif delta > 180 and not offline:
            # The phone says it was online, yet its clock is minutes/hours behind the server. Honouring that
            # time would let anyone back-date a punch by winding the clock back, so use the server time.
            trust, when = ('drift' if delta > tol else 'ok'), now
        elif delta > 180:
            if delta > MAX_OFFLINE_PUNCH_SEC:    # an 'offline' punch older than 3 days is not credible
                trust, when = 'drift', now
            else:
                trust, when = 'delayed', dev     # genuine offline punch: keep the real time
        else:
            trust, when = 'ok', dev if offline else now
        site, dist, has_sites = self._nl_match_site(employee, lat, lng, acc)
        mode = cfg.param('nelsis.geofence_mode')
        if (mode == 'block' and has_sites and not site and not employee.nl_field_staff):
            raise UserError(_('You are outside your allowed work location (%d m away).') % round(dist))
        photo = False
        if p.get('photo'):
            try:
                photo = base64.b64encode(base64.b64decode(p['photo'])[:4_000_000])
            except Exception:  # noqa: BLE001
                photo = False
        address = reverse_geocode(self.env, lat, lng) if not p.get('offline') else (p.get('address') or '')
        Att = self.sudo()
        if kind == 'in':
            if uid:
                dup = Att.search([('nl_in_uuid', '=', uid)], limit=1)
                if dup:
                    return dup
            if Att.search_count([('employee_id', '=', employee.id), ('check_out', '=', False)]):
                raise UserError(_('You are already punched in.'))
            last = Att.search([('employee_id', '=', employee.id), ('check_out', '!=', False)],
                              order='check_out desc', limit=1)
            if last and when < last.check_out:
                # offline punch that predates the previous check-out: keep ordering valid for hr.attendance
                when = last.check_out
            vals = {
                'employee_id': employee.id, 'check_in': when,
                'in_latitude': lat, 'in_longitude': lng, 'nl_in_accuracy': acc,
                'nl_in_mock': bool(p.get('mock')), 'nl_in_offline': bool(p.get('offline')) or trust == 'delayed',
                'nl_in_device_time': dev, 'nl_in_trust': trust, 'nl_in_site_id': site.id if site else False,
                'nl_in_distance_m': dist, 'nl_in_address': address, 'nl_in_photo': photo, 'nl_in_uuid': uid or False,
            }
            att = Att.create(vals)
        else:
            if uid:
                dup = Att.search([('nl_out_uuid', '=', uid)], limit=1)
                if dup:
                    return dup
            att = Att.search([('employee_id', '=', employee.id), ('check_out', '=', False)],
                             order='check_in desc', limit=1)
            if not att:
                raise UserError(_('You are not punched in.'))
            if when <= att.check_in:
                when = max(now, att.check_in)
            att.write({
                'check_out': when, 'out_latitude': lat, 'out_longitude': lng, 'nl_out_accuracy': acc,
                'nl_out_mock': bool(p.get('mock')), 'nl_out_offline': bool(p.get('offline')) or trust == 'delayed',
                'nl_out_device_time': dev, 'nl_out_trust': trust, 'nl_out_site_id': site.id if site else False,
                'nl_out_distance_m': dist, 'nl_out_address': address, 'nl_out_photo': photo,
                'nl_out_uuid': uid or False,
            })
        # keep a log point linked to this punch so the route shows it
        self.env['nelsis.location.log'].ingest(employee, [{
            'uuid': ('p-%s-%s' % (kind, uid)) if uid else None, 'lat': lat, 'lng': lng, 'accuracy': acc,
            'device_time': p.get('device_time') or fields.Datetime.to_string(now).replace(' ', 'T') + 'Z',
            'battery': p.get('battery'), 'mock': p.get('mock'),
            'source': 'punch_in' if kind == 'in' else 'punch_out', 'address': address,
        }], attendance=att)
        return att
