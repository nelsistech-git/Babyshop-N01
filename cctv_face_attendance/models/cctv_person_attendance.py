# -*- coding: utf-8 -*-
import base64

from odoo import _, api, fields, models


def is_real_photo(b64_value):
    """True for JPEG / PNG / WEBP / GIF data. Odoo's auto-generated SVG avatar is NOT a photo."""
    if not b64_value:
        return False
    try:
        head = base64.b64decode(b64_value[:96] if isinstance(b64_value, (bytes, str)) else b'')[:12]
    except Exception:
        return False
    return head[:3] == b'\xff\xd8\xff' or head[:8] == b'\x89PNG\r\n\x1a\n' \
        or (head[:4] == b'RIFF' and head[8:12] == b'WEBP') or head[:4] == b'GIF8'


class CctvPersonFaceImage(models.Model):
    _name = 'cctv.person.face.image'
    _description = 'Extra reference photo for face recognition'
    _order = 'sequence, id'

    person_id = fields.Many2one('cctv.person', required=True, ondelete='cascade', index=True)
    name = fields.Char(help='e.g. "with glasses", "side angle"')
    image = fields.Binary(required=True, attachment=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)


class CctvPersonAttendance(models.Model):
    _inherit = 'cctv.person'

    attendance_enabled = fields.Boolean(
        string='Face Attendance', default=True,
        help='Untick to exclude this employee from automatic face attendance.')
    face_image_ids = fields.One2many('cctv.person.face.image', 'person_id', string='Extra Photos')
    attendance_enroll_state = fields.Selection([
        ('unknown', 'Not checked yet'), ('ok', 'Ready'),
        ('no_face', 'No face found in photo'), ('low_quality', 'Photo too small / blurry'),
        ('multiple', 'Several faces in photo'), ('no_photo', 'No photo'),
    ], default='unknown', string='Enrolment Status', readonly=True, copy=False)
    attendance_enroll_note = fields.Char(readonly=True, copy=False)
    attendance_enroll_checked = fields.Datetime(readonly=True, copy=False)
    attendance_photo_count = fields.Integer(compute='_compute_attendance_photo_count', string='Photos')
    attendance_punch_count = fields.Integer(compute='_compute_attendance_punch_count')

    @api.depends('photo', 'face_image_ids', 'employee_id.image_1920')
    def _compute_attendance_photo_count(self):
        for rec in self:
            rec.attendance_photo_count = len(rec._attendance_gallery_images())

    def _compute_attendance_punch_count(self):
        counts = {}
        if self.ids:
            for person, n in self.env['cctv.attendance.punch'].sudo()._read_group(
                    [('person_id', 'in', self.ids)], ['person_id'], ['__count']):
                counts[person.id] = n
        for rec in self:
            rec.attendance_punch_count = counts.get(rec.id, 0)

    # ------------------------------------------------------------------ eligibility & gallery
    def _attendance_ineligible_reason(self):
        """'' when this person may be punched by face, else why not."""
        self.ensure_one()
        cfg = self.env['cctv.attendance.config']
        emp = self.employee_id
        if not self.active:
            return _('person is archived')
        if self.person_type != 'employee' or not emp:
            return _('person is not linked to an employee')
        if not emp.active:
            return _('employee is archived')
        if not self.attendance_enabled:
            return _('face attendance is switched off for this person')
        if self.biometric_purged:
            return _('biometric data was erased')
        if cfg.param('require_consent') and not self.biometric_consent:
            return _('no biometric consent recorded')
        return ''

    def _binary_version(self, record, field):
        """Stable change marker for a binary field (attachment checksum, else write date)."""
        att = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', record._name), ('res_id', '=', record.id), ('res_field', '=', field)], limit=1)
        return att.checksum or str(record.write_date)

    def _attendance_gallery_images(self):
        """[{'key','kind','id'}] reference photos of this person, used by the face service."""
        self.ensure_one()
        out = []
        if is_real_photo(self.photo):
            out.append({'kind': 'person', 'id': self.id,
                        'key': 'person:%s:%s' % (self.id, self._binary_version(self, 'photo'))})
        for img in self.face_image_ids.filtered(lambda i: i.active and is_real_photo(i.image)):
            out.append({'kind': 'face', 'id': img.id,
                        'key': 'face:%s:%s' % (img.id, self._binary_version(img, 'image'))})
        emp = self.employee_id
        if emp and is_real_photo(emp.image_1920) and not self.env['cctv.attendance.config'].param('skip_employee_photo'):
            out.append({'kind': 'employee', 'id': emp.id,
                        'key': 'employee:%s:%s' % (emp.id, self._binary_version(emp, 'image_1920'))})
        return out

    def action_open_attendance_punches(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Punches - %s', self.name),
            'res_model': 'cctv.attendance.punch', 'view_mode': 'tree,form',
            'domain': [('person_id', '=', self.id)],
        }

    def write(self, vals):
        res = super().write(vals)
        if {'photo', 'attendance_enabled', 'employee_id', 'active', 'face_image_ids',
                'biometric_consent', 'biometric_purged', 'person_type'} & set(vals):
            self.env['cctv.attendance.config'].bump_version()
        return res
