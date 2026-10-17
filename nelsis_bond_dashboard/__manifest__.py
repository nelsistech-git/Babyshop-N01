# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed
{
    'name': 'Nelsis Bond Dashboard, Alerts & Audit',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Bonded Warehouse',
    'summary': 'Bonded warehouse dashboard, configurable compliance alerts and read-only audit access.',
    'description': """
Nelsis Bond Warehouse - Module 07
=================================
* Role-based, data-driven dashboard (every figure is read live from Odoo records).
* Configurable alert rules with scheduled evaluation, Odoo activities and notifications.
* Read-only audit access to validated stock history (no separate audit ledger).
""",
    'author': 'Nelsis Tech (Developer: Nur Uddin Ahammed)',
    'maintainer': 'Nelsis Tech',
    'license': 'Other proprietary',
    # 'nelsis_bond_warehouse' is the suite core: it installs the license, inventory, movement,
    # reconciliation, LC and commercial modules that define the models read here.
    'depends': ['base', 'mail', 'stock', 'nelsis_bond_warehouse'],
    'data': [
        'security/groups.xml',
        'security/suite_roles.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/cron_data.xml',
        'data/kpi_data.xml',
        'data/alert_rule_data.xml',
        'views/alert_views.xml',
        'views/rule_views.xml',
        'views/kpi_views.xml',
        'views/audit_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'nelsis_bond_dashboard/static/src/scss/nelsis_ui.scss',
            'nelsis_bond_dashboard/static/src/scss/dashboard.scss',
            'nelsis_bond_dashboard/static/src/js/dashboard.js',
            'nelsis_bond_dashboard/static/src/xml/dashboard.xml',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
}
