# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentFabricRelaxation(models.Model):
    """Fabric Relaxation tracking before spreading/cutting. See Production
    Management SRS s.23."""
    _name = 'garment.fabric.relaxation'
    _description = 'Garment Fabric Relaxation'
    _order = 'start_datetime desc'

    cutting_order_id = fields.Many2one('garment.cutting.order', string='Cutting Order',
                                       required=True, ondelete='cascade')
    fabric_roll_id = fields.Many2one('garment.fabric.roll', string='Fabric Roll')
    fabric_material_id = fields.Many2one('garment.material', string='Fabric')
    start_datetime = fields.Datetime(string='Start Time', required=True)
    end_datetime = fields.Datetime(string='End Time')
    duration_hours = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)
    responsible_person_id = fields.Many2one('garment.hr.employee', string='Responsible Person')
    status = fields.Selection([
        ('in_progress', 'In Progress'), ('completed', 'Completed'),
    ], string='Status', default='in_progress')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                delta = rec.end_datetime - rec.start_datetime
                rec.duration_hours = delta.total_seconds() / 3600.0
            else:
                rec.duration_hours = 0.0
