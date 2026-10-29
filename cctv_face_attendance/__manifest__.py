# -*- coding: utf-8 -*-
{
    'name': 'CCTV Face Attendance',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Automatic HR attendance (check in / check out) from CCTV cameras you mark for face recognition',
    'description': """
CCTV Face Attendance for Odoo 17 Community
==========================================
Bridge between Smart CCTV Management (cctv_management) and HR Attendances (hr_attendance).

- Mark any camera as an *attendance camera* and give it a role: Entry (check in),
  Exit (check out) or Single door (toggle).
- The face-attendance service (Flask, see face_attendance_service) reads those cameras,
  recognises employees and posts confirmed punches here.
- Each accepted punch creates / closes a standard hr.attendance record, so overtime,
  Time Off, reports and any payroll that reads hr.attendance stay in sync automatically.
- Safety net: confidence bands (auto / HR review / reject), multi-frame confirmation,
  entry/exit roles, minimum gaps, forgotten check-out handling, full audit trail with
  snapshot, employee enrolment-quality report, consent and retention controls.
""",
    'author': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'depends': ['base', 'hr', 'hr_attendance', 'cctv_management'],
    'external_dependencies': {'python': ['pytz']},
    'data': [
        'security/ir.model.access.csv',
        'data/cctv_attendance_data.xml',
        'views/cctv_camera_views.xml',
        'views/cctv_person_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/cctv_attendance_punch_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
