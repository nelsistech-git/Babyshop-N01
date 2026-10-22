# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 33: Garment Product Lifecycle Management (PLM)
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Product Lifecycle Management (PLM)',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Stage-gate PLM governance layer: Concept-to-Production-Handover journey tracking, '
               'cross-functional team, gate sign-off and cross-module status dashboard',
    'description': """
Smart Complete Garment Software — Product Lifecycle Management (PLM)
=======================================================================
Module 33 of the Smart Complete Garment Software suite.

This module is the OVERARCHING governance layer of the PLM journey. Style
data, Tech Pack, BOM, Sample and Costing documents already live in their own
dedicated modules (Style Library, Tech Pack, BOM Management, Sample
Management, Costing) — this module does NOT re-model any of that. Instead it
adds a light-weight cross-module tracking layer on top of them:

Key Features
------------
* PLM Project — one record per style's end-to-end development journey,
  linking out to garment.style, garment.techpack, garment.bom,
  garment.sample and garment.costing rather than duplicating their data
* Stage-Gate tracker for the 7-stage journey: Concept -> Design -> Sourcing
  -> Sampling -> Costing -> Approval -> Production Handover, with planned
  vs. actual dates, SLA/target-date tracking and automatic delay detection
* Gate Sign-Off approvals per role (Designer / Merchandising / Technical /
  Quality / Buyer / Production) required to pass each stage gate
* Cross-functional Team Assignment (Merchandiser, Designer, Pattern Maker,
  Sample Coordinator, IE Engineer, Quality Team, Production Team)
* PLM Task Management for day-to-day development activities
* PLM Notification log (approval-pending / delay / handover alerts)
* AI Assist — extends the shared Garment AI Engine (Buyer CRM) with a
  development-risk and production-readiness insight for each PLM Project
* Cross-module PLM Dashboard (active projects, pending gate approvals,
  samples running, delayed stages, production-ready styles) built on the
  PLM Project record with kanban / graph / pivot views

Explicitly NOT rebuilt here (see IMPLEMENTATION_NOTES.md): Style master &
ECR/change-management (garment_style_library), Tech Pack authoring
(garment_techpack), BOM lines (garment_bom_management), Sample workflow
(garment_sample_management), Costing sheets (garment_costing) — this module
links to their existing models instead of duplicating them.
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail',
        'garment_buyer_crm',
        'garment_style_library',
        'garment_techpack',
        'garment_bom_management',
        'garment_sample_management',
        'garment_costing',
        'garment_hr',
    ],
    'data': [
        'security/garment_plm_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/garment_plm_project_views.xml',
        'views/garment_plm_stage_gate_views.xml',
        'views/garment_plm_team_task_views.xml',
        'views/garment_plm_notification_views.xml',
        'views/garment_plm_dashboard_views.xml',
        'views/garment_plm_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
