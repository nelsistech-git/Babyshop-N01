# -*- coding: utf-8 -*-
import json
import logging

from odoo import fields, http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def _json_response(data, status=200):
    return Response(
        json.dumps(data),
        content_type='application/json;charset=utf-8',
        status=status,
    )


class FaceRecognization(http.Controller):

    @http.route('/face/attendance', type='http', auth="public", csrf=False, cors="*", website=True)
    def faceRecognization(self, **kw):
        return request.render('sot_face_attendance.face_attendance')

    @http.route('/sot_face_attendance/employee_image/<int:employee_id>', type='http', auth='public', methods=['GET'])
    def employee_image(self, employee_id, **kw):
        """Employee photo (image_1920) used as the reference face.

        Replaces the /base_64_to_url/... route of the old setup, which came
        from a third party module and is not part of Odoo.
        """
        employee = request.env['hr.employee'].sudo().browse(employee_id).exists()
        if not employee or not employee.image_1920:
            return request.not_found()
        try:
            stream = request.env['ir.binary']._get_image_stream_from(employee, 'image_1920')
            return stream.get_response()
        except Exception:
            _logger.exception("Could not read the image of employee %s", employee_id)
            return request.not_found()


class FaceAttendanceController(http.Controller):

    @http.route('/attendance/face/get_employees/<string:employee_id>', auth='public', type='http', csrf=False, methods=['GET'])
    def attendance_face_get_employees(self, employee_id=False, **kwargs):
        """Toggle check in / check out of an employee (called after a face match)."""
        data = {}
        try:
            employee = request.env['hr.employee'].sudo().search([('id', '=', int(employee_id))], limit=1)
            if not employee:
                return _json_response({'error': 'employee not found'}, status=404)

            action_date_time = fields.Datetime.now()
            status = False
            if employee.attendance_state != 'checked_in':
                request.env['hr.attendance'].sudo().create({
                    'employee_id': employee.id,
                    'check_in': action_date_time,
                })
                status = True
            else:
                attendance = request.env['hr.attendance'].sudo().search(
                    [('employee_id', '=', employee.id), ('check_out', '=', False)],
                    order='check_in desc', limit=1)
                if attendance:
                    attendance.write({'check_out': action_date_time})
                    status = False

            data['status'] = status
            data['id'] = employee.id
            data['name'] = employee.name
            if employee.last_check_in:
                data['last_check_in'] = employee.last_check_in.strftime('%Y-%m-%d %H:%M:%S')
            return _json_response(data)
        except Exception:
            _logger.exception("Face attendance failed for employee %s", employee_id)
            return _json_response(data, status=500)
