# -*- coding: utf-8 -*-
{
    'name': "Custom Employee Travelling",
    'version': "1.0.0",
    'category': "Human Resources",
    'sequence': 1,
    "images": ['static/description/icon.png'],
    'summary': "Custom Employee Travelling Scheduling & Expenses Tracker for Odoo v17",
    'description': """Custom Employee Travelling Scheduling & Expenses Tracker for Odoo v17""",
    'author': "Nelsis Tech Limited",
    'company': "Nelsis Tech Limited",
    'maintainer': "Nelsis Tech Limited",
    'website': 'https://nelsistech.com/',
    'depends': ['custom_hr_employee'],
    'data': [
        'views/hr_conveyance_seq.xml',
        'views/conveyance_settings_views.xml',
        'views/hr_employee_travelling_view.xml',
        'views/hr_conveyance_views.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'reports/hr_employee_travelling_report.xml'
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
