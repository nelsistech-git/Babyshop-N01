# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed
{
    'name': 'Nelsis Bond Warehouse (Suite Core)',
    'version': '17.0.2.0.0',
    'category': 'Inventory/Bonded Warehouse',
    'summary': 'Integration core of the Nelsis Bond Warehouse suite: one install, one role set, one bond classification.',
    'description': """
Nelsis Bond Warehouse - Suite Core
==================================
Installs and connects every module of the suite:

* 01 nelsis_bond_compliance      - version-controlled compliance rules
* 02 nelsis_bond_license         - licenses, securities, entitlements
* 03 nelsis_lc_management / nelsis_commercial - LC lifecycle and commercial files
* 04 nelsis_bond_inventory       - bonded receipts and classification (source of truth)
* 05 nelsis_bond_movement        - controlled transfers / issues / returns / adjustments
* 06 nelsis_bond_reconciliation  - bond register, ledger, reconciliation, reports
* 07 nelsis_bond_dashboard       - dashboard, alerts, audit (depends on this core)

This core defines no business documents of its own. It provides:

* Suite roles (Operator / Manager / Auditor) that imply the matching role of every module.
* A single bond classification: the approved Bond Status of Bond Inventory drives the
  location classification used by Bond Movement and Bond Reconciliation.
* The LC model configuration (nelsis.lc) for Bond Inventory and Commercial Management.

No legal limit is pre-loaded. A software control is not an official customs approval.
""",
    'author': 'Nelsis Tech',
    'maintainer': 'Nur Uddin Ahammed (Nelsis Tech)',
    'website': 'https://nelsis.tech',
    'license': 'Other proprietary',
    'depends': [
        'base', 'mail', 'product', 'stock',
        'nelsis_bond_compliance',
        'nelsis_bond_license',
        'nelsis_lc_management',
        'nelsis_commercial',
        'nelsis_bond_inventory',
        'nelsis_bond_movement',
        'nelsis_bond_reconciliation',
    ],
    'data': [
        'security/groups.xml',
        'views/stock_location_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'post_init_hook': 'post_init_hook',
    'application': False,
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': ['nelsis_bond_warehouse/static/src/scss/nelsis_ui.scss'],
    },
}
