{
    'name': 'Employee Advance',
    'version': '17.0.3.8.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Employee advance request: Supervisor check, Accounts final check and posting (inside Expenses app)',
    'depends': ['hr_expense', 'account', 'mail', 'payment_request_due_sync'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'report/letterhead.xml',
        'report/advance_claim_report.xml',
        'views/employee_advance_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}