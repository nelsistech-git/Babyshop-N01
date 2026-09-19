# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Warehouse - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Raw Material / WIP / Finished Goods zone setup, WIP cutting bundle '
                'tracking, and packing carton management with barcode, built on '
                'top of Odoo Inventory (stock).',
    'description': """
FW Warehouse
==============
Phase 3 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Uses Odoo's native Inventory app for real stock quantities and movements,
and adds footwear-specific WIP and packing tracking on top.

Features
--------
* One-click setup of Raw Material / WIP / Finished Goods child locations
  under each Factory's warehouse
* WIP Cutting Bundle tracking with barcode, linked to a Production Order
  and its current process stage
* Packing Carton management with per-size content breakdown, gross/net
  weight, and barcode - linked to Buyer Order Line and Shipment
* Quick stock-by-zone views per factory using native stock.quant

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_footwear_mrp', 'fw_merchandising', 'stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_warehouse_sequence.xml',
        'views/fw_factory_warehouse_views.xml',
        'views/fw_bundle_views.xml',
        'views/fw_carton_views.xml',
        'views/fw_warehouse_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
