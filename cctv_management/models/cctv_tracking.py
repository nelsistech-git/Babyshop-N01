# -*- coding: utf-8 -*-
"""Tracking menu upgrade (v4.4): face-driven visits, watchlist alerts, unknown-face review,
overstay detection and vehicle check-out."""
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
PARAM = 'cctv_management.'


def _param(env, key, default):
    """Integer system parameter (Settings > Technical > System Parameters)."""
    val = env['ir.config_parameter'].sudo().get_param(PARAM + key, str(default))
    try:
        return int(val)
    except (TypeError, ValueError):
        return int(default)


class CctvPersonTracking(models.Model):
    _inherit = 'cctv.person'

    last_seen = fields.Datetime(readonly=True)
    last_camera_id = fields.Many2one('cctv.camera', string='Last Seen On', readonly=True)
    on_site = fields.Boolean(compute='_compute_on_site', store=True, string='On Site Now')
    max_stay_minutes = fields.Integer(
        string='Max Stay (min)', help='Raise an overstay alert when a visit stays open longer than this. 0 = no limit.')
    face_log_count = fields.Integer(compute='_compute_face_log_count', string='Face Sightings')

    @api.depends('visit_ids.exit_time')
    def _compute_on_site(self):
        for rec in self:
            rec.on_site = any(not v.exit_time for v in rec.visit_ids)

    def _compute_face_log_count(self):
        counts = {}
        if self.ids:
            for person, n in self.env['cctv.face.log'].sudo()._read_group(
                    [('person_id', 'in', self.ids)], ['person_id'], ['__count']):
                counts[person.id] = n
        for rec in self:
            rec.face_log_count = counts.get(rec.id, 0)

    def action_open_face_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Face Sightings - %s', self.name),
            'res_model': 'cctv.face.log', 'view_mode': 'tree,form',
            'domain': [('person_id', '=', self.id)],
        }

    def _note_sighting(self, camera, when=None):
        """Remember where/when the person was last seen (throttled: face matches arrive per frame)."""
        now = when or fields.Datetime.now()
        for rec in self:
            if not rec.last_seen or (now - rec.last_seen) > timedelta(seconds=30) \
                    or rec.last_camera_id != camera:
                rec.sudo().write({'last_seen': now, 'last_camera_id': camera.id})

    def _raise_watchlist_alert(self, camera):
        """Blacklisted person -> critical alert (at most every 10 min); VIP -> low-severity heads-up (every 4 h)."""
        Alert = self.env['cctv.alert'].sudo()
        now = fields.Datetime.now()
        for rec in self:
            if rec.person_type == 'blacklisted':
                name, severity, alert_type, window = (
                    _('Blacklisted person detected: %(p)s at %(c)s', p=rec.name, c=camera.name),
                    'critical', 'intrusion', timedelta(minutes=10))
            elif rec.person_type == 'vip':
                name, severity, alert_type, window = (
                    _('VIP arrived: %(p)s at %(c)s', p=rec.name, c=camera.name),
                    'low', 'other', timedelta(hours=4))
            else:
                continue
            # dedupe per person (not per camera) so walking past several cameras does not spam
            prefix = name.split(' at ')[0]
            if Alert.search_count([('name', '=like', prefix + '%'), ('create_date', '>=', now - window)]):
                continue
            Alert.create({'name': name, 'alert_type': alert_type, 'severity': severity,
                          'camera_id': camera.id, 'office_id': camera.office_id.id})


