{
    'name': 'Employee KPI',
    'version': '17.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Daily KPI Tracking with Monthly and Yearly Summary',
    'description': """
        Employee KPI Module for Odoo 17 Community Edition.
        Features:
        - KPI Configuration (L1-L5 Rating Scale with Incentive %)
        - Daily KPI Entry with auto Level & Incentive from Config
        - Monthly KPI Summary (auto-computed from Daily)
        - Yearly KPI Summary (auto-computed from Monthly)
        - 2-step Approval Workflow
        - PDF Report
        - Chatter + Activity Tracking
    """,
    'author': 'Blue Dream',
    'depends': ['hr', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/kpi_config_views.xml',
        'views/daily_kpi_views.xml',
        'views/menu_views.xml',
        'report/daily_kpi_report.xml',
        'report/daily_kpi_report_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
