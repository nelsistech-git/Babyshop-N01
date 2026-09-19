# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW Accounting Integration - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Generate real Odoo Accounting customer invoices directly from Buyer '
                'Orders and Distribution Orders.',
    'description': """
FW Accounting Integration
============================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).

DESIGN NOTE - deliberately conservative scope: this module does NOT
build a parallel bookkeeping system. It creates real account.move
(Customer Invoice) records using Odoo's own native Accounting app, and
lets Odoo's own accounting views render and post them. This project
does not inherit or modify any Accounting view - invoices are opened
using their own default form, which Odoo resolves automatically. This
is the only responsible way to touch financial records without a live
instance to validate a custom accounting UI against: real money and
real tax/reporting compliance should run through Odoo's own tested
accounting engine, not a hand-built substitute.

Requires the Invoicing or Accounting app to be installed.

Features
--------
* "Create Invoice" button on a confirmed Buyer Order, generating a
  Customer Invoice with one line per order line (requires each Style
  to have a linked Product, so Odoo can determine the correct income
  account automatically)
* Same for Distribution Order (dealer/distributor/retail sales)
* Invoices remain traceable back to their source order

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'fw_merchandising', 'fw_distribution', 'account'],
    'data': [
        'views/fw_buyer_order_invoice_views.xml',
        'views/fw_distribution_order_invoice_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
