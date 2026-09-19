# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW HR Manufacturing - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Worker skill matrix, individual worker output capture, and '
                'incentive/piece-rate calculation for footwear factory workers.',
    'description': """
FW HR Manufacturing
======================
Phase 4 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Adds shop-floor HR tracking on top of standard Odoo HR (Employees).

IMPORTANT DESIGN NOTE: FW Advanced Manufacturing's Daily Output
(fw.production.daily.output) is captured at the process-stage/line level,
not per individual worker - it reflects what a whole stage produced in a
shift, which is the correct granularity for production and IE reporting.
Piece-rate incentive calculation needs individual-operator output, which
is different data. This module therefore introduces its own Worker
Output model for that purpose rather than assuming a connection that
does not exist in the data.

Features
--------
* Worker Skill Matrix: skill level per employee per operation
  (Trainee/Semi-Skilled/Skilled/Expert) with certification date
* Worker Output: individual daily piece count per employee/operation,
  the basis for piece-rate incentive calculation
* Incentive Scheme master (Piece Rate / Efficiency Bonus) and periodic
  Worker Incentive calculation

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
        'data/fw_hr_sequence.xml',
        'views/fw_worker_skill_views.xml',
        'views/fw_worker_output_views.xml',
        'views/fw_incentive_scheme_views.xml',
        'views/fw_worker_incentive_views.xml',
        'views/fw_hr_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
