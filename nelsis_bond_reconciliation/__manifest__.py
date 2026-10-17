# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
{
    'name': 'Nelsis Bond Reconciliation',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Bond register, stock ledger and reconciliation on top of standard Odoo Inventory',
    'description': """
Nelsis Bond Warehouse - Module 06
=================================
* Bond register (read-only view over validated Odoo stock transactions)
* Detailed, filterable bond stock ledger with running balance
* Reconciliation workflow with discrepancy handling, review, approval and audited reopen
* 12 internal management reports (PDF / CSV / XLSX when xlsxwriter is available)

No independent inventory balance is stored. Standard Odoo stock is the source of
truth. Reports are INTERNAL MANAGEMENT REPORTS, not official statutory customs forms.
    """,
    'author': 'Nelsis Tech (Developer / Product Owner: Nur Uddin Ahammed)',
    'website': 'https://nelsistech.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'product', 'stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/stock_location_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_lot_product_views.xml',
        'views/bond_ledger_views.xml',
        'views/bond_register_views.xml',
        'views/bond_reconciliation_views.xml',
        'wizard/bond_reopen_wizard_views.xml',
        'wizard/bond_report_wizard_views.xml',
        'report/bond_report_templates.xml',
        'views/menus.xml',
    ],
    'external_dependencies': {'python': []},
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': ['nelsis_bond_reconciliation/static/src/scss/nelsis_ui.scss'],
    },
}
