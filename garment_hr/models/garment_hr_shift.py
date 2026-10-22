# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Shift Management System (HRM SRS section 25; Module 36 SRS sections 24-25)
— garment.hr.shift + garment.hr.shift.assignment (Worker Shift Assignment /
simplified roster). Not present at all in the original build even though
both SRS documents call it out as a first-class module ("Shift Management
System" with its own examples) — genuine gap closed here.
"""
from odoo import api, fields, models


class GarmentHrShift(models.Model):
    _name = 'garment.hr.shift'
    _description = 'Garment HR Shift'
    _order = 'start_time'

    name = fields.Char(string='Shift Name', required=True)
    shift_type = fields.Selection([
        ('general', 'General Shift'), ('morning', 'Morning Shift'), ('evening', 'Evening Shift'),
        ('night', 'Night Shift'), ('rotational', 'Rotational Shift'), ('overtime', 'Overtime Shift'),
    ], string='Shift Type', default='general', required=True)
    start_time = fields.Float(string='Start Time', required=True, default=8.0, help='24h float, e.g. 8.5 = 08:30')
    end_time = fields.Float(string='End Time', required=True, default=17.0)
    break_hours = fields.Float(string='Break Time (hours)', default=1.0)
    grace_period_minutes = fields.Integer(string='Grace Period (minutes)', default=10,
                                           help='Minutes after Start Time before a punch counts as Late.')
    working_hours = fields.Float(string='Net Working Hours', compute='_compute_working_hours', store=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.depends('start_time', 'end_time', 'break_hours')
    def _compute_working_hours(self):
        for rec in self:
            span = rec.end_time - rec.start_time
            if span < 0:
                span += 24.0  # night shift crossing midnight
            rec.working_hours = max(0.0, round(span - (rec.break_hours or 0.0), 2))


class GarmentHrShiftAssignment(models.Model):
    """Worker Shift Assignment (Module 36 SRS section 25) — also serves as a
    simplified roster (SRS section 26): one row per employee per effective
    period. A full weekly per-day roster grid is deferred — see
    IMPLEMENTATION_NOTES.md.
    """
    _name = 'garment.hr.shift.assignment'
    _description = 'Garment Worker Shift Assignment'
    _order = 'effective_date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    department_id = fields.Many2one('garment.hr.department', string='Department',
                                     related='employee_id.department_id', store=True, readonly=True)
    shift_id = fields.Many2one('garment.hr.shift', string='Shift', required=True)
    effective_date = fields.Date(string='Effective Date', required=True, default=fields.Date.context_today)
    end_date = fields.Date(string='End Date', help='Leave empty for an open-ended assignment.')
    reason = fields.Char(string='Reason')
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.employee_id and rec.effective_date and rec.effective_date <= fields.Date.context_today(rec):
                rec.employee_id.write({'shift_id': rec.shift_id.id})
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'shift_id' in vals or 'effective_date' in vals:
            today = fields.Date.context_today(self)
            for rec in self:
                if rec.effective_date and rec.effective_date <= today:
                    rec.employee_id.write({'shift_id': rec.shift_id.id})
        return res
