# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Sales Distribution - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Dealer / Distributor / Retail channel master, local distribution '
                'sales orders, and warranty claim tracking.',
    'description': """
FW Sales Distribution
========================
Phase 4 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Covers the domestic sales channel of a footwear business - separate from
the export Buyer Order flow in FW Merchandising.

Features
--------
* Channel Partner master (Dealer / Distributor / Retail Outlet) with
  credit limit and territory
* Distribution Sales Order with style/color/size-curve lines
* Warranty Claim tracking with resolution workflow (Repair / Replace /
  Reject / Refund)

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
        'data/fw_distribution_sequence.xml',
        'views/fw_channel_partner_views.xml',
        'views/fw_distribution_order_views.xml',
        'views/fw_warranty_claim_views.xml',
        'views/fw_distribution_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
