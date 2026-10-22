# -*- coding: utf-8 -*-
"""v4.5 camera sync: map coordinates, site/floor/zone consistency, device auto-sync,
AI capability labels and Google Drive storage path."""
import logging
from datetime import timedelta

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError

from ..utils import camera_probe

_logger = logging.getLogger(__name__)

# fields whose change means "talk to the camera again"
_CONNECTION_FIELDS = {'ip_address', 'port', 'rtsp_url', 'onvif_port', 'username', 'password',
                      'brand', 'connection_type'}
_AI_FLAGS = [
    ('ai_human_detection', 'Human'), ('ai_vehicle_detection', 'Vehicle'), ('ai_face_recognition', 'Face'),
    ('ai_anpr', 'ANPR'), ('ai_ppe_detection', 'PPE'), ('ai_fire_smoke_detection', 'Fire/Smoke'),
    ('ai_people_counting', 'People Count'), ('ai_heatmap_analytics', 'Heatmap'),
    ('ai_queue_monitoring', 'Queue'), ('ai_theft_detection', 'Theft'),
    ('ai_tamper_detection', 'Tamper'), ('ai_mask_helmet_detection', 'Mask/Helmet'),
]


class CctvCameraSync(models.Model):
    _inherit = 'cctv.camera'

    # ------------------------------------------------------------ map
    latitude = fields.Float(string='Latitude', digits=(10, 7),
                            help='Decimal degrees, e.g. 23.8041. Filled from the site when empty.')
    longitude = fields.Float(string='Longitude', digits=(10, 7),
                             help='Decimal degrees, e.g. 90.4152. Filled from the site when empty.')
    map_url = fields.Char(compute='_compute_map_url')

    # ------------------------------------------------------------ device auto-sync
    auto_sync_device = fields.Boolean(
        string='Auto-sync from camera', default=True,
        help='Read bitrate, FPS, resolution and model from the camera/NVR automatically '
             '(when connection details change and then every few hours).')
    sync_pending = fields.Boolean(copy=False)
    sync_state = fields.Selection([('never', 'Not synced yet'), ('ok', 'Synced'), ('failed', 'Failed')],
                                  default='never', copy=False)
    last_sync = fields.Datetime(string='Last Device Sync', copy=False)
    sync_message = fields.Char(string='Sync Result', copy=False)

    # ------------------------------------------------------------ AI / counting tuning
    counting_line_y_pct = fields.Float(
        string='Counting Line Position (%)', default=60.0,
        help='Height of the entry/exit counting line, % from the top of the picture. Used by the AI service.')
    counting_in_direction = fields.Selection([('down', 'Moving down = IN'), ('up', 'Moving up = IN')],
                                             default='down', string='IN Direction')

    # ------------------------------------------------------------ AI service state (written by the service)
    ai_worker_status = fields.Char(string='AI Worker', copy=False)
    ai_worker_seen = fields.Datetime(string='AI Worker Last Report', copy=False)
    ai_capability_labels = fields.Char(compute='_compute_ai_capability_labels', string='AI Capabilities')
    ai_active = fields.Boolean(compute='_compute_ai_capability_labels', string='AI Enabled')
    ai_state = fields.Selection([('off', 'AI off'), ('running', 'AI running'), ('stale', 'AI not reporting')],
                                compute='_compute_ai_state', string='AI State')

    # ------------------------------------------------------------ storage (Google Drive)
    storage_location = fields.Char(compute='_compute_storage_location', store=True, readonly=False,
                                   help='Filled automatically (gdrive://...) once Google Drive is connected '
                                        'under CCTV > Configuration > Settings. Type your own path to override.')
    drive_enabled = fields.Boolean(string='Save events to Google Drive', default=True,
                                   help='Event snapshots and clips of this camera are copied to Google Drive '
                                        'when Drive is connected.')
    drive_upload_ids = fields.One2many('cctv.drive.upload', 'camera_id', string='Drive Uploads')
    drive_upload_count = fields.Integer(compute='_compute_drive_upload_count')

    # ================================================================ computes
    @api.depends('latitude', 'longitude')
    def _compute_map_url(self):
        for rec in self:
            rec.map_url = ('https://www.google.com/maps?q=%s,%s' % (rec.latitude, rec.longitude)
                           if rec.latitude or rec.longitude else False)

    @api.depends(*[f for f, _l in _AI_FLAGS])
    def _compute_ai_capability_labels(self):
        for rec in self:
            labels = [label for f, label in _AI_FLAGS if rec[f]]
            rec.ai_capability_labels = ' · '.join(labels) if labels else False
            rec.ai_active = bool(labels)

    @api.depends('ai_active', 'ai_worker_seen')
    def _compute_ai_state(self):
        stale = fields.Datetime.now() - timedelta(minutes=3)
        for rec in self:
            if not rec.ai_active:
                rec.ai_state = 'off'
            elif rec.ai_worker_seen and rec.ai_worker_seen >= stale:
                rec.ai_state = 'running'
            else:
                rec.ai_state = 'stale'

    @api.depends('office_id.name', 'name', 'camera_code')
    def _compute_storage_location(self):
        drive = self.env['cctv.gdrive']
        connected = drive.is_connected()
        for rec in self:
            current = rec.storage_location
            auto = (not current) or current.startswith('gdrive://')
            if connected and auto and rec.office_id:
                rec.storage_location = 'gdrive://' + '/'.join(drive.camera_folder_parts(rec))
            elif not current:
                rec.storage_location = False

    def _compute_drive_upload_count(self):
        groups = self.env['cctv.drive.upload'].sudo()._read_group(
            [('camera_id', 'in', self.ids)], ['camera_id'], ['__count'])
        counts = {cam.id: n for cam, n in groups}
        for rec in self:
            rec.drive_upload_count = counts.get(rec.id, 0)

    # ================================================================ site / floor / zone sync
    @api.onchange('department_id')
    def _onchange_department_sync(self):
        if self.department_id:
            self.floor_id = self.department_id.floor_id
            self.office_id = self.department_id.office_id

    @api.onchange('floor_id')
    def _onchange_floor_sync(self):
        if self.floor_id:
            self.office_id = self.floor_id.office_id
            if self.department_id and self.department_id.floor_id != self.floor_id:
                self.department_id = False

    @api.onchange('office_id')
    def _onchange_office_sync(self):
        if not self.office_id:
            return
        if self.floor_id and self.floor_id.office_id != self.office_id:
            self.floor_id = False
            self.department_id = False
        if not self.floor_id and len(self.office_id.floor_ids) == 1:
            self.floor_id = self.office_id.floor_ids
        if not self.latitude and not self.longitude:
            self.latitude = self.office_id.latitude
            self.longitude = self.office_id.longitude

    @api.constrains('office_id', 'floor_id', 'department_id')
    def _check_location_consistency(self):
        for rec in self:
            if rec.floor_id and rec.floor_id.office_id != rec.office_id:
                raise ValidationError(_('Floor "%s" does not belong to site "%s".')
                                      % (rec.floor_id.name, rec.office_id.name))
            if rec.department_id and rec.department_id.floor_id != rec.floor_id:
                raise ValidationError(_('Department / zone "%s" does not belong to floor "%s".')
                                      % (rec.department_id.name, rec.floor_id.name or '-'))

    @api.constrains('latitude', 'longitude')
    def _check_coordinates(self):
        for rec in self:
            if not -90 <= rec.latitude <= 90:
                raise ValidationError(_('Latitude must be between -90 and 90.'))
            if not -180 <= rec.longitude <= 180:
                raise ValidationError(_('Longitude must be between -180 and 180.'))

    @api.model
    def _complete_location_vals(self, vals):
        """Fill the missing levels of Office > Floor > Department from what was given, so
        imports/API/duplicate never create an inconsistent camera. Returns vals."""
        vals = dict(vals)
        Dept, Floor, Office = self.env['cctv.department'], self.env['cctv.floor'], self.env['cctv.office']
        if vals.get('department_id'):
            dept = Dept.browse(vals['department_id'])
            vals.setdefault('floor_id', dept.floor_id.id)
            vals.setdefault('office_id', dept.office_id.id)
        if vals.get('floor_id') and not vals.get('office_id'):
            vals['office_id'] = Floor.browse(vals['floor_id']).office_id.id
        office = Office.browse(vals['office_id']) if vals.get('office_id') else Office
        if office:
            if not (vals.get('latitude') or vals.get('longitude')):
                vals['latitude'], vals['longitude'] = office.latitude, office.longitude
            param = self.env['ir.config_parameter'].sudo().get_param
            if not vals.get('floor_id') and param('cctv_management.auto_default_zone', 'True') == 'True':
                floor = office.floor_ids[:1] if len(office.floor_ids) == 1 else Floor
                if not office.floor_ids:
                    floor = Floor.sudo().create({'name': 'Main Floor', 'office_id': office.id})
                if floor:
                    vals['floor_id'] = floor.id
            if vals.get('floor_id') and not vals.get('department_id') \
                    and param('cctv_management.auto_default_zone', 'True') == 'True':
                floor = Floor.browse(vals['floor_id'])
                if not floor.department_ids:
                    dept = Dept.sudo().create({'name': 'General Area', 'floor_id': floor.id})
                    vals['department_id'] = dept.id
                elif len(floor.department_ids) == 1:
                    vals['department_id'] = floor.department_ids.id
        return vals

    # ================================================================ create / write hooks
    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._complete_location_vals(v) for v in vals_list]
        for vals in vals_list:
            if self._has_connection(vals):
                vals['sync_pending'] = True
        records = super().create(vals_list)
        if any(r.sync_pending for r in records):
            self._trigger_sync_cron()
        return records

    def write(self, vals):
        # API / import writes: derive the upper levels when only a lower one is given
        if vals.get('department_id') and 'floor_id' not in vals:
            dept = self.env['cctv.department'].browse(vals['department_id'])
            vals = dict(vals, floor_id=dept.floor_id.id, office_id=dept.office_id.id)
        elif vals.get('floor_id') and 'office_id' not in vals:
            vals = dict(vals, office_id=self.env['cctv.floor'].browse(vals['floor_id']).office_id.id)
        if _CONNECTION_FIELDS & set(vals):
            vals = dict(vals, sync_pending=True)
        res = super().write(vals)
        if vals.get('sync_pending'):
            self._trigger_sync_cron()
        return res

    @api.model
    def _has_connection(self, vals):
        return bool(vals.get('rtsp_url') or vals.get('ip_address'))

    @api.model
    def _trigger_sync_cron(self):
        cron = self.env.ref('cctv_management.cron_cctv_camera_sync', raise_if_not_found=False)
        if cron:
            try:
                cron.sudo()._trigger()
            except Exception:                       # trigger is a nicety; the periodic run still happens
                _logger.debug('could not trigger camera sync cron', exc_info=True)

    # ================================================================ device sync
    def _effective_rtsp_url(self):
        """RTSP url as the AI service must open it (credentials included)."""
        self.ensure_one()
        cam = self.sudo()
        if cam.rtsp_url:
            return cam.rtsp_url
        if not cam.ip_address:
            return False
        auth = ''
        if cam.username:
            from urllib.parse import quote
            auth = '%s%s@' % (quote(cam.username, safe=''), (':' + quote(cam.password or '', safe='')) if cam.password else '')
        port = cam.port or 554
        if cam.brand == 'dahua':
            path = '/cam/realmonitor?channel=1&subtype=0'
        elif cam.brand == 'hikvision':
            path = '/Streaming/Channels/101'
        else:
            return False
        return 'rtsp://%s%s:%s%s' % (auth, cam.ip_address, port, path)

    def _sync_device_info(self):
        """Probe one camera and store what it reports. Never raises: result is stored on the record."""
        self.ensure_one()
        cam = self.sudo()
        vals = {'sync_pending': False, 'last_sync': fields.Datetime.now()}
        try:
            info = camera_probe.probe(cam.brand, cam._effective_rtsp_url() or cam.rtsp_url, cam.ip_address,
                                      cam.username, cam.password, cam.onvif_port)
        except camera_probe.ProbeError as exc:
            vals.update(sync_state='failed', sync_message=str(exc)[:240])
            cam.write(vals)
            return False
        done = []
        if info.get('bitrate_kbps'):
            vals['bitrate_kbps'] = info['bitrate_kbps']
            done.append('%s kbps' % info['bitrate_kbps'])
        if info.get('fps'):
            vals['fps'] = info['fps']
            done.append('%s fps' % info['fps'])
        bucket = camera_probe.resolution_bucket(info.get('width'), info.get('height'))
        if bucket:
            vals['resolution'] = bucket
            done.append('%sx%s' % (info.get('width'), info.get('height')))
        if info.get('model') and not cam.model:
            vals['model'] = info['model']
        if info.get('audio') is not None and info['audio'] != cam.audio_supported:
            vals['audio_supported'] = info['audio']
        vals.update(sync_state='ok', sync_message='%s: %s' % (info.get('source', 'camera'), ', '.join(done)),
                    health_status='online', last_seen=fields.Datetime.now())
        cam.write(vals)
        return True

    def action_sync_from_camera(self):
        ok = failed = 0
        for rec in self:
            if rec._sync_device_info():
                ok += 1
            else:
                failed += 1
        if len(self) == 1:
            rec = self[0]
            kind = 'success' if ok else 'warning'
            msg = rec.sync_message
        else:
            kind, msg = ('success' if not failed else 'warning'), _('%s synced, %s failed') % (ok, failed)
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Camera sync'), 'message': msg, 'type': kind, 'sticky': bool(failed)}}

    @api.model
    def cron_sync_devices(self, batch=25):
        """Pending cameras first (connection details just changed), then those not synced for N hours."""
        hours = int(self.env['ir.config_parameter'].sudo().get_param('cctv_management.sync_interval_hours', 6) or 6)
        stale = fields.Datetime.now() - timedelta(hours=max(hours, 1))
        domain = [('auto_sync_device', '=', True), '|', ('rtsp_url', '!=', False), ('ip_address', '!=', False)]
        cams = self.search(domain + [('sync_pending', '=', True)], limit=batch)
        if len(cams) < batch:
            cams |= self.search(domain + [('sync_pending', '=', False), '|',
                                          ('last_sync', '=', False), ('last_sync', '<', stale)],
                                order='last_sync asc nulls first', limit=batch - len(cams))
        for cam in cams:
            cam._sync_device_info()
            if not tools.config['test_enable']:
                self.env.cr.commit()

    # ================================================================ buttons
    def action_open_map(self):
        self.ensure_one()
        if not self.map_url:
            raise UserError(_('Enter a latitude and longitude first.'))
        return {'type': 'ir.actions.act_url', 'url': self.map_url, 'target': 'new'}

    def action_view_drive_uploads(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Drive Uploads'), 'res_model': 'cctv.drive.upload',
                'view_mode': 'tree,form', 'domain': [('camera_id', '=', self.id)]}

    def action_open_drive_folder(self):
        self.ensure_one()
        folder = self.env['cctv.gdrive'].camera_folder_id(self)
        return {'type': 'ir.actions.act_url', 'url': 'https://drive.google.com/drive/folders/%s' % folder,
                'target': 'new'}

    # ================================================================ AI service state intake
    @api.model
    def register_ai_status(self, statuses):
        """statuses: {camera_code: worker_status}. Called by /cctv/api/ai_status."""
        now = fields.Datetime.now()
        for code, status in (statuses or {}).items():
            cam = self.sudo().search([('camera_code', '=', code)], limit=1)
            if cam:
                cam.write({'ai_worker_status': str(status)[:64], 'ai_worker_seen': now})

    @api.model
    def refresh_storage_locations(self):
        """Called right after Google Drive is connected: fill the (still auto-managed) storage paths."""
        drive = self.env['cctv.gdrive']
        if not drive.is_connected():
            return
        for cam in self.sudo().with_context(active_test=False).search([]):
            cur = cam.storage_location
            if (not cur or cur.startswith('gdrive://')) and cam.office_id:
                cam.storage_location = 'gdrive://' + '/'.join(drive.camera_folder_parts(cam))
