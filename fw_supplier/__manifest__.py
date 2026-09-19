# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Supplier Management - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Material quality inspection (GRN), delivery performance tracking, and '
                'periodic supplier scorecards with automatic grading.',
    'description': """
FW Supplier Management
=========================
Phase 3 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Tracks raw material supplier performance for footwear factories.

Features
--------
* Material GRN (Goods Receipt / Quality Inspection) with accept/reject
  quantities per delivery
* Delivery Performance tracking with promised vs actual date and
  automatic on-time / delay calculation
* Supplier Scorecard: aggregates quality acceptance rate and on-time
  delivery rate over a period into a weighted overall score and letter
  grade (A/B/C/D)

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_supplier_sequence.xml',
        'views/fw_material_grn_views.xml',
        'views/fw_supplier_delivery_views.xml',
        'views/fw_supplier_scorecard_views.xml',
        'views/fw_supplier_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
