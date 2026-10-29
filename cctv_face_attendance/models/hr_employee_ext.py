# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    cctv_person_ids = fields.One2many('cctv.person', 'employee_id', string='Face Database Entries')
    cctv_person_id = fields.Many2one('cctv.person', compute='_compute_cctv_person_id', string='Face Entry')
    cctv_enroll_state = fields.Selection(
        [('unknown', 'Not checked yet'), ('ok', 'Ready'), ('no_face', 'No face found in photo'),
         ('low_quality', 'Photo too small / blurry'), ('multiple', 'Several faces in photo'),
         ('no_photo', 'No photo')], compute='_compute_cctv_enroll_state', string='Face Enrolment')
    cctv_punch_count = fields.Integer(compute='_compute_cctv_punch_count', string='Face Punches')

    @api.depends('cctv_person_ids', 'cctv_person_ids.person_type')
    def _compute_cctv_person_id(self):
        for emp in self:
            emp.cctv_person_id = emp.cctv_person_ids.filtered(
                lambda p: p.person_type == 'employee')[:1] if emp.cctv_person_ids else False

    @api.depends('cctv_person_ids.attendance_enroll_state', 'cctv_person_ids.person_type')
    def _compute_cctv_enroll_state(self):
        for emp in self:
            emp.cctv_enroll_state = emp.cctv_person_id.attendance_enroll_state or False

    def _compute_cctv_punch_count(self):
        counts = {}
        if self.ids:
            for emp, n in self.env['cctv.attendance.punch'].sudo()._read_group(
                    [('employee_id', 'in', self.ids)], ['employee_id'], ['__count']):
                counts[emp.id] = n
        for emp in self:
            emp.cctv_punch_count = counts.get(emp.id, 0)

    def action_enroll_face(self):
        """Create the Face Database entry (type Employee) for each selected employee."""
        Person = self.env['cctv.person'].sudo()
        created, no_photo = 0, 0
        for emp in self:
            if Person.with_context(active_test=False).search_count(
                    [('employee_id', '=', emp.id), ('person_type', '=', 'employee')]):
                continue
            Person.create({
                'name': emp.name, 'person_type': 'employee', 'employee_id': emp.id,
                'company_id': emp.company_id.id or self.env.company.id,
            })
            created += 1
            if not emp.image_1920:
                no_photo += 1
        msg = _('%s employee(s) enrolled.') % created
        if no_photo:
            msg += ' ' + _('%s have no photo yet: add one on the employee form.') % no_photo
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Face attendance'), 'message': msg,
                           'type': 'warning' if no_photo else 'success', 'sticky': bool(no_photo)}}

    def action_open_cctv_punches(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Face Punches - %s', self.name),
            'res_model': 'cctv.attendance.punch', 'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }
