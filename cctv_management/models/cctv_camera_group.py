# -*- coding: utf-8 -*-
from odoo import models, fields


class CctvCameraGroup(models.Model):
    _name = 'cctv.camera.group'
    _description = 'Live Monitor Grid Layout'
    _order = 'name'

    name = fields.Char(required=True)
    layout = fields.Selection([
        ('1', '1 Camera'), ('4', '4 Cameras'), ('9', '9 Cameras'),
        ('16', '16 Cameras'), ('25', '25 Cameras'), ('36', '36 Cameras'),
        ('64', '64 Cameras'), ('100', '100+ Cameras'),
    ], default='4', required=True)
    camera_ids = fields.Many2many('cctv.camera', string='Cameras')
    user_ids = fields.Many2many('res.users', string='Favourited By')
    is_default = fields.Boolean(string='Default Grid for New Users')
