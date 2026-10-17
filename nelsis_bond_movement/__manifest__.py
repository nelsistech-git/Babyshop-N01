# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed
{
    'name': 'Nelsis Bond Warehouse - Stock Movements',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Controlled bonded transfers, issues, returns and approved stock adjustments',
    'description': """
Module 05 of the Nelsis Bond Warehouse suite.
Controls bonded/non-bonded material transfers, issues, returns and stock
adjustments using standard Odoo Inventory stock moves. No independent
stock balance is kept. Maker-checker approvals, audit trail and reversals.
Does not claim legal compliance; rules are configurable and must be reviewed
by a qualified Bangladesh customs professional.
    """,
    'author': 'Nelsis Tech (Developer / Product Owner: Nur Uddin Ahammed)',
    'website': 'https://nelsis.tech',
    'maintainer': 'Nelsis Tech',
    'depends': ['stock', 'mail'],
    'data': [
        'security/bond_movement_security.xml',
        'security/ir.model.access.csv',
        'data/bond_movement_data.xml',
        'views/bond_movement_reverse_views.xml',
        'views/bond_warehouse_movement_views.xml',
        'views/stock_location_views.xml',
        'views/bond_movement_menus.xml',
    ],
    'images': ['static/description/icon.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': ['nelsis_bond_movement/static/src/scss/nelsis_ui.scss'],
    },
}
