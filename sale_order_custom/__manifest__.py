{
    'name': 'Sale Order Custom',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Custom fields and order lines for Sale Order',
    'author': 'Unified Information Technology Limited',
    'depends': ['sale_management', 'contacts', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'reports/invoice_report.xml',
        'reports/money_receipt_report.xml',
        'reports/money_receipt_template.xml',
        'reports/purchase_order_report.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
