# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed
{
    'name': 'Nelsis Bond Warehouse - License & Entitlement',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Compliance',
    'summary': 'Bond licenses, general bond/security instruments and entitlement tracking',
    'description': """
Module 02 of the Nelsis Bond Warehouse suite (Odoo Community 17).

* Bond license records, renewals, suspension/cancellation history
* General bond / security instruments with renewal and release history
* Entitlement tracking with amendments and utilization derived from validated stock moves
* Configurable expiry reminders, role based access, audit trail

No legal limit, entitlement quantity or rate is hard-coded. Every rule applied
must be recorded and verified by an authorised reviewer.
    """,
    'author': 'Nelsis Tech',
    'maintainer': 'Nur Uddin Ahammed',
    'website': '',
    'license': 'Other proprietary',
    'depends': ['base', 'mail', 'product', 'stock'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/sequence.xml',
        'data/cron.xml',
        'wizard/status_wizard_views.xml',
        'views/config_views.xml',
        'views/license_views.xml',
        'views/security_views.xml',
        'views/entitlement_views.xml',
        'views/company_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': ['nelsis_bond_license/static/src/scss/nelsis_ui.scss'],
    },
}
