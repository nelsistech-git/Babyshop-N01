# -*- coding: utf-8 -*-
from odoo import models, fields


class CctvFloor(models.Model):
    _name = 'cctv.floor'
    _description = 'CCTV Floor'
    _order = 'office_id, sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    office_id = fields.Many2one('cctv.office', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='office_id.company_id', store=True)
    department_ids = fields.One2many('cctv.department', 'floor_id', string='Departments')
    camera_ids = fields.One2many('cctv.camera', 'floor_id', string='Cameras')
