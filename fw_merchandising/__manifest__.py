# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Merchandising - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Buyer Order management, Time & Action (TNA) calendar, Shipment, '
                'and Export document tracking for footwear export factories.',
    'description': """
FW Merchandising
==================
Phase 1 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Manages the commercial order-to-shipment cycle for a footwear export
factory, built on top of FW Core Master.

Features
--------
* Buyer Order with style/color/size-curve order lines and auto costing
* Time & Action (TNA) critical-path milestones per order, with
  planned vs actual dates and delay tracking
* Shipment management with partial-shipment lines against order lines
* Export document tracking (LC, Invoice, BL/AWB, Customs)

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
        'data/fw_merchandising_sequence.xml',
        'views/fw_buyer_order_views.xml',
        'views/fw_shipment_views.xml',
        'views/fw_export_tracking_views.xml',
        'views/fw_merchandising_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
