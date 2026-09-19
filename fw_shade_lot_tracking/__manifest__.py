# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Shade & Lot Tracking - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Material lot/batch and shade code tracking with consumption records '
                'against production orders and WIP bundles - for shade-matching QC '
                'and batch traceability/recall.',
    'description': """
FW Shade & Lot Tracking
==========================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

Leather, synthetic uppers, and other footwear materials vary subtly in
shade between production batches from the same supplier. Mixing lots
within a single style/color run causes visible shade mismatch across
pairs - a common cause of buyer rejection. This module tracks material
lots with a shade code, and records which lot was consumed against
which Production Order / WIP Bundle, giving both shade-consistency
control on the floor and full batch traceability if a defect needs to
be traced back to its source material.

Features
--------
* Material Lot register: lot/batch number, shade code, supplier,
  quantity received, running remaining quantity, optional link to the
  originating GRN (FW Supplier Management) for traceability
* Lot Consumption records against a Production Order and/or WIP Bundle
  (FW Advanced Manufacturing / FW Warehouse), with automatic remaining-
  quantity calculation
* Quarantine status for a lot suspected of shade mismatch, to hold it
  out of use until resolved

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_supplier', 'fw_footwear_mrp', 'fw_warehouse',
                'product', 'uom'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_shade_lot_sequence.xml',
        'views/fw_material_lot_views.xml',
        'views/fw_shade_lot_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
