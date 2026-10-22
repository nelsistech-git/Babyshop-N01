# -*- coding: utf-8 -*-
"""v4.5 AI service configuration: model registry, module Settings, and the config the
AI service pulls from Odoo (/cctv/api/config) so cameras never have to be listed twice."""
import hashlib
import json
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
DEFAULT_PLAYBACK = 'http://{host}:9996/get?path={{path}}&start={{start_iso}}&duration={{duration}}'


class CctvAiModel(models.Model):
    _name = 'cctv.ai.model'
    _description = 'CCTV AI Model'
    _order = 'kind, state, id desc'

    name = fields.Char(required=True)
    kind = fields.Selection([
        ('general', 'General (person / vehicle / bag)'), ('ppe', 'PPE (helmet / vest / mask)'),
        ('fire_smoke', 'Fire & Smoke'), ('warehouse', 'Warehouse (forklift / box / door)')],
        required=True, default='general')
    weights_file = fields.Char(required=True, help='File name/path on the AI service host, e.g. yolov8n.pt or '
                                                    '/srv/models/ppe_v3.pt (output of cctv_model_training/scripts/train.py)')
    classes = fields.Char(help='Class names the model detects, comma separated (documentation)')
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')], default='draft')
    trained_on = fields.Date()
    map50 = fields.Float(string='mAP@50', help='Validation score from scripts/evaluate.py (0-1)')
    note = fields.Text()
    sample_confirmed = fields.Integer(compute='_compute_samples', string='Confirmed samples')
    sample_false = fields.Integer(compute='_compute_samples', string='False-alarm samples')

    def _compute_samples(self):
        buckets = {}
        for ev in self.env['cctv.event'].search([('review_state', '!=', 'pending')], limit=20000):
            key = (ev._ai_model_kind(), ev.review_state)
            buckets[key] = buckets.get(key, 0) + 1
        for rec in self:
            rec.sample_confirmed = buckets.get((rec.kind, 'confirmed'), 0)
            rec.sample_false = buckets.get((rec.kind, 'false_positive'), 0)

    def action_activate(self):
        for rec in self:
            self.search([('kind', '=', rec.kind), ('state', '=', 'active'), ('id', '!=', rec.id)]).write({'state': 'archived'})
            rec.state = 'active'
        self.env['cctv.ai.config'].bump_version()
        return True

    def action_archive_model(self):
        self.write({'state': 'archived'})
        self.env['cctv.ai.config'].bump_version()
        return True

    def action_export_samples(self):
        """Queue every reviewed event of this model kind for the Drive 'AI Training' folder."""
        Upload = self.env['cctv.drive.upload']
        if not self.env['cctv.gdrive'].is_connected():
            raise UserError(_('Connect Google Drive first.'))
        n = 0
        for rec in self:
            evs = self.env['cctv.event'].search([('review_state', '!=', 'pending'), ('snapshot', '!=', False)],
                                                limit=5000)
            for ev in evs.filtered(lambda e: e._ai_model_kind() == rec.kind):
                if not Upload.search_count([('event_id', '=', ev.id), ('kind', '=', 'training')]):
                    Upload.enqueue_training(ev, ev.review_state)
                    n += 1
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('AI training samples'), 'type': 'success',
                           'message': _('%s sample(s) queued for Google Drive.') % n}}


