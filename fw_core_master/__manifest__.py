# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Core Master - Footwear ERP Foundation',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Foundation master data module for Footwear ERP (Style, Color, Size, '
                'Season, Buyer, Factory, Production Line, Operation).',
    'description': """
FW Core Master
===============
Phase 1 Foundation module of the Nelsis Footwear ERP platform built on Odoo
Community 17. Provides master data objects consumed by every downstream
footwear module (PLM, Merchandising, Footwear MRP, IE, Quality, CMMS,
Warehouse, Finance, HR, BI).

Master Objects
--------------
* Style Master     - fw.style
* Color Master     - fw.color
* Size Master / Size Curve - fw.size, fw.size.curve
* Season Master    - fw.season
* Buyer Master     - fw.buyer
* Factory Master   - fw.factory
* Production Line Master - fw.production.line
* Operation Master (SMV-ready) - fw.operation

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['base', 'mail', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/fw_style_views.xml',
        'views/fw_color_views.xml',
        'views/fw_size_views.xml',
        'views/fw_season_views.xml',
        'views/fw_buyer_views.xml',
        'views/fw_production_line_views.xml',
        'views/fw_factory_views.xml',
        'views/fw_operation_views.xml',
        'views/fw_core_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