class CctvVisitTracking(models.Model):
    _inherit = 'cctv.visit'

    source = fields.Selection([('manual', 'Manual'), ('face', 'Face Recognition'), ('vehicle', 'Vehicle (ANPR)')],
                              default='manual', index=True)
    state = fields.Selection([('on_site', 'On Site'), ('left', 'Left')], compute='_compute_state',
                             store=True, index=True)
    last_seen = fields.Datetime(default=fields.Datetime.now)
    auto_closed = fields.Boolean(help='Closed automatically because the person was not seen for a while.')
    is_overstay = fields.Boolean(string='Overstayed', readonly=True)
    overstay_alerted = fields.Boolean(readonly=True)
    person_type = fields.Selection(related='person_id.person_type', store=True, string='Person Type')
    route_summary = fields.Char(compute='_compute_route', string='Route')
    route_count = fields.Integer(compute='_compute_route', string='Stops')
    vehicle_log_ids = fields.One2many('cctv.vehicle.log', 'visit_id', string='Vehicles')

    @api.depends('exit_time')
    def _compute_state(self):
        for rec in self:
            rec.state = 'left' if rec.exit_time else 'on_site'

    @api.depends('route_event_ids.camera_id', 'route_event_ids.event_time')
    def _compute_route(self):
        for rec in self:
            labels = []
            for ev in rec.route_event_ids.sorted('event_time'):
                label = ev.department_id.name or ev.camera_id.name
                if label and (not labels or labels[-1] != label):
                    labels.append(label)
            rec.route_summary = ' → '.join(labels) if labels else False
            rec.route_count = len(labels)

    def action_check_out(self):
        now = fields.Datetime.now()
        for rec in self.filtered(lambda r: not r.exit_time):
            rec.write({'exit_time': now})

    @api.model
    def register_face_sighting(self, camera, person, when=None):
        """Open (or refresh) the visit of a face-recognised person at the camera's site.
        Employees are skipped unless cctv_management.track_employee_visits = 1 (they have attendance).
        A visit auto-closed less than visit_reopen_minutes ago is reopened instead of starting a new one."""
        if not camera.office_id:
            return self.browse()
        if person.person_type == 'employee' and not _param(self.env, 'track_employee_visits', 0):
            return self.browse()
        now = when or fields.Datetime.now()
        domain = [('person_id', '=', person.id), ('office_id', '=', camera.office_id.id)]
        visit = self.search(domain + [('exit_time', '=', False)], limit=1, order='entry_time desc')
        if visit:
            if not visit.last_seen or (now - visit.last_seen) > timedelta(seconds=30):
                visit.last_seen = now
            return visit
        recent = self.search(domain + [
            ('auto_closed', '=', True),
            ('exit_time', '>=', now - timedelta(minutes=_param(self.env, 'visit_reopen_minutes', 10)))],
            limit=1, order='exit_time desc')
        if recent:
            recent.write({'exit_time': False, 'auto_closed': False, 'last_seen': now})
            return recent
        return self.create({
            'person_id': person.id, 'office_id': camera.office_id.id,
            'department_visited_id': camera.department_id.id or False,
            'entry_camera_id': camera.id, 'entry_time': now, 'last_seen': now, 'source': 'face',
        })

    @api.model
    def cron_auto_close_visits(self):
        """Close face-created visits nobody has seen for visit_timeout_minutes (default 120).
        Exit time = last sighting. Vehicle/manual visits are closed by their own exit gate / by hand."""
        cutoff = fields.Datetime.now() - timedelta(minutes=_param(self.env, 'visit_timeout_minutes', 120))
        for visit in self.search([('exit_time', '=', False), ('source', '=', 'face'),
                                  ('last_seen', '<', cutoff)]):
            visit.write({'exit_time': visit.last_seen, 'auto_closed': True})

    @api.model
    def cron_check_overstay(self):
        """One alert per visit that stays open longer than the person's max_stay_minutes."""
        now = fields.Datetime.now()
        visits = self.search([('exit_time', '=', False), ('overstay_alerted', '=', False),
                              ('person_id.max_stay_minutes', '>', 0)])
        for visit in visits:
            limit = visit.person_id.max_stay_minutes
            stayed = (now - visit.entry_time).total_seconds() / 60.0
            if stayed <= limit:
                continue
            visit.write({'is_overstay': True, 'overstay_alerted': True})
            self.env['cctv.alert'].sudo().create({
                'name': _('Overstay: %(p)s at %(o)s - %(m)s min (limit %(l)s)',
                          p=visit.person_id.name, o=visit.office_id.name, m=int(stayed), l=limit),
                'alert_type': 'other', 'severity': 'medium',
                'camera_id': visit.entry_camera_id.id or False, 'office_id': visit.office_id.id,
            })


class CctvFaceLogTracking(models.Model):
    _inherit = 'cctv.face.log'

    reviewed = fields.Boolean(index=True, help='An operator has looked at this (unknown) face.')
    reviewed_by = fields.Many2one('res.users', readonly=True)
    reviewed_on = fields.Datetime(readonly=True)
    note = fields.Char()

    def action_mark_reviewed(self):
        self.write({'reviewed': True, 'reviewed_by': self.env.uid, 'reviewed_on': fields.Datetime.now()})

    def action_enroll_person(self):
        """Turn an unknown face into a Face Database entry (visitor) using the stored snapshot."""
        self.ensure_one()
        if self.person_id:
            raise UserError(_('This face is already matched to %s.', self.person_id.name))
        when = fields.Datetime.context_timestamp(self, self.detected_at or fields.Datetime.now())
        person = self.env['cctv.person'].create({
            'name': _('Unknown visitor %s', when.strftime('%Y-%m-%d %H:%M')),
            'person_type': 'visitor',
            'photo': self.snapshot,
            # privacy-safe default: erase the biometric data automatically after 30 days
            'biometric_retention_until': fields.Date.today() + timedelta(days=30),
        })
        person.message_post(body=_(
            'Created from an unknown face seen on %(c)s. Rename it, and add the photo to the AI service face '
            'gallery so future sightings are recognised.', c=self.camera_id.name))
        self.write({'person_id': person.id, 'is_unknown': False})
        self.action_mark_reviewed()
        return {'type': 'ir.actions.act_window', 'res_model': 'cctv.person', 'res_id': person.id,
                'view_mode': 'form', 'target': 'current'}


class CctvVehicleLogTracking(models.Model):
    _inherit = 'cctv.vehicle.log'

    state = fields.Selection([('parked', 'Parked'), ('left', 'Left')], compute='_compute_state',
                             store=True, index=True)

    @api.depends('exit_time')
    def _compute_state(self):
        for rec in self:
            rec.state = 'left' if rec.exit_time else 'parked'

    def action_check_out(self):
        now = fields.Datetime.now()
        for rec in self.filtered(lambda r: not r.exit_time):
            rec.write({'exit_time': now, 'last_seen': now})
            if rec.visit_id and not rec.visit_id.exit_time:
                rec.visit_id.write({'exit_time': now})
