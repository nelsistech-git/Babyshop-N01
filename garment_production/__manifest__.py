# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 15: Production Management, Planning, MES & Shop Floor System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Production Management & MES',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Production planning, capacity, cutting, sewing, washing, finishing, packing, '
               'shop-floor MES, operator/line efficiency, WIP, downtime and production cost tracking',
    'description': """
Smart Complete Garment Software — Production Management & MES
=================================================================
Module 15 of the Smart Complete Garment Software suite — the MAIN CORE
production module. Merges four SRS specifications into one coherent design:
Production Management System, Garment Production Planning & MES System,
Advanced Manufacturing Execution System (MES), and Garment Production MES &
Shop Floor Management System.

Key Features
------------
* Production master setup: Work Centers, Machines, Production Lines,
  Operation Routing / SMV bulletin per style
* Production Planning: long/medium/short-term Production Plans, Capacity
  Planning, Line Allocation, Production Calendar, plan-level approvals
* Production Order (manufacturing order) management with BOM/routing/line
  linkage, real-time department progress and delivery-risk tracking
* Work Orders per operation/work-center with planned vs actual duration
* Material Issue-to-Floor workflow (request -> store approval -> issue) and
  Planned vs Actual Material Consumption / variance tracking
* Cutting Management: Fabric Relaxation, Marker (efficiency %), Cutting
  Orders, Cutting Bundles (barcode-tracked), Cutting QC
* Shop-floor MES: unified Production Entry capture (manual / tablet /
  barcode / IoT) across Cutting-Sewing-Washing-Finishing-Packing, Operator
  Assignment, Operator Performance scorecards, Hourly/Shift/Daily/Monthly
  Production Targets, Line Balancing & bottleneck detection
* Washing Management: Washing Orders, Washing Recipes, Chemical Consumption
* Finishing Management: Finishing Orders/Operations, Final Measurement Check
* Packing Management: Packing Orders and Carton tracking
* Machine Downtime, Production Issue/Andon alerts, Rework, WIP tracking,
  OEE (Availability x Performance x Quality) and Production Cost roll-up
* AI-assisted completion/delay prediction and bottleneck insight, extending
  the shared Garment AI Engine
* Full chatter/tracking, statusbar workflows and role-based security for
  Production Director / Manager / Planner / Supervisor / Operator
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail', 'portal',
        'garment_buyer_crm', 'garment_style_library', 'garment_bom_management',
        'garment_merchandising', 'garment_order_management', 'garment_tna',
        'garment_hr', 'garment_warehouse',
    ],
    'data': [
        'security/garment_production_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/garment_production_machine_views.xml',
        'views/garment_work_center_views.xml',
        'views/garment_production_line_views.xml',
        'views/garment_operation_routing_views.xml',
        'views/garment_production_plan_views.xml',
        'views/garment_capacity_plan_views.xml',
        'views/garment_line_allocation_views.xml',
        'views/garment_production_calendar_views.xml',
        'views/garment_production_order_views.xml',
        'views/garment_work_order_views.xml',
        'views/garment_production_entry_views.xml',
        'views/garment_operator_assignment_views.xml',
        'views/garment_operator_performance_views.xml',
        'views/garment_production_target_views.xml',
        'views/garment_production_material_issue_views.xml',
        'views/garment_production_consumption_views.xml',
        'views/garment_cutting_order_views.xml',
        'views/garment_fabric_relaxation_views.xml',
        'views/garment_cutting_marker_views.xml',
        'views/garment_cutting_bundle_views.xml',
        'views/garment_cutting_qc_views.xml',
        'views/garment_washing_order_views.xml',
        'views/garment_washing_recipe_views.xml',
        'views/garment_finishing_order_views.xml',
        'views/garment_measurement_check_views.xml',
        'views/garment_packing_order_views.xml',
        'views/garment_line_balancing_views.xml',
        'views/garment_machine_downtime_views.xml',
        'views/garment_production_issue_views.xml',
        'views/garment_production_rework_views.xml',
        'views/garment_wip_tracking_views.xml',
        'views/garment_production_oee_views.xml',
        'views/garment_production_cost_views.xml',
        'views/garment_production_dashboard_views.xml',
        'views/garment_production_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
