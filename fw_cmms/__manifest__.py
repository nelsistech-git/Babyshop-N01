# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Maintenance (CMMS) - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Machine Master, Preventive Maintenance scheduling, Breakdown '
                '(corrective maintenance) tracking, and Spare Parts management.',
    'description': """
FW Maintenance (CMMS)
========================
Phase 2 module of the Nelsis Footwear ERP platform (Odoo Community 17).
A self-contained Computerized Maintenance Management System for footwear
factory machines, built on top of FW Core Master.

Features
--------
* Machine Master linked to Factory / Production Line / Operation
* Preventive Maintenance Schedule with configurable frequency, checklist
  templates, and generated PM Task work orders
* Breakdown (corrective maintenance) tracking with priority, downtime
  calculation, and spare parts consumption
* Spare Parts master with simple stock quantity and reorder-level alerts

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_cmms_sequence.xml',
        'views/fw_machine_views.xml',
        'views/fw_spare_part_views.xml',
        'views/fw_pm_schedule_views.xml',
        'views/fw_breakdown_views.xml',
        'views/fw_cmms_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
