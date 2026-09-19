# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Quality - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Inline QC per production stage, AQL-based sampling inspection '
                '(Final / Pre-Shipment), and defect code tracking for footwear factories.',
    'description': """
FW Quality
============
Phase 2 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Builds on FW Advanced Manufacturing (production stages) and FW
Merchandising (shipments) to provide floor-level and shipment-level
quality control.

Features
--------
* Defect Code master with category and severity classification
* Inline QC recorded directly against a production stage line, with
  DHU (Defects per Hundred Units) auto-calculation
* AQL Sampling Table: an editable reference master for sample size and
  Accept/Reject numbers by lot-size range and inspection level -
  IMPORTANT: shipped with commonly used reference default values only.
  Always verify against your buyer's official AQL requirement / ISO
  2859-1 chart before relying on this for compliance decisions.
* AQL Inspection (Inline / Final / Pre-Shipment) with automatic
  sample-size lookup and Pass/Fail determination

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_footwear_mrp', 'fw_merchandising', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_quality_sequence.xml',
        'data/fw_aql_table_data.xml',
        'views/fw_defect_code_views.xml',
        'views/fw_aql_table_views.xml',
        'views/fw_inline_qc_views.xml',
        'views/fw_aql_inspection_views.xml',
        'views/fw_quality_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
