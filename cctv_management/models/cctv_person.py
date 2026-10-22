# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CctvPerson(models.Model):
    _name = 'cctv.person'
    _description = 'CCTV Face Database Entry (Employee/Visitor/Vendor/Blacklist)'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    person_type = fields.Selection([
        ('employee', 'Employee'),
        ('visitor', 'Visitor'),
        ('vendor', 'Vendor'),
        ('blacklisted', 'Blacklisted Person'),
        ('vip', 'VIP'),
    ], required=True, default='visitor', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Linked Employee')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    phone = fields.Char()
    id_number = fields.Char(string='ID/Passport Number')
    photo = fields.Binary(attachment=True)
    face_embedding_ref = fields.Char(
        string='Face Embedding Reference ID',
        help='Opaque ID returned by the external face-recognition service; '
             'the actual embedding vector is stored/managed by that service, not in Odoo.')
    blacklist_reason = fields.Text()
    active = fields.Boolean(default=True)

    visit_ids = fields.One2many('cctv.visit', 'person_id', string='Visits')
    visit_count = fields.Integer(compute='_compute_visit_count')

    @api.depends('visit_ids')
    def _compute_visit_count(self):
        for rec in self:
            rec.visit_count = len(rec.visit_ids)


class CctvVisit(models.Model):
    _name = 'cctv.visit'
    _description = 'Visitor/Person Site Visit Log'
    _order = 'entry_time desc'

    person_id = fields.Many2one('cctv.person', required=True, ondelete='cascade')
    office_id = fields.Many2one('cctv.office', required=True)
    department_visited_id = fields.Many2one('cctv.department', string='Department Visited')
    entry_camera_id = fields.Many2one('cctv.camera', string='Entry Camera')
    exit_camera_id = fields.Many2one('cctv.camera', string='Exit Camera')
    entry_time = fields.Datetime(default=fields.Datetime.now)
    exit_time = fields.Datetime()
    duration_minutes = fields.Float(compute='_compute_duration', store=True)
    route_event_ids = fields.One2many('cctv.event', 'visit_id', string='Route Events (Camera-to-Camera)')

    @api.depends('entry_time', 'exit_time')
    def _compute_duration(self):
        for rec in self:
            if rec.entry_time and rec.exit_time:
                rec.duration_minutes = (rec.exit_time - rec.entry_time).total_seconds() / 60.0
            else:
                rec.duration_minutes = 0.0
