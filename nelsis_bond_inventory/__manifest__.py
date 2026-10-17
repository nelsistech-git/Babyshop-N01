# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
{
    'name': 'Nelsis Bond Inventory',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Bonded inventory and goods receipt workflow on top of standard Odoo Inventory',
    'description': """
Nelsis Bond Inventory (Module 04 of Nelsis Bond Warehouse)
==========================================================

Extends standard Odoo Inventory for bonded warehouse operations in Bangladesh
leather and footwear factories, without creating a duplicate stock engine.

Features
--------

* Bonded / non-bonded classification of locations, products and lots.
* Controlled classification changes (request, evidence and approval).
* Bond receipt workflow: Draft, Document Verification, Inspection, Approval (if required), Ready for Validation, Done.
* Consignments with partial and multiple receipts, LC and Bill of Entry references.
* Shortage, excess, damaged and rejected quantity tracking.
* Leather unit support (pieces, kg, sqm, sqft).
* Lot, batch and expiry traceability; stock report by location, product, LC and Bill of Entry.

All stock is posted through standard stock.picking, stock.move and stock.move.line.
Developer and Product Owner: Nur Uddin Ahammed, Nelsis Tech.
""",
    'author': 'Nelsis Tech',
    'maintainer': 'Nur Uddin Ahammed (Nelsis Tech)',
    'website': 'https://nelsistech.com',
    'license': 'Other proprietary',
    'depends': ['stock', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/document_type_data.xml',
        'data/uom_data.xml',
        'views/receipt_views.xml',
        'views/consignment_views.xml',
        'views/classification_views.xml',
        'views/master_views.xml',
        'views/report_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': ['nelsis_bond_inventory/static/src/scss/nelsis_ui.scss'],
    },
}
