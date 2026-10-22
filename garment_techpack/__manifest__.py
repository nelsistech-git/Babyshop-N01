# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 3: Tech Pack Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Tech Pack Management System',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Digital technical specification hub connecting Style, BOM, Sampling, Production and Quality',
    'description': """
Smart Complete Garment Software — Tech Pack Management System
=======================================================================
Module 3 of the Smart Complete Garment Software suite.

Digitizes the traditional Excel/PDF tech pack into the single technical
source of truth shared by buyer, merchandising, sampling, production,
quality and engineering.

Key Features
------------
* Tech Pack Master linked to Style, with full construction/spec sheet
* Artwork (print/embroidery/heat-transfer/logo/label/packaging) management
* Label & Packaging specification
* Measurement Sheet — imports directly from the Style Library measurement chart
* Version control with minor/major revision classification and full history
* Technical review checklist (product/fabric/measurement/trim/packaging)
* Multi-stage internal + buyer approval workflow with digital signature
* Production Release Control — checks every prerequisite is approved before release
* Auto-generated technical/sampling/production tasks
* AI Tech Pack Assistant: buyer file OCR/text extraction, missing-data detection,
  specification validation and historical tech pack comparison — extends the
  shared Garment AI Engine from Buyer CRM / Style Library
* Full Tech Pack PDF, Production Specification Sheet, Buyer Approval Document
  and Production Release Certificate reports
* Version Comparison wizard, Calendar/Kanban deadlines and Revision/Approval
  trend analysis
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_buyer_crm', 'garment_style_library'],
    'data': [
        'security/garment_techpack_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/garment_techpack_views.xml',
        'views/garment_techpack_version_views.xml',
        'views/garment_tech_spec_construction_views.xml',
        'views/garment_artwork_views.xml',
        'views/garment_label_packaging_views.xml',
        'views/garment_measurement_sheet_views.xml',
        'views/garment_tech_review_approval_views.xml',
        'views/garment_tech_change_views.xml',
        'views/garment_tech_attachment_views.xml',
        'views/garment_techpack_task_views.xml',
        'wizard/garment_techpack_version_compare_views.xml',
        'report/garment_techpack_report.xml',
        'views/garment_techpack_dashboard_views.xml',
        'views/garment_techpack_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
