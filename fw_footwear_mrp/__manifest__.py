# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Advanced Manufacturing - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Footwear-specific production execution: Cutting, Stitching (Upper), '
                'Sole/Assembly (Lasting), and Finishing/Packing stage tracking with '
                'daily output capture, built on top of Odoo MRP.',
    'description': """
FW Advanced Manufacturing
===========================
Phase 2 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Footwear production does not fit a single-operation MRP flow: a pair of
shoes moves through distinct process stages (Cutting, Stitching/Upper,
Assembly/Lasting, Finishing/Packing), usually on different lines, with
daily output and rejection reporting per stage.

Features
--------
* Footwear Production Order per buyer-order line, linked to Style, BOM
  Version, Factory and Production Line
* Multi-stage process tracking (Cutting / Stitching / Assembly / Finishing)
  with planned vs completed quantities
* Daily output entry per stage/line with defect quantity capture
* Optional link to a standard Odoo Manufacturing Order (mrp.production)
  for stock/inventory integration
* Adds Style / Buyer Order / Factory / Line reference fields directly on
  the standard Manufacturing Order form

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_plm', 'fw_merchandising', 'mrp', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_footwear_mrp_sequence.xml',
        'views/mrp_production_views.xml',
        'views/fw_production_order_views.xml',
        'views/fw_daily_output_views.xml',
        'views/fw_footwear_mrp_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
