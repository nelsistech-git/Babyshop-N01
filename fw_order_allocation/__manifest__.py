# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Order Allocation & Subcontracting - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Split a single buyer order line across owned and subcontractor (CMT) '
                'factories with commission calculation and material-out/goods-in '
                'subcontract tracking - the buying-house and CMT layer.',
    'description': """
FW Order Allocation & Subcontracting
=======================================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).
This is the architectural layer that makes the platform work for THREE
business models at once without changing anything in the modules
already built:

1. Export-oriented factory (owns production) - unchanged, uses
   FW Merchandising + FW Advanced Manufacturing directly.
2. Local / Subcontractor (CMT) factory - this module's Subcontract
   Order tracks material sent out and finished goods received back,
   with a conversion (CMT) fee per pair.
3. Buying House / Corporate Buying Office - this module's Order
   Allocation splits one buyer order line across multiple factories
   (owned and/or subcontracted) and calculates commission on top.

Design
------
* fw.factory (FW Core Master) gains one additive field: relationship_type
  (Owned / Subcontractor / External Vendor). Nothing else changes there.
* fw.order.allocation sits ABOVE fw.buyer.order.line (FW Merchandising),
  splitting its quantity across one or more factories.
* fw.subcontract.order is generated per subcontractor allocation line,
  tracking material-out and finished-goods-in independently of your own
  stock/production flow.

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_merchandising', 'fw_footwear_mrp', 'fw_quality',
                'product', 'uom', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_order_allocation_sequence.xml',
        'views/fw_factory_relationship_views.xml',
        'views/fw_order_allocation_views.xml',
        'views/fw_subcontract_order_views.xml',
        'views/fw_order_allocation_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
