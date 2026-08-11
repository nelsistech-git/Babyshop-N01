{
    'name': 'Payment/Receive Report',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Payment and Receive Report with PDF and Excel export',
    'description': """
        Generates Payment/Receive Report from Journal Entries (account.move).
        Supports PDF and Excel export.
        Compatible with any Odoo 17 project that has the Accounting module.
    """,
    'author': 'BlueDream',
    'depends': ['account','custom_account_day_book'],
    'data': [
        'security/ir.model.access.csv',
        'report/account_payment_report_template.xml',
        'report/account_receive_payment_report_template.xml',
        'wizard/account_payment_report_wizard_views.xml',
        'wizard/account_receive_payment_report_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
