{
    'name': 'Worker\'s Profit Participation Fund',
    'version': '17.0.0.0.1',
    'summary': """
     Redefining Retirement with WPPF, Where Your Future Begins Anew.
    """,
    'description': """
    Odoo 17's WPPF module offers a comprehensive solution for managing pension funds.
    From tracking contributions to processing withdrawals, it provides a user-friendly platform within a nice interface.
    Stay compliant and empower your workforce to plan for their retirement with ease.
    """,
    'category': 'hr',
    'author': 'Nelsis Tech Limited',
    'website': 'https://www.nelsistech.com',
    'license': 'LGPL-3',
    'depends': ['provident_fund'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_wppf_view.xml',
        'views/wppf_interest_disburse.xml',
        'views/wppf_profile_view.xml',
        'views/hr_employee_inherit_wppf.xml',
        'views/pf_provident_board_views.xml',
        'views/pf_committee.xml',
        'views/wppf_policy_views.xml',
        'wizard/wppf_statement_wizard_views.xml',
        'report/wppf_statement_report_tmpl.xml',
    ],
    'demo': [],
    'application': True,
    'installable': True,
    'auto_install': False
}
