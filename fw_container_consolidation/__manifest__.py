# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Container Consolidation - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Group multiple Shipments (each against their own Buyer Order) into a '
                'single Container / Vessel booking - freight consolidation for '
                'factories shipping several smaller orders together.',
    'description': """
FW Container Consolidation
=============================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

FW Merchandising's Shipment (Module 3) is deliberately one-shipment-
per-buyer-order, which is correct for tracking each order's delivery.
But physically, factories very often load several smaller orders'
cartons into the SAME container or vessel booking to optimize freight
cost. This module adds that layer without changing Shipment's existing
structure: a Container Consolidation groups several Shipments together
and aggregates their quantity and weight for the actual freight
booking.

Features
--------
* Container Consolidation record: mode, container/vessel number, port
  of loading/discharge, ETD/ETA
* Link multiple Shipments (across different Buyer Orders) to one
  consolidation
* Auto-aggregated total quantity shipped and total gross weight
  (pulled from FW Warehouse's Packing Cartons on each linked shipment)

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_merchandising', 'fw_warehouse'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_container_consolidation_sequence.xml',
        'views/fw_container_consolidation_views.xml',
        'views/fw_shipment_consolidation_link_views.xml',
        'views/fw_container_consolidation_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
