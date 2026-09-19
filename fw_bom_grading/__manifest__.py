# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW BOM Size Grading - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Size-wise material consumption grading on top of FW Product PLM\'s '
                'BOM Version - larger sizes consume more material than smaller ones.',
    'description': """
FW BOM Size Grading
======================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

FW Product PLM's BOM (Module 2) stores one flat quantity per pair per
component. Real footwear costing needs size-wise consumption - a
size 45 boot uses noticeably more upper leather than a size 38 - which
matters both for accurate per-size costing and for correct total
material requirement planning against an order's size curve.

This module adds an optional size-wise consumption grading table per
BOM line, without changing the existing flat qty_per_pair field or any
existing costing logic in FW Product PLM or FW Finance - both continue
to work unmodified using the flat quantity as a fallback/average when
size grading is not defined for a component.

Features
--------
* Size Grading table per BOM component (one row per size, with a
  consumption multiplier or absolute quantity)
* "Generate from Size Curve" button auto-creates one row per size in
  the style's Size Curve, with the flat qty_per_pair as a starting
  default the user can then adjust up/down by size
* Computed total material requirement for a given order quantity
  broken down by size, useful for raw material purchase planning

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
        'security/ir.model.access.csv',
        'views/fw_bom_line_grading_views.xml',
        'views/fw_bom_size_grading_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
