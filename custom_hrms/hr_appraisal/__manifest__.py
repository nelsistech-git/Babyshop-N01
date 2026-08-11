# -*- encoding: utf-8 -*-


{
    'name': 'Appraisals',
    'version': '17.0.0.0.1',
    'category': 'Human Resources/Appraisals',
    'sequence': 50,
    'summary': 'Evaluate your employees',
    'depends': ['hr', 'calendar'],
    'description': """
Employee Appraisal System
=========================

This application helps maintain employee motivation by conducting regular performance appraisals. Regular assessments benefit both employees and the organization.

Each employee can be assigned an appraisal plan, defining the frequency and method of their periodic evaluations.

Key Features
------------
* Create appraisals for employees.
* Appraisals can be initiated by a manager or automatically based on a predefined schedule.
* Appraisals follow a plan with various surveys, answered by different levels in the employee hierarchy. The final review is conducted by the manager.
* Notifications are sent to managers, colleagues, collaborators, and employees to perform appraisals.
* Completed appraisal forms can be viewed in PDF format.
* Meeting requests can be created manually based on appraisals.
""",
    "data": [
        'security/hr_appraisal_security.xml',
        'security/ir.model.access.csv',
        'wizard/request_appraisal_views.xml',
        'data/hr_appraisal_templates.xml',
        'views/hr_appraisal_views.xml',
        'views/hr_appraisal_goal_views.xml',
        'views/hr_appraisal_note_views.xml',
        'report/hr_appraisal_report_views.xml',
        'views/hr_department_views.xml',
        'views/res_config_settings_view.xml',
        'views/res_users_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_employee_public_views.xml',
        'data/hr_appraisal_data.xml',
        'data/mail_template_data.xml',
        'wizard/hr_departure_wizard_views.xml',
    ],
    "demo": [
        "data/hr_appraisal_demo.xml",
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'post_init_hook': '_generate_assessment_note_ids',
    'assets': {
        'web.assets_backend': [
            'hr_appraisal/static/src/**/*',
        ],
        'web.assets_tests': [
            'hr_appraisal/static/tests/tours/*.js',
        ]
    }
}
