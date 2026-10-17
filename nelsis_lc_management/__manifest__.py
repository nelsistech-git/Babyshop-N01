# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
{
    'name': 'Nelsis LC Management',
    'version': '17.0.1.0.0',
    'summary': 'Letter of Credit lifecycle management for Bangladesh bonded-warehouse factories',
    'description': """
Nelsis LC Management
====================
Import LC lifecycle: application, approval, opening, amendments, shipments,
documents, Bill of Entry, warehouse receipt traceability, utilization and closure.

Standard Odoo Inventory remains the only stock ledger. This module only links
LC records to stock.picking; it never creates stock moves or quants.

Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
    """,
    'category': 'Inventory/Inventory',
    'author': 'Nelsis Tech',
    'maintainer': 'Nur Uddin Ahammed',
    'license': 'Other proprietary',
    'depends': ['base', 'mail', 'stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/sequences.xml',
        'data/document_types.xml',
        'data/setting_data.xml',
        'data/cron.xml',
        'views/lc_views.xml',
        'views/shipment_views.xml',
        'views/amendment_views.xml',
        'views/boe_views.xml',
        'views/document_views.xml',
        'views/config_views.xml',
        'wizard/wizard_views.xml',
        'views/stock_picking_views.xml',
        'views/menus.xml',
        'report/lc_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'nelsis_lc_management/static/src/scss/nelsis_ui.scss',
            'nelsis_lc_management/static/src/scss/lc.scss',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}
