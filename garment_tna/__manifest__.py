# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 8: TNA (Time & Action Calendar) Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - TNA (Time & Action Calendar) Management System',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Order execution timeline, milestones, dependencies, delay tracking and shipment risk',
    'description': """
Smart Complete Garment Software — TNA (Time & Action Calendar) Management System
===================================================================================
Module 8 of the Smart Complete Garment Software suite — the last piece of
the Commercial Front phase, and the order execution timeline that every
downstream department (Production, Quality, Shipment) will plan against.

Key Features
------------
* TNA Master per order, buyer-specific Template support (e.g. Buyer A —
  Knitwear vs Buyer B — Woven timelines) with "days before shipment"
  activity generation
* TNA Activity management across 6 categories (Merchandising, Product
  Development, Material, Production, Quality, Commercial) with
  Finish-to-Start / Start-to-Start / Finish-to-Finish dependencies
* Milestone tracking (PP Approval, Fabric Approval, Production Start,
  Final Inspection, Shipment)
* Automatic delay calculation with a 5-level severity scale (Normal / Low
  / Medium / High / Critical) and structured delay reasons
* 4-level auto-escalation (Responsible Person → Department Manager →
  General Manager → Managing Director) with multi-channel notification
  logging (Odoo / Email / SMS / WhatsApp / Push)
* TNA Risk register (rule-based Order Risk Score + Main Issue) and a
  Department Review approval workflow, with a full Draft → Generated →
  Department Review → Active → Monitoring → Completed → Closed status
  workflow and department-scoped record rules (Purchase/Production/QA/
  Commercial each only touch their own category)
* Gantt-ready activity data (planned/actual dates, dependency, progress %,
  computed Gantt colour status) — Odoo Community ships no Gantt widget, so
  the Calendar view is the working substitute
* Automatic TNA Creation on Order Confirmation, cron-driven 7/3/1-day and
  daily-overdue Reminders, 4-level Auto Escalation, and dependency-aware
  workflow blocking (Finish-to-Start / Start-to-Start / Finish-to-Finish)
* TNA Revision Management for major timeline changes on an Active/
  Monitoring/Completed TNA, with full chatter audit trail on Activities
* AI TNA Intelligence: shipment risk scoring, shipment probability %,
  expected delay days, delay-probability estimate from historical
  activity/supplier delay data, and schedule adjustment suggestions —
  extends the shared Garment AI Engine
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_buyer_crm', 'garment_style_library', 'garment_techpack',
                'garment_bom_management', 'garment_merchandising', 'garment_costing'],
    'data': [
        'security/garment_tna_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_tna_template_data.xml',
        'data/ir_cron_data.xml',
        'views/garment_tna_views.xml',
        'views/garment_tna_activity_views.xml',
        'views/garment_tna_template_views.xml',
        'views/garment_tna_milestone_views.xml',
        'views/garment_tna_delay_views.xml',
        'views/garment_tna_risk_views.xml',
        'views/garment_tna_approval_views.xml',
        'views/garment_tna_notification_views.xml',
        'views/garment_tna_revision_views.xml',
        'report/garment_tna_report.xml',
        'views/garment_tna_dashboard_views.xml',
        'views/garment_tna_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
