# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Business Intelligence - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Periodic KPI Snapshot fact table plus graph/pivot analytics views '
                'across sales, efficiency, and costing data.',
    'description': """
FW Business Intelligence
===========================
Phase 5 module of the Nelsis Footwear ERP platform (Odoo Community 17).

SCOPE NOTE: This module is built entirely on Odoo's native, stable
list/graph/pivot view infrastructure. It deliberately does NOT include a
custom JavaScript/OWL dashboard controller: without a live Odoo instance
to render and test against, shipping untested front-end framework code
would risk silent breakage that static review cannot catch. Graph and
pivot views, by contrast, are declarative XML, well-documented, and safe
to hand-author with confidence.

Features
--------
* KPI Snapshot: a per-factory, per-period fact table that pulls together
  production qty, order count, quality (DHU% and AQL pass rate),
  average line efficiency, breakdown/downtime, sales value, and cost
  per pair - generated with one click from existing FW module data
* Graph and Pivot analytics views on the KPI Snapshot, Buyer Orders,
  Efficiency Reports, and Factory Costing for slicing by factory,
  period, buyer, and more

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': [
        'fw_core_master', 'fw_merchandising', 'fw_footwear_mrp', 'fw_quality',
        'fw_ie', 'fw_cmms', 'fw_finance',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_bi_sequence.xml',
        'views/fw_kpi_snapshot_views.xml',
        'views/fw_analytics_views.xml',
        'views/fw_bi_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
