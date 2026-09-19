# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Export Documents - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Printable PDF export documents: Commercial/Proforma Invoice from the '
                'Buyer Order, and Packing List from the Shipment (carton-wise breakdown).',
    'description': """
FW Export Documents
======================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Standard, well-documented QWeb PDF reports - no custom dashboard or
untested front-end code, just Odoo's own native report rendering
pipeline applied to data already captured in FW Merchandising and
FW Warehouse.

Features
--------
* Commercial / Proforma Invoice - printable from a Buyer Order, listing
  style/color/qty/unit price/amount per line with order and buyer
  details
* Packing List - printable from a Shipment, listing carton-by-carton
  size content, qty, and weight, pulled from FW Warehouse's Packing
  Carton records

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_merchandising', 'fw_warehouse', 'web'],
    'data': [
        'report/fw_buyer_order_invoice_report.xml',
        'report/fw_shipment_packing_list_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
