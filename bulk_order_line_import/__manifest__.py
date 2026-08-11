# -*- coding: utf-8 -*-
{
    'name': 'Bulk Sales & Purchase Order Line Importer',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Bulk import Sales/Purchase order lines from Excel (.xlsx/.xls) or CSV files',
    'description': """
Bulk Sales & Purchase Order Line Importer
==========================================
Import large numbers of order lines into draft/sent Sales Orders and
Purchase Orders directly from an Excel (.xlsx / .xls) or CSV file, instead
of typing them one by one.

Features
--------
* "Import Lines" button on the Sales Order and Purchase Order forms
  (visible while the order is in Draft or Sent/RFQ state).
* Import wizard: upload a file, download a ready-to-fill sample template,
  and choose how duplicate product codes in the file should be handled
  (separate lines vs. merged quantities).
* Products are matched live against Inventory (product.product) by
  Internal Reference or Barcode - Unit of Measure, price, tax and
  description are pulled from the product master data the same way the
  standard Odoo UI would, unless overridden in the file.
* Robust, row-level validation (missing product, invalid quantity/price)
  with a single consolidated error report - nothing is created unless the
  whole file is valid.
    """,
    'author': 'Nelsis Tech',
#    'license': 'LGPL-3',
    'depends': ['base', 'sale_management', 'purchase', 'uom'],
    'external_dependencies': {
        'python': ['openpyxl', 'xlrd'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/bulk_order_line_import_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
