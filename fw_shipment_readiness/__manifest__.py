# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Shipment Readiness - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'One consolidated "Ready to Ship" gate on the Shipment record, pulling '
                'together QC result, carton packing, export documents, and L/C status '
                'from across FW Quality, FW Warehouse, and FW Letter of Credit.',
    'description': """
FW Shipment Readiness
========================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

Before this module, "is this shipment actually ready to leave" required
checking four different screens: AQL inspection result (FW Quality),
carton packing status (FW Warehouse), export document status (FW
Merchandising), and L/C document submission (FW Letter of Credit).
This module does not duplicate any of that data - it inherits the
existing Shipment record and adds computed readiness fields that read
straight from those other modules, so the answer is visible in one
place without a second system of record.

Features
--------
* QC Ready: at least one AQL Inspection is linked, completed, and
  passed, with no failed inspections still unresolved
* Cartons Ready: at least one Packing Carton is linked and all are
  packed or shipped
* Export Docs Ready: linked Export Tracking record has moved past
  Draft status
* L/C Ready: no L/C linked, OR all its required documents are
  submitted
* Overall Ready flag and a plain-language summary of what's still
  outstanding

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_merchandising', 'fw_quality', 'fw_warehouse',
                'fw_lc_banking'],
    'data': [
        'views/fw_shipment_readiness_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
