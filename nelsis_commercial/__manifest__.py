# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
{
    'name': 'Nelsis Commercial Management',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Commercial',
    'summary': 'Commercial files, documents, shipments and Bill of Entry tracking for bonded warehouses',
    'description': """
Nelsis Commercial Management
============================
Commercial-documentation and traceability layer for Bangladesh leather and
footwear bonded warehouse operations. Links commercial files to an existing
LC model (configurable, never duplicated), shipments, Bills of Entry and
standard Odoo stock receipts. Does not maintain stock.

Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
    """,
    'author': 'Nelsis Tech (Developer: Nur Uddin Ahammed)',
    'website': 'https://nelsis.tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'stock'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/document_type_data.xml',
        'views/file_views.xml',
        'views/document_views.xml',
        'views/shipment_views.xml',
        'report/report_file_summary.xml',
        'data/cron_data.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'nelsis_commercial/static/src/scss/nelsis_ui.scss','nelsis_commercial/static/src/scss/nelsis.scss'],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}
