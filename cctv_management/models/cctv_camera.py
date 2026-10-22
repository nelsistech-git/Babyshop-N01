# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CctvCamera(models.Model):
    _name = 'cctv.camera'
    _description = 'CCTV Camera'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'office_id, name'
    _rec_name = 'name'

    name = fields.Char(required=True, tracking=True)
    camera_code = fields.Char(string='Camera ID', copy=False, required=True,
                               default=lambda s: s.env['ir.sequence'].next_by_code('cctv.camera') or 'New')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company)

    # Hierarchy
    office_id = fields.Many2one('cctv.office', required=True, tracking=True)
    floor_id = fields.Many2one('cctv.floor', domain="[('office_id', '=', office_id)]")
    department_id = fields.Many2one('cctv.department', domain="[('floor_id', '=', floor_id)]")

    # Connection
    brand = fields.Selection([
        ('hikvision', 'Hikvision'),
        ('dahua', 'Dahua'),
        ('uniview', 'Uniview'),
        ('axis', 'Axis'),
        ('cp_plus', 'CP Plus'),
        ('onvif_generic', 'Generic ONVIF'),
        ('other', 'Other / USB'),
    ], required=True, default='onvif_generic')
    model = fields.Char()
    connection_type = fields.Selection([
        ('onvif', 'ONVIF'),
        ('rtsp', 'RTSP Stream'),
        ('nvr', 'NVR Channel'),
        ('dvr', 'DVR Channel'),
        ('usb', 'USB Camera'),
        ('ip', 'Generic IP Camera'),
    ], required=True, default='rtsp')
    ip_address = fields.Char()
    port = fields.Integer(default=554)
    rtsp_url = fields.Char(string='RTSP URL', help='e.g. rtsp://user:pass@192.168.1.10:554/Streaming/Channels/101')
    onvif_port = fields.Integer(default=80)
    username = fields.Char()
    password = fields.Char(string='Password', groups='cctv_management.group_cctv_admin',
                            help='Stored per Odoo record access rules; restrict this field group to admins. '
                                 'For production, store credentials in a vault/secrets manager instead of the DB.')
    stream_bridge_url = fields.Char(
        string='Browser Stream URL (HLS/MJPEG)',
        help='Browsers cannot play raw RTSP. Point this to an HLS/MJPEG re-stream '
             '(e.g. served by MediaMTX/go2rtc/ffmpeg) for this camera, used by the Live Monitor grid.')

    resolution = fields.Selection([
        ('720p', '720p (HD)'), ('1080p', '1080p (Full HD)'),
        ('4mp', '4MP'), ('4k', '4K (UHD)'),
    ], default='1080p')
    fps = fields.Integer(default=25)
    bitrate_kbps = fields.Integer(string='Bitrate (kbps)')
    ptz_supported = fields.Boolean(string='PTZ Supported')
    night_mode_supported = fields.Boolean(string='Night Mode Supported')
    audio_supported = fields.Boolean(string='Audio Supported')

    # Health
    health_status = fields.Selection([
        ('online', 'Online'), ('offline', 'Offline'), ('unknown', 'Unknown'),
    ], default='unknown', tracking=True)
    last_seen = fields.Datetime(string='Last Heartbeat')
    last_offline_alert_sent = fields.Datetime()

    # Recording
    recording_mode = fields.Selection([
        ('continuous', 'Continuous'),
        ('motion', 'Motion Triggered'),
        ('ai_event', 'AI Event Triggered'),
        ('manual', 'Manual'),
        ('schedule', 'Scheduled'),
    ], default='continuous')
    recording_schedule_id = fields.Many2one('cctv.recording.schedule')
    retention_days = fields.Selection([
        ('7', '7 Days'), ('30', '30 Days'), ('90', '90 Days'), ('365', '365 Days'),
    ], default='30')
    storage_location = fields.Char(help='NAS path / MinIO or S3 bucket for this camera\'s recordings')

    # Map placement (section 18)
    map_x = fields.Float(string='Map X (%)')
    map_y = fields.Float(string='Map Y (%)')

    # AI capability flags - which detections this camera feeds into cctv.event
    ai_human_detection = fields.Boolean(default=True)
    ai_vehicle_detection = fields.Boolean()
    ai_face_recognition = fields.Boolean()
    ai_anpr = fields.Boolean(string='AI License Plate Recognition (ANPR)')
    ai_ppe_detection = fields.Boolean(string='AI PPE Detection (Helmet/Vest/Mask)')
    ai_fire_smoke_detection = fields.Boolean(string='AI Fire/Smoke Detection')

    # Retail / showroom AI capabilities (People Counting, Heatmap, Queue,
    # Theft/Suspicious Activity, Tamper Detection) - added for multi-showroom
    # retail deployments on top of the original security/factory feature set.
    ai_people_counting = fields.Boolean(string='AI People Counting (Entry/Exit)')
    ai_heatmap_analytics = fields.Boolean(string='AI Heatmap Analytics')
    ai_queue_monitoring = fields.Boolean(string='AI Queue Monitoring')
    ai_theft_detection = fields.Boolean(string='AI Theft / Suspicious Activity Detection')
    ai_tamper_detection = fields.Boolean(string='AI Tamper Detection (Blocked/Moved/Blurred)')
    ai_mask_helmet_detection = fields.Boolean(string='AI Mask/Helmet Compliance Detection')

    is_entry_exit_camera = fields.Boolean(
        string='Entry/Exit Counting Line Camera',
        help='Enable if this camera is positioned to count customers crossing the '
             'store entrance. The counting line itself is configured per-camera in '
             'the AI service config.yaml (counting_line: two pixel points).')
    is_queue_zone_camera = fields.Boolean(
        string='Billing Counter / Queue Zone Camera',
        help='Enable if this camera watches the billing counter so the AI service '
             'reports live queue length and average wait time for it.')
    is_pos_counter_camera = fields.Boolean(
        string='POS Counter Camera',
        help='Enable to link this camera to a Point of Sale register so each POS '
             'transaction is time-correlated with this camera\'s footage/snapshot '
             '(CCTV \u2194 POS Integration).')
    pos_config_id = fields.Many2one(
        'pos.config', string='Linked POS Register',
        help='Which POS register (till) this camera watches, for POS \u2194 CCTV sync.')

    footfall_today_in = fields.Integer(compute='_compute_footfall_today', string='Entries Today')
    footfall_today_out = fields.Integer(compute='_compute_footfall_today', string='Exits Today')
    footfall_ids = fields.One2many('cctv.footfall.count', 'camera_id', string='Footfall Counts')
    heatmap_ids = fields.One2many('cctv.heatmap.snapshot', 'camera_id', string='Heatmap Snapshots')
    queue_status_ids = fields.One2many('cctv.queue.status', 'camera_id', string='Queue Status Log')
    pos_link_ids = fields.One2many('cctv.pos.link', 'camera_id', string='POS Transaction Links')

    event_ids = fields.One2many('cctv.event', 'camera_id', string='AI Events')
    event_count = fields.Integer(compute='_compute_event_count')

    @api.depends('footfall_ids')
    def _compute_footfall_today(self):
        Footfall = self.env['cctv.footfall.count']
        today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for rec in self:
            counts = Footfall.search([
                ('camera_id', '=', rec.id), ('interval_start', '>=', today_start),
            ])
            rec.footfall_today_in = sum(counts.mapped('entry_count'))
            rec.footfall_today_out = sum(counts.mapped('exit_count'))

    _sql_constraints = [
        ('camera_code_uniq', 'unique(camera_code, company_id)', 'Camera ID must be unique per company.'),
    ]

    @api.depends('event_ids')
    def _compute_event_count(self):
        for rec in self:
            rec.event_count = len(rec.event_ids)

    @api.constrains('connection_type', 'rtsp_url', 'ip_address')
    def _check_connection_fields(self):
        for rec in self:
            if rec.connection_type in ('rtsp', 'onvif', 'ip', 'nvr', 'dvr') and not (rec.rtsp_url or rec.ip_address):
                raise ValidationError('Provide either an RTSP URL or an IP address for this connection type.')

    def action_mark_online(self):
        self.write({'health_status': 'online', 'last_seen': fields.Datetime.now()})

    def action_mark_offline(self):
        self.write({'health_status': 'offline'})

    def action_view_events(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'AI Events',
            'res_model': 'cctv.event',
            'view_mode': 'tree,form',
            'domain': [('camera_id', '=', self.id)],
        }

    @api.model
    def cron_check_offline_cameras(self):
        """Scheduled action: flag cameras with no heartbeat in 5 minutes as offline and alert."""
        stale_before = fields.Datetime.now() - __import__('datetime').timedelta(minutes=5)
        cameras = self.search([
            ('health_status', '=', 'online'),
            '|', ('last_seen', '<', stale_before), ('last_seen', '=', False),
        ])
        for cam in cameras:
            cam.health_status = 'offline'
            self.env['cctv.alert'].create({
                'name': 'Camera Offline: %s' % cam.name,
                'alert_type': 'camera_offline',
                'camera_id': cam.id,
                'office_id': cam.office_id.id,
                'severity': 'high',
            })
