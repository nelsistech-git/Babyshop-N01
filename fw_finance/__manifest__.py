# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Finance Extension - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Style-level costing and profitability, factory-level periodic costing, '
                'and export/shipment costing (FOB vs landed cost) for footwear factories.',
    'description': """
FW Finance Extension
=======================
Phase 4 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Rolls up data from BOM Versions, Line Balancing (SMV), and Buyer Orders
into real cost and margin figures.

Features
--------
* Style Cost Sheet: material cost (pulled from a confirmed BOM Version),
  labor cost (optionally pulled from Line Balancing SMV x labor rate),
  overhead, and other cost, rolled into total cost, profit and margin %
  against the style's selling price
* Factory Costing: periodic (e.g. monthly) factory-level cost summary
  with a free-form expense line list (utilities, rent, admin salaries,
  etc.) and cost-per-pair
* Export Costing: FOB value vs. Cut & Make + freight + insurance +
  other export costs, to get net margin per Buyer Order

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_plm', 'fw_ie', 'fw_merchandising', 'fw_footwear_mrp', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_finance_sequence.xml',
        'views/fw_style_costing_views.xml',
        'views/fw_factory_costing_views.xml',
        'views/fw_export_costing_views.xml',
        'views/fw_finance_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
