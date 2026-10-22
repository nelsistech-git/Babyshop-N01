# -*- coding: utf-8 -*-
# Part of Smart Complete Garment Software. Copyright (c) Nelsis Tech (www.nelsistech.com)
"""
Employee Attendance Management + Biometric Device Integration (SRS
sections 21-22) — garment.hr.attendance. Source-agnostic: a real
biometric/RFID integration (e.g. the Hikvision Face Terminal connector
already in this suite) would create records here via this same model,
rather than duplicating attendance data.
"""
from odoo import api, fields, models


class GarmentHrAttendance(models.Model):
    _name = 'garment.hr.attendance'
    _description = 'Garment Employee Attendance'
    _order = 'attendance_date desc'

    employee_id = fields.Many2one('garment.hr.employee', string='Employee', required=True, ondelete='cascade')
    attendance_date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    source = fields.Selection([
        ('biometric', 'Biometric Device'), ('face_recognition', 'Face Recognition'), ('rfid', 'RFID Card'),
        ('mobile', 'Mobile Attendance'), ('manual', 'Manual Entry'),
    ], string='Source', default='manual')
    shift_id = fields.Many2one('garment.hr.shift', string='Shift')
    check_in = fields.Datetime(string='Check In')
    check_out = fields.Datetime(string='Check Out')
    scheduled_start = fields.Float(string='Scheduled Start (hour)', default=8.0)
    scheduled_end = fields.Float(string='Scheduled End (hour)', default=17.0)
    grace_period_minutes = fields.Integer(string='Grace Period (minutes)', default=10,
                                           help='Attendance Rule Engine: a punch within this many minutes of '
                                                'Scheduled Start still counts as Present, not Late.')
    is_holiday = fields.Boolean(string='Holiday')
    is_weekly_off = fields.Boolean(string='Weekly Off')

    working_hours = fields.Float(string='Working Hours', compute='_compute_hours', store=True)
    late_minutes = fields.Integer(string='Late Minutes', compute='_compute_hours', store=True)
    early_leave_minutes = fields.Integer(string='Early Leave Minutes', compute='_compute_hours', store=True)
    overtime_hours = fields.Float(string='Overtime Hours', compute='_compute_hours', store=True)

    status = fields.Selection([
        ('present', 'Present'), ('absent', 'Absent'), ('late', 'Late'), ('half_day', 'Half Day'),
        ('leave', 'Leave'), ('holiday', 'Holiday'), ('weekly_off', 'Weekly Off'),
    ], string='Status', compute='_compute_hours', store=True)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id.shift_id:
            self.shift_id = self.employee_id.shift_id

    @api.onchange('shift_id')
    def _onchange_shift_id(self):
        if self.shift_id:
            self.scheduled_start = self.shift_id.start_time
            self.scheduled_end = self.shift_id.end_time
            self.grace_period_minutes = self.shift_id.grace_period_minutes

    @api.depends('check_in', 'check_out', 'scheduled_start', 'scheduled_end', 'grace_period_minutes',
                 'is_holiday', 'is_weekly_off')
    def _compute_hours(self):
        for rec in self:
            if rec.is_holiday:
                rec.working_hours = 0.0
                rec.late_minutes = 0
                rec.early_leave_minutes = 0
                rec.overtime_hours = 0.0
                rec.status = 'holiday'
                continue
            if rec.is_weekly_off:
                rec.working_hours = 0.0
                rec.late_minutes = 0
                rec.early_leave_minutes = 0
                rec.overtime_hours = 0.0
                rec.status = 'weekly_off'
                continue
            if not rec.check_in:
                rec.working_hours = 0.0
                rec.late_minutes = 0
                rec.early_leave_minutes = 0
                rec.overtime_hours = 0.0
                rec.status = 'absent'
                continue
            if rec.check_out:
                delta_hours = (rec.check_out - rec.check_in).total_seconds() / 3600.0
                rec.working_hours = round(delta_hours, 2)
            else:
                rec.working_hours = 0.0

            check_in_hour = rec.check_in.hour + rec.check_in.minute / 60.0
            late = max(0, round((check_in_hour - rec.scheduled_start) * 60))
            rec.late_minutes = late

            if rec.check_out:
                check_out_hour = rec.check_out.hour + rec.check_out.minute / 60.0
                early = max(0, round((rec.scheduled_end - check_out_hour) * 60))
                rec.early_leave_minutes = early
                rec.overtime_hours = max(0.0, round(check_out_hour - rec.scheduled_end, 2))
            else:
                rec.early_leave_minutes = 0
                rec.overtime_hours = 0.0

            # Attendance Rule Engine (SRS section 24): a punch within the shift's
            # Grace Period still counts as Present — only late beyond grace flips
            # the status to Late. late_minutes itself stays the raw minute count.
            standard_hours = rec.scheduled_end - rec.scheduled_start
            if rec.working_hours >= standard_hours * 0.9:
                rec.status = 'late' if late > (rec.grace_period_minutes or 0) else 'present'
            elif rec.working_hours >= standard_hours * 0.4:
                rec.status = 'half_day'
            else:
                rec.status = 'absent'
