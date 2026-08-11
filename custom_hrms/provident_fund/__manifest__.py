{
    'name': 'Provident Fund',
    'version': '17.0.0.0.1',
    'summary': """
    Seamless Solutions for Secure Savings: Provident Fund Simplified.
    """,
    'description': """
        Effortlessly manage employee provident funds with Odoo 17's dedicated Provident Fund module.
         Easily track contributions, manage payouts and ensure compliance with regulations, all within Odoo's user-friendly interface.
    """,
    'category': 'Human Resources/Payroll',
    'author': 'Nelsis Tech Limited',
    'website': 'https://www.nelsistech.com/',
    'license': 'LGPL-3',
    'depends': ['hr_payroll'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/pf_menu.xml',
        'views/pf_loan_policy_views.xml',
        'views/hr_employee_pf_view.xml',
        'views/hr_employee_inherit_pf.xml',
        'views/pf_membership_request_view.xml',
        'views/pf_profile_view.xml',
        'views/pf_provident_board_inherit_menu.xml',
        'views/pf_committee.xml',
        'views/pf_interest_disburse.xml',
        'views/agent_fee_views.xml',
        'views/agent_commission_type_views.xml',
        'views/pf_configuration_views.xml',
        'views/pf_interest_disburse.xml',
        'views/pf_provident_board_views.xml',
        'views/pf_provident_board_inherit_menu.xml',
        'report/pf_statement_report_tmpl.xml',
        'wizard/missing_pf_wizard_views.xml',
        'wizard/pf_statement_wizard_views.xml',
        'views/pf_accounts_day_book.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False
}
