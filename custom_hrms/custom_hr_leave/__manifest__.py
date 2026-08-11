{
    'name': 'Custom HR Leave',
    'version': "1.0.0",
    'category': 'Generic Modules/Human Resources',
    'summary': 'Custom HR Leave',
    'description': """
    Custom HR Leave
    """,
    'author': "Nelsis Tech Limited",
    'company': "Nelsis Tech Limited",
    'maintainer': "Nelsis Tech Limited",
    'website': 'https://nelsistech.com/',
    'depends': ['hr_holidays', 'custom_hr_employee'], #,'custom_hr_report'
    'images': ['static/description/banner.jpg'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/inherited_hr_leave_type_inherit_custom_hr_leave_views.xml',
        'views/inherited_hr_leave_inherit_custom_hr_leave_views.xml',
        # 'views/inherited_hr_leave_reports_inherit_custom_hr_leave_views.xml',
        'views/inherited_hr_employee_inherit_custom_hr_leave.xml',
        'reports/leave_report_tmpl.xml',
        'wizard/leave_report_wizard_views.xml',
        'reports/yearly_leave_summary_report_tmpl.xml',
        'wizard/yearly_leave_summary_report_wizard_views.xml',
        'wizard/hr_leave_auto_allocation_wizard_views.xml',
        #'wizard/print_leave_summary_view.xml',
        'views/leave_balance_report.xml',
        'views/inherited_resource_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True
}
