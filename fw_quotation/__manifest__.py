# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Quotation - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Formal itemized Quotation document for a Buyer or CRM Lead, with '
                'validity period and one-click conversion into a real Buyer Order.',
    'description': """
FW Quotation
==============
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

FW CRM (Module 19) tracks a lead's rough expected revenue as a single
number. FW Merchandising's Buyer Order (Module 3) is the real,
confirmed order. Neither covers the step in between: a formal,
itemized Quotation - style/color/qty/price lines with a validity
period - that gets sent to a prospective buyer (or an existing one
requesting a new price) for review and negotiation before any order
is confirmed.

Features
--------
* Quotation linked to either a Buyer or a CRM Lead (or both, once a
  lead has been converted), with style/color/qty/unit price lines
* Validity period with automatic Expired status once past that date
* One-click "Convert to Buyer Order" once accepted - requires a Buyer
  (converts a linked Lead first if needed to be explicit, since a
  Quotation is commercial and a real Buyer record should exist before
  a real Order does)

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_crm', 'fw_merchandising'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_quotation_sequence.xml',
        'data/fw_quotation_cron.xml',
        'views/fw_quotation_views.xml',
        'views/fw_quotation_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
