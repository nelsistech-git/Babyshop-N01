# -*- coding: utf-8 -*-
{
    'name': 'Inter-Company / Branch Stock Transfer',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Automate stock transfers between companies/branches with auto-generated SO & PO',
    'description': """
Inter-Company / Branch Stock Transfer
======================================
Automates stock transfers between multiple companies or branches within a
single Odoo database.

Features
--------
* Dedicated Transfer wizard/document under Inventory > Operations.
* Auto-generates a Sales Order in the Source Company and a linked Purchase
  Order in the Destination Company.
* Smart buttons to jump directly to the generated SO / PO / Delivery / Receipt.
* Full state workflow: Draft -> In Progress -> Done -> Cancelled.
* Multi-company security with dedicated access group and record rules.
    """,
    'author': 'Nelsis Tech',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'sale_management', 'purchase', 'stock', 'account'],
    'external_dependencies': {
        'python': ['openpyxl', 'xlrd'],
    },
    'data': [
        'security/inter_company_transfer_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'wizard/bulk_transfer_line_import_views.xml',
        'views/inter_company_transfer_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
