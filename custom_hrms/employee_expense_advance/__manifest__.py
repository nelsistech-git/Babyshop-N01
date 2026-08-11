{
    'name': 'Expense Advance Request - Employee',
    'version': '17.0.0.0.1',
    'license': 'LGPL-3',
    'category': 'Human Resources',
    'summary': 'Allow employee to request expense in advance.',
    'description': """
        This module allows employees to request expense advances, manage advance requests, and track advance expenses. 
        It supports multi-currency and integrates with existing expense management workflows without altering accounting entries.
            """,
    'images': ['static/description/img1.jpg'],
    'author': 'Nelsis Tech Limited',
    'website': 'https://www.nelsistech.com',
    'depends': ['hr_expense'],
    'data': ['security/employee_advance_expense_security.xml',
             'security/ir.model.access.csv',
             'data/expense_sequence_data.xml',
             'views/employee_advance_expense.xml',
             'views/hr_expense.xml',
             'views/advance_expense_sheet.xml',
             'report/employee_advance_expense_report.xml'
             ],
    'installable': True,
    'application': False,
}
