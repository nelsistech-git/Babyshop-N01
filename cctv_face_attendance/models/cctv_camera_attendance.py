# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CctvCameraAttendance(models.Model):
    _inherit = 'cctv.camera'

    ai_attendance = fields.Boolean(
        string='Face Attendance Camera', tracking=True,
        help='Tick to use this camera for automatic HR attendance. The face-attendance service '
             'reads the camera, recognises enrolled employees and posts check-ins / check-outs.')
    attendance_direction = fields.Selection([
        ('in', 'Entry - check in only'),
        ('out', 'Exit - check out only'),
        ('both', 'Single door - check in and out'),
    ], string='Attendance Role', default='in', tracking=True,
        help='Entry: only ever checks in (point it at the entrance). Exit: only ever checks out. '
             'Single door: toggles in/out, with a minimum gap so one walk through the door is one punch. '
             'Cameras that merely see people pass by should NOT be attendance cameras.')
    attendance_stream_url = fields.Char(
        string='Attendance Stream URL',
        help='Optional. Stream the face service should read for this camera (for example the main '
             'stream, which has more pixels per face than the sub stream). Empty = the camera RTSP URL.')
    attendance_usb_index = fields.Integer(
        string='USB Camera Index', default=0,
        help='For USB cameras plugged into the machine running the face service: 0 = first camera.')
    attendance_worker_status = fields.Char(copy=False, readonly=True)
    attendance_worker_seen = fields.Datetime(copy=False, readonly=True)
    attendance_state = fields.Selection(
        [('off', 'Not used'), ('running', 'Running'), ('stale', 'Service not reporting')],
        compute='_compute_attendance_state', string='Attendance Service')
    attendance_punch_count = fields.Integer(compute='_compute_attendance_punch_count')

    @api.depends('ai_attendance', 'attendance_worker_seen', 'attendance_worker_status')
    def _compute_attendance_state(self):
        stale = fields.Datetime.now() - timedelta(minutes=3)
        for rec in self:
            if not rec.ai_attendance:
                rec.attendance_state = 'off'
            elif rec.attendance_worker_seen and rec.attendance_worker_seen >= stale \
                    and rec.attendance_worker_status == 'running':
                rec.attendance_state = 'running'
            else:
                rec.attendance_state = 'stale'

    def _compute_attendance_punch_count(self):
        counts = {}
        if self.ids:
            for cam, n in self.env['cctv.attendance.punch'].sudo()._read_group(
                    [('camera_id', 'in', self.ids)], ['camera_id'], ['__count']):
                counts[cam.id] = n
        for rec in self:
            rec.attendance_punch_count = counts.get(rec.id, 0)

    # ------------------------------------------------------------------ source for the service
    def _attendance_source(self):
        """(source, kind) the face service must open, or (False, False)."""
        self.ensure_one()
        cam = self.sudo()
        if cam.attendance_stream_url:
            return cam.attendance_stream_url.strip(), 'url'
        url = cam._effective_rtsp_url()
        if url:
            return url, 'url'
        if cam.connection_type == 'usb':
            return cam.attendance_usb_index or 0, 'usb'
        if cam.stream_bridge_url:
            return cam.stream_bridge_url.strip(), 'url'
        return False, False

    @api.constrains('ai_attendance', 'attendance_stream_url', 'rtsp_url', 'ip_address',
                    'connection_type', 'brand', 'stream_bridge_url')
    def _check_attendance_source(self):
        for cam in self.filtered('ai_attendance'):
            if cam._attendance_source()[1] is False:
                raise ValidationError(_(
                    'Camera "%s" is marked for face attendance but the service has nothing to read: '
                    'fill in the RTSP URL (or an Attendance Stream URL).', cam.display_name))

    def attendance_camera_config(self):
        self.ensure_one()
        source, kind = self._attendance_source()
        return {
            'camera_code': self.camera_code, 'name': self.name,
            'source': source, 'source_kind': kind,
            'direction': self.attendance_direction or 'in',
            'site': self.office_id.name, 'floor': self.floor_id.name, 'department': self.department_id.name,
        }

    def action_view_attendance_punches(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Punches - %s', self.name),
            'res_model': 'cctv.attendance.punch', 'view_mode': 'tree,form',
            'domain': [('camera_id', '=', self.id)],
        }

    def action_mark_attendance_camera(self):
        self.write({'ai_attendance': True})
        self.env['cctv.attendance.config'].bump_version()

    def write(self, vals):
        res = super().write(vals)
        if {'ai_attendance', 'attendance_direction', 'attendance_stream_url', 'attendance_usb_index',
                'rtsp_url', 'ip_address', 'username', 'password', 'active'} & set(vals):
            self.env['cctv.attendance.config'].bump_version()
        return res