class CctvAiConfig(models.AbstractModel):
    _name = 'cctv.ai.config'
    _description = 'Builds the configuration pulled by the AI service'

    @api.model
    def _p(self, key, default=None):
        val = self.env['ir.config_parameter'].sudo().get_param('cctv_management.' + key)
        return default if val in (None, False, '') else val

    @api.model
    def bump_version(self):
        self.env['ir.config_parameter'].sudo().set_param('cctv_management.ai_config_bump',
                                                         fields.Datetime.to_string(fields.Datetime.now()))

    @api.model
    def _full_frame_polygon(self, w, h, inset=0.08):
        x0, y0, x1, y1 = int(w * inset), int(h * inset), int(w * (1 - inset)), int(h * (1 - inset))
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    @api.model
    def _camera_config(self, cam, fw, fh):
        rtsp = cam._effective_rtsp_url()
        if not rtsp:
            return None
        sudo_cam = cam.sudo()
        cfg = {
            'camera_code': cam.camera_code, 'name': cam.name, 'rtsp_url': rtsp,
            'frame_width': fw, 'frame_height': fh,
            'detect_human': bool(cam.ai_human_detection),
            'detect_vehicle': bool(cam.ai_vehicle_detection or cam.ai_anpr),
            'detect_vehicle_plate': bool(cam.ai_anpr),
            'detect_face': bool(cam.ai_face_recognition),
            'detect_fire_smoke': bool(cam.ai_fire_smoke_detection),
            'detect_ppe': bool(cam.ai_ppe_detection or cam.ai_mask_helmet_detection),
            'restricted_area': bool(cam.department_id.is_restricted_area),
            'zone': {'site': cam.office_id.name, 'floor': cam.floor_id.name, 'department': cam.department_id.name},
        }
        poly = self._full_frame_polygon(fw, fh)
        if cam.ai_people_counting or cam.is_entry_exit_camera:
            y = int(fh * (cam.counting_line_y_pct or 60) / 100.0)
            cfg['counting_line'] = {'p1': [0, y], 'p2': [fw, y], 'in_direction': cam.counting_in_direction or 'down',
                                    'repeated_entry_threshold': 3, 'repeated_entry_window_seconds': 600}
            cfg['counting_push_interval_seconds'] = 300
        if cam.ai_heatmap_analytics:
            cfg['heatmap'] = {'enabled': True, 'push_interval_seconds': 3600,
                              'zones': [{'name': cam.department_id.name or cam.name, 'polygon': poly}]}
        if cam.ai_queue_monitoring or cam.is_queue_zone_camera:
            cfg['queue_zone'] = {'polygon': poly, 'threshold': int(self._p('queue_threshold', 5)),
                                 'push_interval_seconds': 20, 'avg_service_seconds': 90, 'counters_open': 1}
        if cam.ai_theft_detection:
            cfg['theft_detection'] = {'enabled': True, 'retail_zones': [{'polygon': poly}], 'loiter_seconds': 30,
                                      'concealment_height_drop_pct': 35, 'rapid_exit_seconds': 8,
                                      'store_open_hour': int(self._p('store_open_hour', 9)),
                                      'store_close_hour': int(self._p('store_close_hour', 21))}
        if cam.ai_tamper_detection:
            cfg['tamper_detection'] = {'enabled': True, 'check_every_seconds': 15, 'blocked_brightness_max': 25,
                                       'blocked_std_max': 8, 'blur_ratio_threshold': 0.35,
                                       'moved_diff_threshold': 40, 'cooldown_seconds': 300}
        if cam.ptz_supported and cam.ip_address:
            cfg['ptz'] = {'host': cam.ip_address, 'port': cam.onvif_port or 80,
                          'username': sudo_cam.username or '', 'password': sudo_cam.password or ''}
        return cfg

    @api.model
    def build(self):
        """Full configuration for the AI service. Only active cameras that have at least one AI capability."""
        fw, fh = int(self._p('ai_frame_width', 640)), int(self._p('ai_frame_height', 360))
        cams = self.env['cctv.camera'].sudo().search([('active', '=', True)])
        cam_cfgs, warnings = [], []
        for cam in cams.filtered('ai_active'):
            cfg = self._camera_config(cam, fw, fh)
            if cfg:
                cam_cfgs.append(cfg)
            else:
                warnings.append(_('%s: AI is ticked but no RTSP URL / IP+brand to build one.') % cam.display_name)

        models_ = self.env['cctv.ai.model'].sudo().search([('state', '=', 'active')])
        by_kind = {m.kind: m.weights_file for m in models_}
        # the detector takes one "extra" model (PPE / fire-smoke / warehouse); first match wins
        extra = by_kind.get('ppe') or by_kind.get('fire_smoke') or by_kind.get('warehouse')
        if any(c['detect_ppe'] for c in cam_cfgs) and not by_kind.get('ppe'):
            warnings.append(_('PPE detection is ticked on some cameras but no active PPE model is registered '
                              '(AI Models). It will do nothing until you train and activate one.'))
        if any(c['detect_fire_smoke'] for c in cam_cfgs) and not by_kind.get('fire_smoke'):
            warnings.append(_('Fire/smoke detection is ticked but no active fire & smoke model is registered.'))
        conf = {
            'detection': {
                'model_weights': by_kind.get('general') or 'yolov8n.pt',
                'confidence_threshold': float(self._p('ai_confidence', 0.45)),
                'frame_skip': int(self._p('ai_frame_skip', 2)),
                'ppe_model_weights': extra,
            },
            'tracking': {'enabled': True, 'max_age': int(self._p('ai_tracking_max_age', 30))},
            'face_recognition': {'enabled': any(c['detect_face'] for c in cam_cfgs),
                                 'gallery_dir': './face_gallery',
                                 'match_threshold': float(self._p('ai_face_threshold', 0.55))},
            'anpr': {'enabled': any(c['detect_vehicle_plate'] for c in cam_cfgs), 'languages': ['en'],
                     'min_confidence': float(self._p('ai_anpr_confidence', 0.4))},
            'cameras': cam_cfgs,
        }
        blob = json.dumps(conf, sort_keys=True) + (self._p('ai_config_bump') or '')
        return {'version': hashlib.sha256(blob.encode()).hexdigest()[:16], 'config': conf, 'warnings': warnings}

    @api.model
    def readiness_text(self):
        data = self.build()
        lines = [_('%s camera(s) will be sent to the AI service.') % len(data['config']['cameras'])]
        lines += ['• ' + w for w in data['warnings']]
        return '\n'.join(lines)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ---- AI service
    cctv_ai_service_url = fields.Char(string='AI Service URL', config_parameter='cctv_management.ai_service_url',
                                      help='e.g. http://127.0.0.1:8000 - used by "Test" and "Apply now"')
    cctv_ai_confidence = fields.Float(string='Detection confidence', config_parameter='cctv_management.ai_confidence', default=0.45)
    cctv_ai_frame_skip = fields.Integer(string='Process every Nth frame', config_parameter='cctv_management.ai_frame_skip', default=2)
    cctv_ai_tracking_max_age = fields.Integer(string='Keep lost tracks (frames)', config_parameter='cctv_management.ai_tracking_max_age', default=30)
    cctv_ai_frame_width = fields.Integer(string='AI frame width', config_parameter='cctv_management.ai_frame_width', default=640)
    cctv_ai_frame_height = fields.Integer(string='AI frame height', config_parameter='cctv_management.ai_frame_height', default=360)
    cctv_ai_face_threshold = fields.Float(string='Face match threshold', config_parameter='cctv_management.ai_face_threshold', default=0.55)
    cctv_ai_anpr_confidence = fields.Float(string='Plate read confidence', config_parameter='cctv_management.ai_anpr_confidence', default=0.4)
    cctv_queue_threshold = fields.Integer(string='Queue alert above (people)', config_parameter='cctv_management.queue_threshold', default=5)
    cctv_store_open_hour = fields.Integer(string='Store opens (hour)', config_parameter='cctv_management.store_open_hour', default=9)
    cctv_store_close_hour = fields.Integer(string='Store closes (hour)', config_parameter='cctv_management.store_close_hour', default=21)
    cctv_ai_readiness = fields.Text(string='AI readiness', compute='_compute_cctv_ai_readiness')

    # ---- camera sync
    cctv_sync_interval_hours = fields.Integer(string='Re-read camera settings every (hours)',
                                              config_parameter='cctv_management.sync_interval_hours', default=6)
    cctv_auto_default_zone = fields.Boolean(string='Auto-create Floor / Zone for new cameras',
                                            default=True)

    # ---- recording / playback
    cctv_playback_base_url = fields.Char(
        string='Recording playback server URL', config_parameter='cctv_management.playback_base_url',
        help='MediaMTX playback server reachable FROM ODOO, e.g. http://192.168.1.50:9996. '
             'Cameras without their own template use it for event clips.')

    # ---- Google Drive
    cctv_gdrive_client_id = fields.Char(string='OAuth Client ID', config_parameter='cctv_management.gdrive_client_id')
    cctv_gdrive_client_secret = fields.Char(string='OAuth Client Secret', config_parameter='cctv_management.gdrive_client_secret')
    cctv_gdrive_root_name = fields.Char(string='Drive root folder', config_parameter='cctv_management.gdrive_root_name', default='CCTV')
    cctv_drive_upload_snapshots = fields.Boolean(string='Upload event snapshots', default=True)
    cctv_drive_upload_clips = fields.Boolean(string='Upload event video clips', default=True)
    cctv_drive_clip_min_severity = fields.Selection(
        [('low', 'All flagged events'), ('medium', 'Medium and above'), ('high', 'High and above'),
         ('critical', 'Critical only')], string='Upload clips for',
        config_parameter='cctv_management.drive_clip_min_severity', default='high')
    cctv_drive_dedupe_seconds = fields.Integer(string='Ignore repeats within (s)', config_parameter='cctv_management.drive_dedupe_seconds', default=30)
    cctv_drive_training_export = fields.Boolean(string='Send reviewed events to AI Training folder', default=True)
    cctv_drive_daily_log = fields.Boolean(string='Daily event log + camera config backup', default=True)
    cctv_drive_log_retention_days = fields.Integer(string='Keep logs (days)', config_parameter='cctv_management.drive_log_retention_days', default=365)
    cctv_drive_db_backup = fields.Boolean(string='Weekly Odoo database backup', config_parameter='cctv_management.drive_db_backup')
    cctv_drive_backup_keep = fields.Integer(string='Keep last N DB backups', config_parameter='cctv_management.drive_backup_keep', default=4)
    cctv_gdrive_status = fields.Char(string='Status', compute='_compute_cctv_gdrive_status')
    cctv_gdrive_redirect_uri = fields.Char(string='Redirect URI', compute='_compute_cctv_gdrive_status')
    cctv_gdrive_queue = fields.Char(string='Upload queue', compute='_compute_cctv_gdrive_status')

    def _compute_cctv_ai_readiness(self):
        text = self.env['cctv.ai.config'].readiness_text()
        for rec in self:
            rec.cctv_ai_readiness = text

    def _compute_cctv_gdrive_status(self):
        drive = self.env['cctv.gdrive']
        Upload = self.env['cctv.drive.upload'].sudo()
        for rec in self:
            if drive.is_connected():
                rec.cctv_gdrive_status = _('Connected as %s') % (drive._param('gdrive_email') or _('(Google account)'))
            else:
                rec.cctv_gdrive_status = _('Not connected')
            rec.cctv_gdrive_redirect_uri = drive.redirect_uri()
            rec.cctv_gdrive_queue = _('%s queued · %s failed · %s uploaded') % (
                Upload.search_count([('state', '=', 'pending')]), Upload.search_count([('state', '=', 'failed')]),
                Upload.search_count([('state', '=', 'done')]))

    # Booleans that are ON by default: Odoo deletes a config parameter set to False, which would make the
    # default come back. Store an explicit 'True' / 'False' string instead.
    _CCTV_DEFAULT_ON = {
        'cctv_auto_default_zone': 'auto_default_zone',
        'cctv_drive_upload_snapshots': 'drive_upload_snapshots',
        'cctv_drive_upload_clips': 'drive_upload_clips',
        'cctv_drive_training_export': 'drive_training_export',
        'cctv_drive_daily_log': 'drive_daily_log',
    }

    @api.model
    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param
        for fname, key in self._CCTV_DEFAULT_ON.items():
            res[fname] = param('cctv_management.' + key, 'True') == 'True'
        return res

    def set_values(self):
        super().set_values()
        icp = self.env['ir.config_parameter'].sudo()
        for fname, key in self._CCTV_DEFAULT_ON.items():
            icp.set_param('cctv_management.' + key, 'True' if self[fname] else 'False')
        self.env['cctv.ai.config'].bump_version()

    # ---- buttons
    def action_cctv_gdrive_connect(self):
        return {'type': 'ir.actions.act_url', 'url': '/cctv/gdrive/connect', 'target': 'self'}

    def action_cctv_gdrive_disconnect(self):
        self.env['cctv.gdrive'].disconnect()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_cctv_gdrive_test(self):
        folder = self.env['cctv.gdrive'].test_connection()
        return self._notify(_('Google Drive'), _('Connected. Root folder ready (id %s).') % folder, 'success')

    def action_cctv_gdrive_run_queue(self):
        self.env['cctv.drive.upload'].cron_process_queue(limit=100)
        return self._notify(_('Google Drive'), _('Upload queue processed.'), 'success')

    def action_cctv_gdrive_backup_now(self):
        row = self.env['cctv.drive.upload'].action_backup_database()
        ok = row.state == 'done'
        return self._notify(_('Backup'), _('Database backup uploaded.') if ok else (row.error or _('Failed')),
                            'success' if ok else 'danger', sticky=not ok)

    def action_cctv_ai_test(self):
        url = (self.cctv_ai_service_url or '').rstrip('/')
        if not url:
            raise UserError(_('Enter the AI Service URL first.'))
        try:
            data = requests.get(url + '/health', timeout=5).json()
        except (requests.RequestException, ValueError) as exc:
            raise UserError(_('AI service not reachable: %s') % exc)
        running = sum(1 for s in (data.get('cameras') or {}).values() if s == 'running')
        return self._notify(_('AI service'), _('Online - %s of %s camera workers running.')
                            % (running, len(data.get('cameras') or {})), 'success')

    def action_cctv_ai_apply(self):
        """Ask the AI service to re-pull its config right now (it also polls by itself every minute)."""
        url = (self.cctv_ai_service_url or '').rstrip('/')
        if not url:
            raise UserError(_('Enter the AI Service URL first.'))
        self.env['cctv.ai.config'].bump_version()
        try:
            requests.post(url + '/reload', timeout=10)
        except requests.RequestException as exc:
            raise UserError(_('AI service not reachable: %s') % exc)
        return self._notify(_('AI service'), _('Reload requested.'), 'success')

    def _notify(self, title, message, kind, sticky=False):
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': title, 'message': message, 'type': kind, 'sticky': sticky}}
