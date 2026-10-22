# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 16: Quality Management System (QMS)
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Quality Management System (QMS)',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Incoming, in-process & final garment quality control, AQL inspection, defect logging and CAPA',
    'description': """
Smart Complete Garment Software — Quality Management System (QMS)
====================================================================
Module 16 of the Smart Complete Garment Software suite. Consolidates three
overlapping SRS revisions (base QMS, Garment QMS and Advanced Garment QMS)
into a single, coherent quality management design covering the complete
quality lifecycle from incoming raw material to final shipment approval.

Key Features
------------
* Quality Standards master (buyer / product / process, AQL level, tolerance)
* Defect Code master library (category, defect group, severity, department)
* Quality Checkpoints — stage-specific inspection checklist templates
  (Incoming, Fabric, Accessory, Cutting, Sewing Inline, End Line, Washing,
  Finishing, Final/AQL)
* Quality Inspection — one unified document for every inspection stage,
  tied to GRN / material for incoming QC and to the shop floor for
  in-process QC, with checklist execution lines and measurement lines
* Defect logging against a defect code, with location, department,
  responsible person, corrective action and status tracking
* AQL Sampling & Final Inspection with automatic lot/sample-size decision
  logic, buyer portal approval/rejection and shipment release control
* Quality Test Reports (shrinkage, GSM, color fastness, pull strength, etc.)
* Repair / Rework management with re-inspection
* CAPA (Corrective And Preventive Action) with root cause linkage
* Root Cause Analysis (5-Why, Fishbone, Pareto)
* Buyer Quality Complaint management with resolution workflow
* Quality Audit management (Internal / Buyer / Compliance / Process /
  Pre-Production / Inline / Social) with findings and CAPA follow-up
* AI Quality Insight log — risk prediction, defect trend, supplier score,
  computer-vision detection and IoT monitoring entry points
* Pass / Fail / Hold disposition workflow on every inspection document
* Dashboards, list/kanban/pivot/graph views and role-based security

Cross-Module Integration
-------------------------
* Style — ``garment.style`` (Style Library)
* Incoming material — ``garment.grn`` / ``garment.grn.line`` / ``garment.material``
  (Warehouse & Inventory)
* Supplier — ``garment.supplier`` (Supplier / Vendor Management)
* Buyer — ``garment.buyer`` (Buyer CRM)
* Production / shop floor — soft text reference (see IMPLEMENTATION_NOTES.md);
  ``garment_production`` is a declared dependency for future hardening once
  that sibling module's Production Order model is finalized.
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
        'garment_style_library',
        'garment_warehouse',
        'garment_supplier',
        'garment_buyer_crm',
        'garment_production',
    ],
    'data': [
        'security/garment_quality_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_quality_defect_code_data.xml',
        'data/garment_quality_checkpoint_data.xml',
        'views/garment_quality_standard_views.xml',
        'views/garment_quality_defect_code_views.xml',
        'views/garment_quality_checkpoint_views.xml',
        'views/garment_quality_inspection_views.xml',
        'views/garment_quality_defect_views.xml',
        'views/garment_aql_inspection_views.xml',
        'views/garment_quality_test_report_views.xml',
        'views/garment_quality_rework_views.xml',
        'views/garment_quality_capa_views.xml',
        'views/garment_quality_rca_views.xml',
        'views/garment_quality_complaint_views.xml',
        'views/garment_quality_audit_views.xml',
        'views/garment_quality_ai_analysis_views.xml',
        'views/garment_quality_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
