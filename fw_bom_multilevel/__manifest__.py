# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW BOM Multi-Level (Sub-Assembly) - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Optional sub-assembly BOM link on a BOM component line, with automatic '
                'cost sync from the sub-assembly and circular-reference protection.',
    'description': """
FW BOM Multi-Level (Sub-Assembly)
=====================================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

FW Product PLM's BOM (Module 2) is a flat, single-level list of
components. Some footwear components are themselves pre-assembled
sub-units with their own bill of materials (a pre-made outsole unit,
a pre-assembled strap or buckle unit). This module adds an optional
"this component is itself a BOM" link on a BOM line, without changing
Module 2's existing model or its cost computation chain at all - the
existing unit_cost -> line_cost logic keeps working exactly as before.
When a sub-assembly BOM is linked, this module simply keeps unit_cost
in sync with that sub-BOM's own total cost.

Features
--------
* Link a BOM Version as the "sub-assembly BOM" for any component line
* One-click sync of that line's Unit Cost from the sub-assembly's
  current Total Cost (call again any time the sub-BOM changes)
* Circular-reference protection: a BOM cannot (directly or through any
  chain of sub-assemblies) reference itself

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_plm'],
    'data': [
        'views/fw_bom_line_subassembly_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
