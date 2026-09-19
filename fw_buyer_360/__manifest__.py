# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Buyer 360 - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Buyer compliance certificate tracking with expiry alerts, factory audit '
                '& Corrective Action Plan (CAP) tracking, and negotiated price agreements.',
    'description': """
FW Buyer 360
==============
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).
Extends the thin Buyer master from FW Core Master into full buyer
relationship management for export compliance.

Features
--------
* Compliance Certificates: BSCI, WRAP, SEDEX, ISO 9001/14001/45001,
  GOTS, OEKO-TEX, etc. with automatic expiry status (Valid / Expiring
  Soon / Expired)
* Factory Audits: buyer-conducted audits with score, result, findings,
  and a Corrective Action Plan (CAP) line list with responsible person,
  target date, and closure tracking
* Price Agreements: negotiated FOB price bands per buyer, by style or
  category and season, with validity dates

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_buyer_360_sequence.xml',
        'data/fw_buyer_360_cron.xml',
        'views/fw_buyer_compliance_views.xml',
        'views/fw_buyer_audit_views.xml',
        'views/fw_buyer_price_agreement_views.xml',
        'views/fw_buyer_form_inherit_views.xml',
        'views/fw_buyer_360_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
