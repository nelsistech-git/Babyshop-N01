# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)

from odoo import api, fields, models


class GarmentProductionOee(models.Model):
    """Overall Equipment Effectiveness = Availability x Performance x
    Quality. See Planning & MES SRS s.45, Shop Floor SRS s.41."""
    _name = 'garment.production.oee'
    _description = 'Garment Production OEE'
    _order = 'date desc'

    line_id = fields.Many2one('garment.production.line', string='Production Line')
    machine_id = fields.Many2one('garment.production.machine', string='Machine')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    shift = fields.Selection([
        ('morning', 'Morning'), ('evening', 'Evening'), ('night', 'Night'), ('general', 'General'),
    ], string='Shift', default='general')

    availability_pct = fields.Float(string='Availability (%)')
    performance_pct = fields.Float(string='Performance (%)')
    quality_pct = fields.Float(string='Quality (%)')
    oee_pct = fields.Float(string='OEE (%)', compute='_compute_oee', store=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('availability_pct', 'performance_pct', 'quality_pct')
    def _compute_oee(self):
        for rec in self:
            rec.oee_pct = (rec.availability_pct / 100.0) * (rec.performance_pct / 100.0) * \
                          (rec.quality_pct / 100.0) * 100.0
