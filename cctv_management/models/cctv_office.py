# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CctvOffice(models.Model):
    _name = 'cctv.office'
    _description = 'CCTV Site (Office / Factory / Warehouse / Branch)'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda s: s.env.company)
    site_type = fields.Selection([
        ('office', 'Office'),
        ('factory', 'Factory'),
        ('warehouse', 'Warehouse'),
        ('branch', 'Branch'),
        ('other', 'Other'),
    ], default='office', required=True)
    address = fields.Text()
    latitude = fields.Float(digits=(10, 7), help='Default map position for new cameras of this site.')
    longitude = fields.Float(digits=(10, 7))
    manager_id = fields.Many2one('hr.employee', string='Branch/Factory Manager')
    floor_ids = fields.One2many('cctv.floor', 'office_id', string='Floors')
    camera_ids = fields.One2many('cctv.camera', 'office_id', string='Cameras')
    camera_count = fields.Integer(compute='_compute_camera_count')
    camera_online_count = fields.Integer(compute='_compute_camera_count')
    map_image = fields.Binary(string='Site Map', attachment=True)
    active = fields.Boolean(default=True)

    def _compute_camera_count(self):
        for rec in self:
            rec.camera_count = len(rec.camera_ids)
            rec.camera_online_count = len(rec.camera_ids.filtered(lambda c: c.health_status == 'online'))

    # ✅ Add this method — it's what the button in your XML calls
    def action_view_events(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cameras',
            'res_model': 'cctv.camera',
            'view_mode': 'tree,form',
            'domain': [('office_id', '=', self.id)],
            'context': {'default_office_id': self.id},
        }
