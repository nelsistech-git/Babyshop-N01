# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Merchandiser Target & Achievement - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Periodic booking target per merchandiser, with achievement auto-computed '
                'from confirmed Buyer Orders on their assigned Buyers.',
    'description': """
FW Merchandiser Target & Achievement
========================================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).
A Buyer (FW Core Master) can have Assigned Merchandisers. This module
sets a periodic order-booking value target per merchandiser and
computes actual achievement from confirmed Buyer Orders placed by
their assigned buyers within the period - a straightforward, real KPI
tool rather than a duplicate of FW Business Intelligence's factory-
level dashboards.

Features
--------
* Target record: merchandiser, period, target order value and qty
* One-click "Compute Achievement" pulls confirmed Buyer Orders (order
  date within the period, buyer's Assigned Merchandisers includes this
  person) and sums qty/value
* Achievement % with a simple visual indicator

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_merchandising'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_merchandiser_kpi_sequence.xml',
        'views/fw_merchandiser_target_views.xml',
        'views/fw_merchandiser_kpi_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
