# -*- coding: utf-8 -*-
{
    'name': 'Nelsis Bond Warehouse - Demo Data',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Bonded Warehouse',
    'summary': 'Workflow-consistent demo data for the whole Nelsis Bond Warehouse suite (test databases only).',
    'description': """
Nelsis Bond Warehouse - Demo Data
=================================
Loads a complete, FICTITIOUS demonstration data set into every module of the suite:
compliance rules, licenses, securities, entitlements, LCs, commercial files, bonded
receipts, movements, utilizations, reconciliations, dashboard alerts and purchase orders
(bonded import, local, retro-linked to existing LCs and consignments).

All records are created by calling the real workflow methods as separate demo users
(maker / checker / approver), so the data respects the suite's controls.

No statutory value is loaded: every rule reference, limit and number is marked
"DEMO" / "fictitious". Install on a TEST database only.
""",
    'author': 'Nelsis Tech (demo data)',
    'license': 'Other proprietary',
    'depends': ['nelsis_bond_warehouse', 'nelsis_bond_dashboard', 'nelsis_bond_purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/demo_log_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': ['nelsis_bond_demo/static/src/scss/nelsis_ui.scss'],
    },
}
