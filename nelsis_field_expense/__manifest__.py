{
    'name': 'Nelsis Field Force - Expense, Advance & Map Verification',
    'version': '17.0.1.1.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Connects the mobile app to Conveyance (TA/DA), Employee Advance and Adjustment modules. '
               'Matches every claim against the employee GPS track (True/False), bill photo resize + '
               'duplicate-bill detection, payment history API.',
    'author': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['nelsis_field_tracking', 'conveyance_expense', 'employee_advance', 'employee_advance_adjustment'],
    'data': [
        'security/security.xml',
        'data/cron.xml',
        'views/conveyance_views.xml',
        'views/menus.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
