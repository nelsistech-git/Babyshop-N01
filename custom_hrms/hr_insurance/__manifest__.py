
{
    'name': 'Employee Insurance',
    'version': '17.0.1.0.1',
    'summary': """Employee Insurance Management for  HRMS.""",
    'description': """Manages insurance amounts for employees to be deducted 
    from salary""",
    'category': 'Generic Modules/Human Resources',
    'author': 'Nelsis Tech Limited',
    'maintainer': 'Nelsis Tech Limited',
    'company': 'Nelsis Tech Limited',
    'website': 'https://www.nelsistech.com',
    'depends': ['base', 'hr', 'hr_payroll', 'hr_contract'],
    'data': [
        'security/ir.model.access.csv',
        'security/hr_insurance_security.xml',
        'views/hr_employee_views.xml',
        'views/employee_insurance_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/insurance_policy_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
