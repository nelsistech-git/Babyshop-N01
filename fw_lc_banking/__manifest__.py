# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Letter of Credit & Banking - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Letter of Credit tracking against Buyer Orders, with required-document '
                'checklist, expiry/latest-shipment-date alerts, and discrepancy notes - '
                'the dominant payment mechanism for Bangladesh footwear export.',
    'description': """
FW Letter of Credit & Banking
================================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).
L/C is the primary payment instrument for Bangladesh footwear export
trade, and none of the modules built so far tracked it - this module
closes that gap.

Features
--------
* Letter of Credit master linked to a Buyer Order: issuing/advising
  bank, L/C type (Sight/Usance/Revolving/Transferable/Back-to-Back),
  amount, dates (issue/expiry/latest shipment date), partial shipment
  and transshipment permissions
* Required Document Checklist per L/C (Commercial Invoice, Packing
  List, B/L or AWB, Certificate of Origin, Beneficiary Certificate,
  Insurance Certificate, etc.) with submission tracking
* Discrepancy notes field for bank-flagged document discrepancies
* Daily scheduled action flags L/Cs nearing expiry or latest shipment
  date so nothing is missed
* Optional link from a Shipment (FW Merchandising) back to its L/C

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_merchandising', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_lc_banking_sequence.xml',
        'data/fw_lc_banking_cron.xml',
        'views/fw_letter_of_credit_views.xml',
        'views/fw_shipment_lc_link_views.xml',
        'views/fw_lc_banking_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
