# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 4: Sample Development Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Sample Development Management System',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Complete garment sample lifecycle from buyer request to bulk production approval',
    'description': """
Smart Complete Garment Software — Sample Development Management System
=======================================================================
Module 4 of the Smart Complete Garment Software suite.

Manages the complete garment sample lifecycle — Proto, Fit, Size Set, PP,
Salesman and Shipment samples — from buyer request through material
reservation, sample room production, quality checking, buyer submission,
comments/revisions and final approval before bulk production.

Key Features
------------
* Sample Request intake (from Buyer, Merchandiser, Style, or Tech Pack)
* Sample Master linked to Style, Tech Pack and (later) BOM
* Sample Development Plan — activities with responsible person/dates/progress
* Material Reservation tracking (required/available/reserved/issued)
* Sample Room production tracking (operator, machine, operation)
* Sample QC checklist (measurement, workmanship, appearance)
* Multi-stage internal + buyer approval workflow
* Buyer Comment Management and Sample Revision tracking
* Sample Cost Management (material/labor/processing/packaging/courier/misc)
  with a dedicated cost approval workflow
* Sample Courier / Submission tracking to buyers
* AI Sample Assistant: image comparison, measurement verification against
  the Tech Pack, approval-probability prediction and similarity search —
  extends the shared Garment AI Engine
* Pattern Development Integration, real BOM linking, Sample Room Capacity
  Planning, Sample Calendar, buyer/QC/compliance tracking fields and an
  automated deadline/notification cron job
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_buyer_crm', 'garment_style_library', 'garment_techpack',
                'garment_bom_management'],
    'data': [
        'security/garment_sample_management_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_sample_type_data.xml',
        'data/ir_cron_data.xml',
        'views/garment_sample_type_views.xml',
        'views/garment_sample_request_views.xml',
        'views/garment_sample_views.xml',
        'views/garment_sample_activity_views.xml',
        'views/garment_sample_material_views.xml',
        'views/garment_sample_qc_views.xml',
        'views/garment_sample_cost_views.xml',
        'views/garment_sample_approval_comment_views.xml',
        'views/garment_sample_revision_views.xml',
        'views/garment_sample_courier_views.xml',
        'views/garment_sample_room_capacity_views.xml',
        'report/garment_sample_report.xml',
        'views/garment_sample_dashboard_views.xml',
        'views/garment_sample_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
