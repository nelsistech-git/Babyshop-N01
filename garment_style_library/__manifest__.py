# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 2: Style Library & Product Development
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Style Library & Product Development',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Central style master, PLM lifecycle, colorways, measurements, patterns, CAD and revision control',
    'description': """
Smart Complete Garment Software — Style Library & Product Development
=======================================================================
Module 2 of the Smart Complete Garment Software suite.

Central repository for every garment style and product specification —
the single source of truth used by Merchandising, BOM, Costing, Sampling,
Production and Quality.

Key Features
------------
* Style Master with product classification, attributes, fabric/trim specs
* Product Development Request intake (from Buyer CRM RFQs)
* Colorway (Style Color) management with Pantone / buyer-color mapping
* Structured Image Gallery & Digital Asset (document) library
* Size Set master supporting International / Numeric / Children's / Custom systems
* Measurement Chart with per-point base size, grade rule & tolerance
* Grade Rule engine with automatic size-set grading calculation
* Pattern & CAD File management (marker length/width/efficiency/consumption)
* Style Revision (version control) log — approved styles lock against direct edits
* Engineering Change Request (ECR) workflow
* Reusable Style Templates (default BOM / measurement / grading / packaging)
* AI-Assisted Style Similarity — extends the shared Garment AI Engine from
  Buyer CRM to surface similar historical styles, costs and sample outcomes
* Full PLM lifecycle + Style Approval workflow with electronic sign-off log,
  configurable Approval Rules and automatic missing-asset alerts
* Configurable Style Number generation (Year + Product-Category code +
  running sequence), Measurement Point master, Document Type/Tag masters
* Grade Rule calculation preview wizard and QWeb print formats (Style
  Specification Sheet, Approval Sheet, Pattern Report)
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_buyer_crm'],
    'data': [
        'security/garment_style_library_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_style_category_data.xml',
        'data/garment_size_set_data.xml',
        'data/garment_measurement_point_data.xml',
        'views/garment_style_category_views.xml',
        'views/garment_style_views.xml',
        'views/garment_style_development_request_views.xml',
        'views/garment_style_color_views.xml',
        'views/garment_style_image_document_views.xml',
        'views/garment_size_set_views.xml',
        'views/garment_measurement_chart_views.xml',
        'views/garment_grade_rule_views.xml',
        'views/garment_pattern_cad_views.xml',
        'views/garment_style_revision_ecr_views.xml',
        'views/garment_style_approval_views.xml',
        'views/garment_style_config_views.xml',
        'views/garment_style_template_views.xml',
        'views/garment_style_dashboard_views.xml',
        'wizard/garment_grade_rule_preview_wizard_views.xml',
        'report/garment_style_spec_sheet_report.xml',
        'report/garment_style_approval_sheet_report.xml',
        'report/garment_pattern_report.xml',
        'views/garment_style_library_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
