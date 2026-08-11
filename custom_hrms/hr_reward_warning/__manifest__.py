# -*- coding: utf-8 -*-

{
    'name': 'Open HRMS Official Announcements',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': """Manages Official Announcements""",
    'description': 'This module helps you to manage HR official announcements',
    'author': "Nelsis Tech Limited",
    'company': "Nelsis Tech Limited",
    'maintainer': "Nelsis Tech Limited",
    'website': 'https://nelsistech.com/',
    'depends': ['hr', 'mail'],
    'data': [
        'security/hr_announcement_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'views/hr_announcement_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_reward_warning_menus.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
