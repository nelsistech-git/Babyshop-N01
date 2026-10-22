# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CctvEvent(models.Model):
    _name = 'cctv.event'
    _description = 'AI Detection Event'
    _order = 'event_time desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)
    camera_id = fields.Many2one('cctv.camera', required=True, ondelete='cascade')
    office_id = fields.Many2one(related='camera_id.office_id', store=True)
    department_id = fields.Many2one(related='camera_id.department_id', store=True)
    event_time = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    hour_of_day = fields.Integer(compute='_compute_hour_of_day', store=True, index=True,
                                  help='0-23, used by the Heat Map dashboard')

    detection_type = fields.Selection([
        ('human', 'Human'), ('vehicle', 'Vehicle'), ('face', 'Face'),
        ('animal', 'Animal'), ('fire', 'Fire'), ('smoke', 'Smoke'),
        ('tamper', 'Camera Tamper'),
    ], required=True)

    behavior_type = fields.Selection([
        ('none', 'None / Normal'),
        ('suspicious', 'Suspicious Activity'),
        ('running', 'Running'), ('fighting', 'Fighting'), ('falling', 'Falling'),
        ('sleeping', 'Sleeping'), ('sitting_long', 'Sitting Too Long'),
        ('crowd', 'Crowd Gathering'), ('loitering', 'Loitering'),
        ('trespassing', 'Trespassing'), ('climbing_fence', 'Climbing Fence'),
        ('wrong_direction', 'Wrong Direction'), ('restricted_entry', 'Restricted Area Entry'),
        ('object_throwing', 'Object Throwing'),
        # Employee activity / compliance
        ('idle', 'Employee Idle'), ('phone_usage', 'Phone Usage'), ('smoking', 'Smoking'),
        ('eating', 'Eating'), ('no_helmet', 'No Safety Helmet'), ('no_vest', 'No Safety Vest'),
        ('no_mask', 'No Mask'), ('no_uniform', 'No Uniform'),
        ('left_station', 'Left Workstation (Unannounced)'),
        ('unauthorized_break', 'Unauthorized / Extended Break'),
        ('late_arrival', 'Late Arrival'), ('early_departure', 'Early Departure'),
        ('argument', 'Argument / Verbal Conflict'),
        ('unprofessional_conduct', 'Unprofessional Conduct (Other)'),
        ('task_delay', 'Task Delay (No Detected Presence During Task Window)'),
        ('personal_visitor', 'Unofficial / Personal Visitor at Workstation'),
        ('group_gathering', 'Excessive Group Gathering / Non-Work Socializing'),
        # Warehouse / facility
        ('unauthorized_entry', 'Unauthorized Entry'), ('package_removal', 'Package Removal'),
        ('door_open', 'Door Left Open'), ('forklift_movement', 'Forklift Movement'),
        # Retail / showroom
        ('theft_suspected', 'Theft / Shoplifting Suspected'),
        ('item_concealment', 'Item Concealment Gesture'),
        ('after_hours_presence', 'After-Hours Presence in Retail Zone'),
        ('queue_overcrowded', 'Queue / Billing Counter Overcrowded'),
        ('camera_blocked', 'Camera Blocked / Covered'),
        ('camera_moved', 'Camera Moved / Angle Changed'),
        ('camera_blurred', 'Camera Blurred / Defocused'),
        # Added in v4.0 (AI service: object_watch / crowd / motion analyzers)
        ('unattended_object', 'Unattended Object'),
        ('abandoned_package', 'Abandoned Package / Bag'),
        ('crowd_limit', 'Crowd Over Limit'),
        ('repeated_entry', 'Repeated Entry'),
        ('no_helmet_compliance', 'Helmet Compliance Check'),
        ('no_mask_compliance', 'Mask Compliance Check'),
    ], default='none')

    person_id = fields.Many2one('cctv.person', string='Identified Person')
    visit_id = fields.Many2one('cctv.visit', string='Related Visit (route tracking)')
    vehicle_log_id = fields.Many2one('cctv.vehicle.log', string='Related Vehicle Event')

    confidence = fields.Float(string='AI Confidence (%)')
    bounding_box = fields.Char(help='Raw JSON bounding box from the CV service, e.g. {"x":..,"y":..,"w":..,"h":..}')
    track_ref = fields.Char(string='Track ID', help='Tracker (DeepSORT) id of the person/object, used by the Live Monitor '
                                                   'to show one box per tracked person instead of one per frame.')
    frame_width = fields.Integer(help='Pixel width of the AI frame the bounding box refers to (Live Monitor overlay scaling)')
    frame_height = fields.Integer(help='Pixel height of the AI frame the bounding box refers to (Live Monitor overlay scaling)')
    snapshot = fields.Binary(attachment=True)
    source_service = fields.Char(string='Detection Source', help='e.g. yolo-v8-cam03, deepsort-tracker-1')
    raw_payload = fields.Text(string='Raw Payload', help='Full JSON payload as received from the AI webhook')

    alert_id = fields.Many2one('cctv.alert', string='Generated Alert')
    incident_id = fields.Many2one('cctv.incident', string='Escalated Incident')

    @api.depends('event_time')
    def _compute_hour_of_day(self):
        for rec in self:
            rec.hour_of_day = rec.event_time.hour if rec.event_time else 0

    @api.depends('detection_type', 'behavior_type', 'camera_id', 'event_time')
    def _compute_display_name(self):
        for rec in self:
            behavior = dict(rec._fields['behavior_type'].selection).get(rec.behavior_type, '')
            det = dict(rec._fields['detection_type'].selection).get(rec.detection_type, '')
            rec.display_name = f"[{rec.camera_id.name or ''}] {det} - {behavior} ({rec.event_time or ''})"

    # High-severity behaviors that auto-create an alert (and, for the worst ones, an incident)
    _ALERT_BEHAVIORS = {
        'fighting', 'trespassing', 'climbing_fence', 'restricted_entry',
        'object_throwing', 'unauthorized_entry', 'door_open',
        'left_station', 'unauthorized_break', 'late_arrival', 'early_departure',
        'argument', 'task_delay',
        'theft_suspected', 'item_concealment', 'after_hours_presence',
        'queue_overcrowded', 'camera_blocked', 'camera_moved', 'camera_blurred',
        'unattended_object', 'abandoned_package', 'crowd_limit', 'repeated_entry',
        'falling', 'crowd',
    }
    _INCIDENT_BEHAVIORS = {'fighting', 'trespassing', 'restricted_entry', 'theft_suspected',
                           'abandoned_package'}
    _FIRE_SMOKE = {'fire', 'smoke'}
    _LOW_SEVERITY_BEHAVIORS = {'late_arrival', 'early_departure', 'unauthorized_break', 'task_delay',
                                'queue_overcrowded', 'repeated_entry'}
    _MEDIUM_SEVERITY_BEHAVIORS = {'left_station', 'argument', 'item_concealment',
                                   'camera_moved', 'camera_blurred', 'unattended_object',
                                   'crowd', 'crowd_limit'}

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        for event in events:
            if event.detection_type in self._FIRE_SMOKE or event.behavior_type in self._ALERT_BEHAVIORS:
                if event.detection_type in self._FIRE_SMOKE or event.behavior_type in self._INCIDENT_BEHAVIORS:
                    severity = 'critical'
                elif event.behavior_type in self._LOW_SEVERITY_BEHAVIORS:
                    severity = 'low'
                elif event.behavior_type in self._MEDIUM_SEVERITY_BEHAVIORS:
                    severity = 'medium'
                else:
                    severity = 'high'
                alert = self.env['cctv.alert'].create({
                    'name': event.display_name,
                    'alert_type': event.detection_type if event.detection_type in self._FIRE_SMOKE else 'ai_event',
                    'camera_id': event.camera_id.id,
                    'office_id': event.office_id.id,
                    'severity': severity,
                    'event_id': event.id,
                })
                event.alert_id = alert.id
                if event.behavior_type in self._INCIDENT_BEHAVIORS or event.detection_type in self._FIRE_SMOKE:
                    incident = self.env['cctv.incident'].create({
                        'name': event.display_name,
                        'incident_type': 'fire' if event.detection_type == 'fire' else (
                            'trespassing' if event.behavior_type == 'trespassing' else
                            'theft' if event.behavior_type == 'theft_suspected' else
                            'fighting' if event.behavior_type == 'fighting' else
                            'emergency' if event.behavior_type == 'abandoned_package' else 'accident'),
                        'office_id': event.office_id.id,
                        'camera_id': event.camera_id.id,
                        'event_id': event.id,
                    })
                    event.incident_id = incident.id
            self.env['cctv.violation'].create_from_event(event)
            self.env['cctv.stock.link']._register_movement_event(event)
        return events

    # ------------------------------------------------------ recording playback
    playback_url = fields.Char(compute='_compute_playback_url', string='Recording Clip URL')

    def _compute_playback_url(self):
        for rec in self:
            rec.playback_url = rec.camera_id._playback_url_for(rec.event_time) if rec.event_time else False

    def action_open_recording(self):
        self.ensure_one()
        if not self.playback_url:
            raise UserError(_('No playback URL template is configured on camera "%s". '
                              'Set it on the camera (Recording tab) - see README "Recording playback".')
                            % self.camera_id.display_name)
        return {'type': 'ir.actions.act_url', 'url': self.playback_url, 'target': 'new'}
