# -*- coding: utf-8 -*-
"""Upload queue + log for everything copied to Google Drive (snapshots, clips, daily logs, backups).

Events never wait for Google: cctv.event.create() only inserts a row here; a cron does the
uploading, retries with back-off, and stamps every row with the Drive file id/link, so this
table IS the upload log."""
import base64
import csv
import io
import json
import logging
from datetime import timedelta

import pytz
import requests

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 6
MAX_CLIP_BYTES = 150 * 1024 * 1024


class CctvDriveUpload(models.Model):
    _name = 'cctv.drive.upload'
    _description = 'CCTV Google Drive Upload Log'
    _order = 'id desc'

    name = fields.Char(required=True)
    kind = fields.Selection([
        ('snapshot', 'Event Snapshot'), ('clip', 'Event Clip'), ('training', 'AI Training Sample'),
        ('log', 'Daily Log'), ('backup', 'Backup')], required=True, index=True)
    state = fields.Selection([
        ('pending', 'Queued'), ('done', 'Uploaded'), ('failed', 'Failed'), ('skipped', 'Skipped')],
        default='pending', index=True)
    camera_id = fields.Many2one('cctv.camera', ondelete='set null', index=True)
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    event_id = fields.Many2one('cctv.event', ondelete='set null', index=True)
    event_key = fields.Char(help='detection|behaviour, used to avoid uploading the same thing every frame')
    label = fields.Char(help='Training samples: confirmed / false_positive')
    folder_path = fields.Char(help='Overrides the automatic Drive folder (parts joined by "/")')
    attempts = fields.Integer(default=0)
    next_try = fields.Datetime()
    drive_file_id = fields.Char(copy=False)
    web_link = fields.Char(copy=False)
    size = fields.Integer(string='Size (bytes)')
    uploaded_on = fields.Datetime(copy=False)
    expires_on = fields.Datetime(copy=False, help='The file is removed from Drive after this moment (camera retention)')
    deleted_on = fields.Datetime(copy=False)
    error = fields.Text()

    # ================================================================ helpers
    @api.model
    def _tz(self):
        name = self.env['ir.config_parameter'].sudo().get_param('cctv_management.report_timezone') or 'Asia/Dhaka'
        try:
            return pytz.timezone(name)
        except pytz.UnknownTimeZoneError:
            return pytz.UTC

    @api.model
    def _local(self, dt):
        return pytz.UTC.localize(dt).astimezone(self._tz())

    # ================================================================ enqueue
    @api.model
    def enqueue_for_event(self, event):
        drive = self.env['cctv.gdrive']
        cam = event.camera_id
        if not cam.drive_enabled or not drive.is_connected() or not event._drive_worthy():
            return
        param = self.env['ir.config_parameter'].sudo().get_param
        key = '%s|%s' % (event.detection_type, event.behavior_type)
        window = int(param('cctv_management.drive_dedupe_seconds', 30) or 30)
        since = fields.Datetime.now() - timedelta(seconds=window)
        if self.sudo().search_count([('camera_id', '=', cam.id), ('event_key', '=', key),
                                     ('kind', 'in', ('snapshot', 'clip')), ('create_date', '>=', since)]):
            return
        expires = fields.Datetime.now() + timedelta(days=int(cam.retention_days or 30))
        base = {'camera_id': cam.id, 'event_id': event.id, 'event_key': key, 'expires_on': expires}
        stamp = self._local(event.event_time).strftime('%H%M%S')
        if param('cctv_management.drive_upload_snapshots', 'True') == 'True' and event.snapshot:
            self.sudo().create(dict(base, kind='snapshot', name='%s_%s_%s.jpg' % (stamp, event.behavior_type, event.id)))
        if param('cctv_management.drive_upload_clips', 'True') == 'True' \
                and event._severity_rank() >= event._severity_rank_of(
                    param('cctv_management.drive_clip_min_severity', 'high')):
            ready = event.event_time + timedelta(seconds=(cam.playback_clip_seconds or 40) + 45)
            self.sudo().create(dict(base, kind='clip', next_try=ready,
                                    name='%s_%s_%s.mp4' % (stamp, event.behavior_type, event.id)))

    @api.model
    def enqueue_training(self, event, label):
        """Reviewed event -> labelled snapshot in CCTV/AI Training/<model kind>/<label>/."""
        if not event.snapshot:
            return False
        kind = event._ai_model_kind()
        root = self.env['cctv.gdrive'].root_name()
        return self.sudo().create({
            'kind': 'training', 'camera_id': event.camera_id.id, 'event_id': event.id, 'label': label,
            'name': '%s_%s_%s_%s.jpg' % (kind, label, event.detection_type, event.id),
            'folder_path': '/'.join([root, 'AI Training', kind, label]),
        })

    # ================================================================ processing
    @api.model
    def cron_process_queue(self, limit=30):
        if not self.env['cctv.gdrive'].is_connected():
            return
        now = fields.Datetime.now()
        rows = self.search([('state', 'in', ('pending', 'failed')), ('attempts', '<', MAX_ATTEMPTS),
                            '|', ('next_try', '=', False), ('next_try', '<=', now)], order='id', limit=limit)
        for row in rows:
            row._process()
            if not tools.config['test_enable']:
                self.env.cr.commit()

    def action_retry(self):
        self.write({'state': 'pending', 'attempts': 0, 'next_try': False, 'error': False})
        return True

    def _folder_parts(self, cam, sub):
        drive = self.env['cctv.gdrive']
        if self.folder_path:
            return self.folder_path.split('/')
        local = self._local(self.event_id.event_time or fields.Datetime.now())
        return drive.camera_folder_parts(cam) + [local.strftime('%Y-%m-%d'), sub]

    def _process(self):
        self.ensure_one()
        drive = self.env['cctv.gdrive']
        ev, cam = self.event_id, self.camera_id
        try:
            if self.kind in ('snapshot', 'training'):
                if not ev or not ev.snapshot:
                    return self._finish_skip(_('The event or its snapshot no longer exists.'))
                data, mime = base64.b64decode(ev.snapshot), 'image/jpeg'
                sub = 'Snapshots'
            elif self.kind == 'clip':
                if not ev or not cam:
                    return self._finish_skip(_('The event no longer exists.'))
                url = ev.playback_url
                if not url:
                    return self._finish_skip(_(
                        'No playback URL: set "Recording playback server URL" in CCTV > Configuration > Settings '
                        '(or the playback template on the camera) so Odoo can fetch the clip.'))
                data, mime = self._download_clip(url), 'video/mp4'
                sub = 'Clips'
            else:
                return self._finish_skip(_('Nothing to process for this kind.'))
            folder = drive.ensure_path(self._folder_parts(cam, sub))
            res = drive.upload_bytes(self.name, data, mime, folder)
            self.write({'state': 'done', 'drive_file_id': res.get('id'), 'web_link': res.get('webViewLink'),
                        'size': len(data), 'uploaded_on': fields.Datetime.now(), 'error': False,
                        'attempts': self.attempts + 1})
        except (UserError, requests.RequestException, ValueError) as exc:
            attempts = self.attempts + 1
            self.write({'state': 'failed', 'attempts': attempts, 'error': str(exc)[:1000],
                        'next_try': fields.Datetime.now() + timedelta(minutes=min(2 ** attempts, 120))})
        except Exception as exc:                     # a bad row must never stall the queue
            _logger.exception('drive upload %s crashed', self.id)
            self.write({'state': 'failed', 'attempts': MAX_ATTEMPTS, 'error': '%s: %s' % (type(exc).__name__, exc)})

    def _finish_skip(self, reason):
        self.write({'state': 'skipped', 'error': reason})

    @api.model
    def _download_clip(self, url):
        r = requests.get(url, stream=True, timeout=(10, 90))
        if r.status_code != 200:
            raise UserError(_('Playback server answered HTTP %s (is the recording finished and the server '
                              'reachable from Odoo?)') % r.status_code)
        ctype = (r.headers.get('Content-Type') or '').lower()
        if 'html' in ctype or 'json' in ctype or 'text' in ctype:
            raise UserError(_('Playback server returned %s instead of video: %s') % (ctype, r.text[:150]))
        buf = bytearray()
        for chunk in r.iter_content(1024 * 1024):
            buf.extend(chunk)
            if len(buf) > MAX_CLIP_BYTES:
                raise UserError(_('Clip is larger than %s MB, not uploaded.') % (MAX_CLIP_BYTES // 1048576))
        if not buf:
            raise UserError(_('Playback server returned an empty clip.'))
        return bytes(buf)

    # ================================================================ retention
    @api.model
    def cron_apply_retention(self, limit=100):
        if not self.env['cctv.gdrive'].is_connected():
            return
        drive = self.env['cctv.gdrive']
        rows = self.search([('state', '=', 'done'), ('deleted_on', '=', False), ('drive_file_id', '!=', False),
                            ('expires_on', '!=', False), ('expires_on', '<=', fields.Datetime.now())], limit=limit)
        for row in rows:
            try:
                drive.delete_file(row.drive_file_id)
                row.deleted_on = fields.Datetime.now()
            except UserError as exc:
                row.error = str(exc)[:500]
            if not tools.config['test_enable']:
                self.env.cr.commit()

    # ================================================================ daily log + backups
    @api.model
    def _store(self, kind, name, data, mime, parts, retention_days=0):
        """Upload right now and keep a log row (used for logs/backups, which are not event driven)."""
        drive = self.env['cctv.gdrive']
        vals = {'kind': kind, 'name': name, 'folder_path': '/'.join(parts),
                'expires_on': (fields.Datetime.now() + timedelta(days=retention_days)) if retention_days else False}
        row = self.sudo().create(vals)
        try:
            res = drive.upload_bytes(name, data, mime, drive.ensure_path(parts))
            row.write({'state': 'done', 'drive_file_id': res.get('id'), 'web_link': res.get('webViewLink'),
                       'size': len(data), 'uploaded_on': fields.Datetime.now(), 'attempts': 1})
        except UserError as exc:
            row.write({'state': 'failed', 'attempts': 1, 'error': str(exc)[:1000],
                       'next_try': fields.Datetime.now() + timedelta(hours=1)})
        return row

    @api.model
    def cron_daily_log_and_backup(self):
        """Yesterday's flagged events + upload log (CSV), camera config (JSON) and, if enabled, a weekly DB dump."""
        drive = self.env['cctv.gdrive']
        param = self.env['ir.config_parameter'].sudo().get_param
        if not drive.is_connected() or param('cctv_management.drive_daily_log', 'True') != 'True':
            return
        tz = self._tz()
        today_local = fields.Datetime.now().replace(tzinfo=pytz.UTC).astimezone(tz)
        day = (today_local - timedelta(days=1)).date()
        start = tz.localize(fields.Datetime.from_string('%s 00:00:00' % day)).astimezone(pytz.UTC).replace(tzinfo=None)
        end = start + timedelta(days=1)
        root = drive.root_name()
        retention = int(param('cctv_management.drive_log_retention_days', 365) or 365)

        events = self.env['cctv.event'].sudo().search([
            ('event_time', '>=', start), ('event_time', '<', end),
            '|', ('behavior_type', '!=', 'none'), ('detection_type', 'in', ['fire', 'smoke', 'tamper'])],
            order='event_time')
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(['time_local', 'site', 'camera', 'department', 'detection', 'behavior', 'confidence',
                    'track_id', 'alert', 'incident', 'review', 'snapshot_link', 'clip_link'])
        for ev in events:
            w.writerow([self._local(ev.event_time).strftime('%Y-%m-%d %H:%M:%S'), ev.office_id.name or '',
                        ev.camera_id.display_name, ev.department_id.name or '', ev.detection_type,
                        ev.behavior_type, round(ev.confidence or 0, 1), ev.track_ref or '',
                        ev.alert_id.display_name or '', ev.incident_id.display_name or '',
                        ev.review_state, ev.drive_snapshot_link or '', ev.drive_clip_link or ''])
        month = day.strftime('%Y-%m')
        self._store('log', 'events_%s.csv' % day, out.getvalue().encode('utf-8-sig'), 'text/csv',
                    [root, 'Logs', month], retention)

        ups = self.sudo().search([('create_date', '>=', start), ('create_date', '<', end),
                                  ('kind', 'in', ('snapshot', 'clip', 'training'))])
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(['created_utc', 'kind', 'camera', 'file', 'state', 'attempts', 'size_bytes', 'link', 'error'])
        for u in ups:
            w.writerow([u.create_date, u.kind, u.camera_id.display_name or '', u.name, u.state, u.attempts,
                        u.size, u.web_link or '', (u.error or '')[:200]])
        self._store('log', 'drive_uploads_%s.csv' % day, out.getvalue().encode('utf-8-sig'), 'text/csv',
                    [root, 'Logs', month], retention)

        cams = self.env['cctv.camera'].sudo().with_context(active_test=False).search([])
        cfg = [{'camera_code': c.camera_code, 'name': c.name, 'site': c.office_id.name,
                'floor': c.floor_id.name, 'department': c.department_id.name,
                'latitude': c.latitude, 'longitude': c.longitude, 'brand': c.brand, 'model': c.model,
                'connection_type': c.connection_type, 'resolution': c.resolution, 'fps': c.fps,
                'bitrate_kbps': c.bitrate_kbps, 'ai': c.ai_capability_labels, 'recording_mode': c.recording_mode,
                'retention_days': c.retention_days, 'active': c.active} for c in cams]      # no passwords
        self._store('backup', 'cameras_%s.json' % day, json.dumps(cfg, indent=2, ensure_ascii=False).encode(),
                    'application/json', [root, 'Backups', 'Camera Config'], retention)

        if param('cctv_management.drive_db_backup', 'False') == 'True' \
                and today_local.weekday() == int(param('cctv_management.drive_db_backup_weekday', 6) or 6):
            self.action_backup_database()

    @api.model
    def action_backup_database(self):
        """Full Odoo backup (database + filestore, zip) -> Drive. Needs pg_dump on the Odoo server."""
        from odoo.service import db as db_service
        drive = self.env['cctv.gdrive']
        if not drive.is_connected():
            raise UserError(_('Google Drive is not connected.'))
        keep = int(self.env['ir.config_parameter'].sudo().get_param('cctv_management.drive_backup_keep', 4) or 4)
        dbname = self.env.cr.dbname
        name = '%s_%s.zip' % (dbname, fields.Datetime.now().strftime('%Y%m%d_%H%M'))
        root = drive.root_name()
        row = self.sudo().create({'kind': 'backup', 'name': name,
                                  'folder_path': '/'.join([root, 'Backups', 'Database'])})
        try:
            stream = db_service.dump_db(dbname, None, 'zip')
            try:
                stream.seek(0, 2)
                size = stream.tell()

                def reader(offset, n):
                    stream.seek(offset)
                    return stream.read(n)

                folder = drive.ensure_path([root, 'Backups', 'Database'])
                res = drive.upload_stream(name, size, reader, 'application/zip', folder)
            finally:
                stream.close()
            row.write({'state': 'done', 'drive_file_id': res.get('id'), 'web_link': res.get('webViewLink'),
                       'size': size, 'uploaded_on': fields.Datetime.now(), 'attempts': 1})
        except Exception as exc:
            row.write({'state': 'failed', 'attempts': MAX_ATTEMPTS, 'error': '%s: %s' % (type(exc).__name__, exc)})
            return row
        old = self.sudo().search([('kind', '=', 'backup'), ('state', '=', 'done'), ('deleted_on', '=', False),
                                  ('name', 'like', dbname + '_%.zip')], order='id desc', offset=keep)
        for o in old:
            try:
                drive.delete_file(o.drive_file_id)
                o.deleted_on = fields.Datetime.now()
            except UserError:
                pass
        return row
