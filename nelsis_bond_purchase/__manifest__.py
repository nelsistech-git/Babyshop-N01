# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
{
    'name': 'Nelsis Bond Purchase',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Purchase orders linked to LC, commercial file, entitlement, bonded consignments and bond receipts',
    'description': """
Nelsis Bond Purchase
====================
Connects standard Odoo Purchase with the Nelsis Bond Warehouse suite.

* Purchase type: local / import bonded / import non-bonded.
* Links a purchase order to its Letter of Credit, commercial file and bond entitlement.
* Confirmation checks: LC supplier / currency / limit, bond-eligible products, entitlement availability.
* Bonded orders get no standard receipt: goods enter through bond consignments and bond receipts.
* A validated bond receipt updates the order's received quantity (at the order price) and carries
  the LC, Bill of Entry, license and entitlement references to the transfer, LC and commercial file.
* Create LC, commercial file and consignment from the order; smart buttons on every linked record.

No statutory value is stored. A software check is not an official customs approval.
    """,
    'author': 'Nelsis Tech',
    'maintainer': 'Nur Uddin Ahammed (Nelsis Tech)',
    'website': 'https://nelsistech.com',
    'license': 'Other proprietary',
    'depends': ['purchase_stock', 'nelsis_bond_warehouse', 'nelsis_bond_dashboard'],
    'data': [
        'security/groups.xml',
        'views/purchase_order_views.xml',
        'views/linked_views.xml',
        'views/res_config_settings_views.xml',
        'data/dashboard_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'web.assets_backend': ['nelsis_bond_purchase/static/src/scss/nelsis_ui.scss'],
    },
}
