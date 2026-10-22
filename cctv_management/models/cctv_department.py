# -*- coding: utf-8 -*-
from odoo import models, fields


class CctvDepartment(models.Model):
    _name = 'cctv.department'
    _description = 'CCTV Department / Zone'
    _order = 'floor_id, name'

    name = fields.Char(required=True)
    floor_id = fields.Many2one('cctv.floor', required=True, ondelete='cascade')
    office_id = fields.Many2one(related='floor_id.office_id', store=True)
    hr_department_id = fields.Many2one('hr.department', string='Linked HR Department')
    is_restricted_area = fields.Boolean(string='Restricted Area',
                                         help='Trespassing/unauthorized-entry alerts trigger for this zone')
    camera_ids = fields.One2many('cctv.camera', 'department_id', string='Cameras')
