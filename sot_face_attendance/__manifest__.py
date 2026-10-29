# -*- coding: utf-8 -*-
{
    'name': "sot_face_attendance",

    'summary': """
        Face recognition check in / check out for Odoo Attendances""",

    'description': """
        Adds face recognition (face-api.js) on top of Odoo Attendances:
        - a public kiosk page (/face/attendance) to check in / out by face
        - a backend "Face Attendance" screen for the logged-in employee
        - an HTTP endpoint used by the external Flask face-recognition app
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    'category': 'Human Resources/Attendances',
    'version': '17.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr_attendance', 'website'],

    # always loaded
    'data': [
        'views/face_attendance_views.xml',
        'views/face_recognization_template.xml',
    ],

    # Odoo 17: the old 'qweb' key and <template inherit_id="web.assets_backend">
    # no longer exist, assets are declared here.
    'assets': {
        'web.assets_backend': [
            'sot_face_attendance/static/src/js/face_attendance_action.js',
            'sot_face_attendance/static/src/xml/face_attendance.xml',
        ],
    },

    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
