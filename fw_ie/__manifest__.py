# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Industrial Engineering - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Time Study (SMV capture), Line Balancing, and Daily Efficiency reporting '
                'for footwear production lines.',
    'description': """
FW Industrial Engineering
============================
Phase 2 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Provides the classic garment/footwear IE toolkit on top of FW Core Master
and FW Advanced Manufacturing.

Features
--------
* Time Study: capture multiple stopwatch cycle readings per operation,
  apply performance rating and PFD allowance, derive Standard SMV, and
  push the approved SMV back onto the Operation Master
* Line Balancing: assign operations with SMV to a production line,
  auto-compute cycle time, manpower requirement per operation, bottleneck
  detection, and overall line balancing efficiency
* Daily Efficiency Report: compare actual floor output against the SMV
  benchmark to compute Earned Minutes, Available Minutes and Efficiency %

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_footwear_mrp', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_ie_sequence.xml',
        'views/fw_time_study_views.xml',
        'views/fw_line_balancing_views.xml',
        'views/fw_efficiency_report_views.xml',
        'views/fw_ie_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
