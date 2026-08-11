# -*- coding: utf-8 -*-
{
    'name': "Daily Sale & Official Cost Report",
    'version': '17.0.1.0.0',
    'summary': "Automated, error-free daily reconciliation of Sales, Costs, "
               "Supplier Payments and Bank/bKash collections.",
    'description': """
Daily Sale & Official Cost Report (Odoo 17)
============================================
Fully automated daily cash/financial report built directly on top of
Accounting journal items (account.move, account.move.line, account.payment).

Features
--------
* Zero manual data entry - every figure is pulled live from posted
  accounting entries for the selected date.
* Showroom Sales, Official Cost, Supplier Transactions and Mobile/Bank
  (incl. bKash) sections, each mapped to a specific Odoo model/domain.
* Automatic bottom reconciliation panel computing Net Office Cash.
* Daily "Lock" so a generated report can never be silently changed by
  later edits to the underlying ledger.
* Date filter to regenerate the report for any day, instantly.
""",
    'category': 'Accounting/Reporting',
    'author': 'Nasim Ahmed',
    'license': 'LGPL-3',
    'depends': ['account', 'payment'],
    'data': [
        'security/ir.model.access.csv',
        'security/report_security.xml',
        'views/daily_report_views.xml',
        'views/daily_report_menus.xml',
        'report/daily_report_report.xml',
        'report/daily_report_template.xml',
    ],
    'installable': True,
    'application': True,
}
