# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Procurement - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'RFQ (multi-vendor quote comparison), Purchase Order, and receipt '
                'tracking - linked to FW Supplier Management GRN inspection.',
    'description': """
FW Procurement
================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

DESIGN NOTE: This module implements its own lightweight Purchase Order
model rather than deep-inheriting Odoo's native purchase.order form
view. That form has many nested tabs and a complex structure I cannot
verify with certainty without a live instance; a wrong xpath there
would risk breaking the whole module on install. A self-contained,
fully-controlled model is the safer and more honest engineering choice
here - the same reasoning applied to FW Maintenance (CMMS) earlier in
this build. It links properly to FW Supplier Management's Material GRN
model (which this project does own and fully control) via a new,
additive po_id field.

Features
--------
* RFQ with multiple vendor quote lines for side-by-side comparison
* Purchase Order with line items, received-quantity tracking
* Material GRN (FW Supplier Management) gains a proper PO link, on top
  of its existing free-text PO Reference field

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_supplier', 'product', 'uom', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_purchase_sequence.xml',
        'views/fw_rfq_views.xml',
        'views/fw_purchase_order_views.xml',
        'views/fw_material_grn_po_link_views.xml',
        'views/fw_purchase_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
