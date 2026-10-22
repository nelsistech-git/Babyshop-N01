# -*- coding: utf-8 -*-
from odoo import models, fields


class CctvIncident(models.Model):
    _name = 'cctv.incident'
    _description = 'Security Incident'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(required=True, tracking=True)
    incident_type = fields.Selection([
        ('theft', 'Theft'), ('fire', 'Fire'), ('fighting', 'Fighting'),
        ('accident', 'Accident'), ('trespassing', 'Trespassing'),
        ('emergency', 'Emergency'), ('machine_failure', 'Machine Failure'),
    ], required=True, tracking=True)
    state = fields.Selection([
        ('open', 'Open'), ('investigation', 'Investigation'),
        ('action', 'Action'), ('closed', 'Closed'),
    ], default='open', required=True, tracking=True)
    office_id = fields.Many2one('cctv.office', required=True)
    camera_id = fields.Many2one('cctv.camera')
    event_id = fields.Many2one('cctv.event')
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    description = fields.Text()
    resolution_notes = fields.Text()
    closed_date = fields.Datetime()

    def action_start_investigation(self):
        self.write({'state': 'investigation'})

    def action_take_action(self):
        self.write({'state': 'action'})

    def action_close(self):
        self.write({'state': 'closed', 'closed_date': fields.Datetime.now()})
