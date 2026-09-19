# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Rework & Repair - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Structured rework/repair workflow for defects found in Inline QC or '
                'AQL Inspection, with re-inspection result and scrap tracking.',
    'description': """
FW Rework & Repair
=====================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

FW Quality (Module 6) records defects at the point they're found -
Inline QC and AQL Inspection - but has no structured workflow for what
happens next: sending defective pairs back for repair, tracking who
reworked them and how long it took, re-inspecting the reworked units,
and recording units that turn out to be unrepairable (scrap). This
module closes that loop.

Features
--------
* Rework Order linked to its source (an Inline QC or AQL Inspection
  record) and the Production Order, with defect lines reusing the
  existing Defect Code master
* Assigned technician/team, start/end dates
* Re-inspection result (Pass / Fail) with the ability to route a
  failed re-inspection back into another rework cycle
* Scrap quantity tracking for units deemed unrepairable

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_quality', 'fw_footwear_mrp', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_rework_sequence.xml',
        'views/fw_rework_order_views.xml',
        'views/fw_rework_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
