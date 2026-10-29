# -*- coding: utf-8 -*-
from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    in_mode = fields.Selection(selection_add=[('cctv_face', 'CCTV Face')])
    out_mode = fields.Selection(selection_add=[('cctv_face', 'CCTV Face')])

    cctv_in_camera_id = fields.Many2one('cctv.camera', string='Check-in Camera', readonly=True)
    cctv_out_camera_id = fields.Many2one('cctv.camera', string='Check-out Camera', readonly=True)
    cctv_in_confidence = fields.Float(string='Check-in Match (%)', readonly=True)
    cctv_out_confidence = fields.Float(string='Check-out Match (%)', readonly=True)
    cctv_in_snapshot = fields.Binary(string='Check-in Snapshot', attachment=True, readonly=True)
    cctv_out_snapshot = fields.Binary(string='Check-out Snapshot', attachment=True, readonly=True)
    cctv_in_punch_id = fields.Many2one('cctv.attendance.punch', string='Check-in Punch', readonly=True,
                                       ondelete='set null')
    cctv_out_punch_id = fields.Many2one('cctv.attendance.punch', string='Check-out Punch', readonly=True,
                                        ondelete='set null')
    cctv_late_minutes = fields.Float(
        string='Minutes After Shift Start', readonly=True,
        help='Minutes between the scheduled shift start (CCTV Monitoring Assignment) and this first '
             'check-in of the day. 0 when on time or when the employee has no assignment.')
    cctv_is_late = fields.Boolean(
        string='Late', readonly=True,
        help='Checked in later than shift start + grace minutes of the Monitoring Assignment.')
    cctv_auto_closed = fields.Boolean(
        string='Closed Automatically', readonly=True,
        help='The employee never checked out; the attendance was closed at the last time they were seen. '
             'Please verify it before payroll.')
