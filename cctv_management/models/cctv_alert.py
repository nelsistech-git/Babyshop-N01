# -*- coding: utf-8 -*-
from odoo import api, models, fields


class CctvAlert(models.Model):
    _name = 'cctv.alert'
    _description = 'Smart Alert'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(required=True)
    alert_type = fields.Selection([
        ('camera_offline', 'Camera Offline'),
        ('ai_event', 'AI Detection Event'),
        ('unknown_face', 'Unknown Face'),
        ('fire', 'Fire'),
        ('smoke', 'Smoke'),
        ('intrusion', 'Intrusion'),
        ('ppe_violation', 'PPE Violation'),
        ('warehouse_door', 'Warehouse Door Open'),
        ('other', 'Other'),
    ], required=True, default='other')
    severity = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ], default='medium', required=True)
    camera_id = fields.Many2one('cctv.camera')
    office_id = fields.Many2one('cctv.office')
    event_id = fields.Many2one('cctv.event')
    state = fields.Selection([
        ('new', 'New'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved'), ('ignored', 'Ignored'),
    ], default='new', tracking=True)
    acknowledged_by = fields.Many2one('res.users')
    acknowledged_at = fields.Datetime()
    notes = fields.Text()
    escalation_level = fields.Integer(default=0, help='Highest escalation level already notified.')
    last_escalated_at = fields.Datetime()
    delivery_ids = fields.One2many('cctv.alert.delivery', 'alert_id', string='Notifications Sent')
    delivery_count = fields.Integer(compute='_compute_delivery_count')

    @api.depends('delivery_ids')
    def _compute_delivery_count(self):
        for rec in self:
            rec.delivery_count = len(rec.delivery_ids)

    @api.model_create_multi
    def create(self, vals_list):
        alerts = super().create(vals_list)
        for alert in alerts:
            if alert.name and alert.name.startswith('TEST - alert channel check'):
                continue   # the "Send Test" button sends its own delivery
            alert._queue_notifications()
        return alerts

    def _queue_notifications(self, level=0):
        """Create pending deliveries for every matching channel at this level and
        ask the cron to send them right away (never blocks the caller)."""
        Channel = self.env['cctv.alert.channel'].sudo()
        queued = False
        for alert in self:
            channels = Channel.search([('escalation_level', '=', level)]).filtered(
                lambda c: c._matches(alert))
            if channels and channels._make_deliveries(alert, check_cooldown=True):
                queued = True
        if queued:
            cron = self.env.ref('cctv_management.cron_cctv_send_notifications', raise_if_not_found=False)
            if cron:
                cron.sudo()._trigger()

    def action_view_deliveries(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': 'Notifications', 'res_model': 'cctv.alert.delivery',
                'view_mode': 'tree,form', 'domain': [('alert_id', '=', self.id)]}

    def action_acknowledge(self):
        self.write({'state': 'acknowledged', 'acknowledged_by': self.env.user.id,
                     'acknowledged_at': fields.Datetime.now()})

    def action_resolve(self):
        self.write({'state': 'resolved'})

    def action_ignore(self):
        self.write({'state': 'ignored'})
