# -*- coding: utf-8 -*-
{
    'name': 'Express Retail Sales (Server-Side POS)',
    'version': '17.0.2.1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Lightweight server-side driven retail checkout console built on Sale Order',
    'description': """
Express Retail Sales
=====================
A lightweight, server-side driven, single-page retail checkout interface
built on top of the standard Odoo Sales, Inventory and Accounting engines.

Features:
---------
* Single page OWL checkout console (product grid + cart)
* Barcode scanning with live stock guard
* Walk-in customer with quick contact creation
* Hold Cart / Parked Orders (multi draft management)
* One-Click Checkout automation (confirm -> deliver -> invoice -> post)
* Multi-Journal split payment registration
* Express Return / Exchange engine with credit note + refund payment
* 80mm thermal receipt auto-print
* Multi-branch console: branch/brand switcher, per-branch staff scoping and
  branch-aware security rules (Cashiers/Branch Managers only ever see their
  own branch's sales)
* Live KPI ribbon (today's sales, order count, average basket, held carts)
* Category quick-filter chips and a redesigned, branded checkout screen
* Optional "Sell on Credit / Due" tender for registered customers
* Sales Analysis reporting (pivot/graph) across branch, brand, cashier,
  product and category, respecting the same branch-visibility rules
* Two ready-made thermal receipt/invoice layouts - a Bangladesh-style cash
  memo and a Dubai/UAE-style VAT Tax Invoice (TRN, 5% VAT breakdown) -
  auto-selected per branch (or company-wide default), with manual override
  print actions for either format
""",
    'author': 'Nelsis Tech',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'stock', 'account', 'product', 'web'],
    'external_dependencies': {
        'python': [],
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'report/paperformat.xml',
        'report/receipt_report.xml',
        'report/receipt_template.xml',
        'views/express_pos_views.xml',
        'views/express_approval_views.xml',
        'views/express_brand_views.xml',
        'views/express_day_closing_views.xml',
        'views/express_pos_report_views.xml',
        'views/express_loyalty_views.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'express_retail_pos/static/src/js/express_pos_console.js',
            'express_retail_pos/static/src/js/express_pos_payment_dialog.js',
            'express_retail_pos/static/src/js/express_pos_quick_customer_dialog.js',
            'express_retail_pos/static/src/js/express_pos_return_dialog.js',
            'express_retail_pos/static/src/xml/express_pos_console.xml',
            'express_retail_pos/static/src/xml/express_pos_payment_dialog.xml',
            'express_retail_pos/static/src/xml/express_pos_quick_customer_dialog.xml',
            'express_retail_pos/static/src/xml/express_pos_return_dialog.xml',
            'express_retail_pos/static/src/css/express_pos.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
