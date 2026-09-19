# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Capacity Planning - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Visual calendar of production line bookings against confirmed buyer '
                'orders, with required-days auto-calculated from rated line capacity.',
    'description': """
FW Capacity Planning
=======================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).
A factory or buying house juggling several confirmed orders across a
limited number of production lines needs to see, at a glance, which
lines are booked when - this module provides that view.

Features
--------
* Line Booking record: production line, buyer order, date range,
  booked quantity
* Required days auto-calculated from the line's rated daily capacity
  (FW Core Master), with an overbooking warning if the date range is
  too short for the booked quantity
* Calendar view colored by production line, plus a standard list/form

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
        'data/fw_capacity_planning_sequence.xml',
        'views/fw_line_booking_views.xml',
        'views/fw_capacity_planning_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
