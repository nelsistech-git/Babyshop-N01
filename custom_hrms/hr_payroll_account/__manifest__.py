#-*- coding:utf-8 -*-
{
    'name': 'Payroll Accounting',
    'category': 'Human Resources/Payroll',
    'description': """
        Generic Payroll system Integrated with Accounting.
        ==================================================
        
            * Expense Encoding
            * Payment Encoding
            * Company Contribution Management
        """,
    'author': 'Nelsis Tech Limited',
    'company': 'Nelsis Tech Limited',
    'maintainer': 'Nelsis Tech Limited',
    'website': 'https://nelsistech.com/',
    'depends': ['hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payroll_data.xml',
        'wizard/individual_salary_payment_views.xml',
        'wizard/salary_payment_wizard_views.xml',
        'views/hr_payroll_account_views.xml',
        'views/salary_payment_views.xml',
    ],
    'demo': ['data/hr_payroll_account_demo.xml'],
    #'test': ['../account/test/account_minimal_test.xml'],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
