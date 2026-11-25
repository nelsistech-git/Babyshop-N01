{
    'name': 'Employee Advance Adjustment',
    'version': '17.0.3.1.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Adjust a paid advance with expenses: Supervisor check, Accounts final check and posting',
    'depends': ['employee_advance'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'report/adjustment_report.xml',
        'views/adjustment_views.xml',
        'views/advance_inherit_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
