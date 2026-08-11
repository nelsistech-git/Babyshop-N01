{
    'name': 'Baby Shop - Daily Reports',
    'version': '17.0.1.0.0',
    'summary': 'Daily Bank Expense Report, Stock Ledger and Store Report for Baby Shop Ltd branches',
    'description': """
Baby Shop Ltd - Daily Reports
==============================
Adds three daily reports, entered branch/showroom-wise, working correctly
across the multi-company (branch) structure of BABY SHOP LTD:

1. Bank Expense Report  -> under Sales > Reporting
2. Stock Ledger         -> under Inventory > Reporting
3. Store Report         -> under Sales > Reporting

Each report has a simple daily entry form so Area Managers / Store Managers
can type the day's figures directly into Odoo (replacing the Google Sheet
that was used before), and a print button that produces a PDF in exactly
the same layout as the previous manual reports.
    """,
    'author': 'Nelsis Tech',
    'category': 'Sales',
    'depends': ['base', 'sale', 'stock', 'account', 'sales_team'],
    'data': [
        'security/ir.model.access.csv',
        'views/bank_expense_views.xml',
        'views/stock_ledger_views.xml',
        'views/store_report_views.xml',
        'views/menus.xml',
        'report/bank_expense_report.xml',
        'report/stock_ledger_report.xml',
        'report/store_report_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
