# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Product PLM - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Product Lifecycle Management for footwear: Tech Packs, BOM Versioning, '
                'Sample Tracking & Approval, Engineering Change Notices (ECN).',
    'description': """
FW Product PLM
===============
Phase 1 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Builds on FW Core Master to manage the full product development lifecycle
of a footwear style before it enters mass production.

Features
--------
* Tech Pack management with construction spec lines
* Versioned Bill of Materials (BOM) with automatic costing
* Sample lifecycle tracking (Proto, Fit, SMS, PP, Size-Set, TOD) with
  buyer approval workflow
* Engineering Change Notice (ECN) with before/after component tracking
  and approval routing

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'product', 'uom', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_plm_sequence.xml',
        'views/fw_techpack_views.xml',
        'views/fw_bom_version_views.xml',
        'views/fw_sample_views.xml',
        'views/fw_ecn_views.xml',
        'views/fw_plm_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
