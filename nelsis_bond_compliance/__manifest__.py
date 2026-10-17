# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
{
    'name': 'Nelsis Bond Compliance',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Bonded Warehouse',
    'summary': 'Version-controlled regulatory rule register for Bangladesh bonded warehouses',
    'description': """
Nelsis Bond Warehouse - Module 01: Compliance Core
==================================================
Reusable, version-controlled compliance configuration layer for bonded
warehouse management (Bangladesh leather / footwear / leather goods).

* Regulatory rule register with official references and source URLs
* Effective-from / effective-to dates, rule versions and superseded-rule handling
* Applicable license / factory category (never assumed)
* Required-document and validation-parameter configuration
* Review -> approval -> activation workflow with segregation of duties
* Compliance exception records with approval and expiry
* Rule evaluation interface for other modules (bond.compliance.engine)
* Immutable evaluation log that keeps the rule version used for each result
* Reviewer / approver activities and scheduled reminders

This addon contains NO statutory values. All legal parameters must be entered
and verified from official sources and reviewed by a qualified Bangladesh
customs professional. A software validation is not an official customs approval.
    """,
    'author': 'Nelsis Tech',
    'maintainer': 'Nur Uddin Ahammed',
    'website': 'https://nelsis.tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/bond_compliance_master_data.xml',
        'views/bond_compliance_reject_wizard_views.xml',
        'views/bond_compliance_master_views.xml',
        'views/bond_compliance_rule_views.xml',
        'views/bond_compliance_exception_views.xml',
        'views/bond_compliance_evaluation_views.xml',
        'views/menus.xml',
        'data/ir_cron_data.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': ['nelsis_bond_compliance/static/src/scss/nelsis_ui.scss'],
    },
}
