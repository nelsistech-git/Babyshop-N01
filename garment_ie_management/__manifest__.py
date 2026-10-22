# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 16: Industrial Engineering (IE) Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Industrial Engineering (IE) Management',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'SMV/time study, line balancing, skill matrix, capacity study, method/motion study '
               'and productivity engineering for garment production',
    'description': """
Smart Complete Garment Software — Industrial Engineering (IE) Management System
==================================================================================
Module 16 of the Smart Complete Garment Software suite. Provides the SMV /
work-study engineering layer that sits on top of the Production Management &
MES module (``garment_production``) — it does NOT redefine operation routing,
production lines, work centers or work orders; it studies, standardises and
improves the operations already modelled there.

Key Features
------------
* Operation Master library (operation code, department, machine type,
  required skill, standard SMV) feeding SMV and Time Study
* SMV Master Database — Style x Operation x Machine x Skill Level, with
  Basic Time + Allowance = SMV calculation, allowance breakdown (Personal /
  Fatigue / Delay / Machine Delay), versioning and an approval workflow
* Stopwatch Time Study — per-cycle observations, performance rating,
  Normal Time = Observed Time x Rating, allowance application and a
  one-click "Update SMV" action that pushes the studied time into the SMV
  Master
* Allowance Type master (Personal / Fatigue / Delay / Machine Delay policy)
* Operator Skill Matrix — per-employee, per-operation skill level,
  efficiency % and training status, feeding skill-based operator
  recommendation for an operation
* Line Balancing study — operation allocation to operators with SMV,
  required vs. actual capacity per hour, automatic bottleneck detection and
  a recommended-action list (add operator / resequence / skilled operator /
  improve method / change machine)
* Capacity Study — factory / order / forecast capacity simulation (daily
  capacity per line, required lines, estimated completion days, risk level,
  monthly booked vs. available capacity)
* Method Study and Motion Study — current vs. improved method/movement,
  time-saving analysis
* Workstation master (machine, table position, tools, attachments, operator)
* Work Sampling — random activity observations (working / idle / waiting /
  rework) with working-ratio computation
* Operator Productivity records — Target vs. Actual output, the standard
  garment-industry Efficiency % ( SMV x Output / Minutes Worked x 100 ) and
  SMV variance (standard vs. actual)
* IE Improvement Tracking — problem / root cause / action / before-after
  result with a cost-saving figure, workflow-driven
* AI IE Insight log — line balancing recommendation, SMV prediction,
  capacity forecast and productivity-coach entries (manual/API entry point,
  see IMPLEMENTATION_NOTES.md)
* Dashboards, list/tree/pivot/graph views and role-based security

Cross-Module Integration
-------------------------
* Style — ``garment.style`` (Style Library)
* Production Line / Work Order / Operation Routing & Routing Line /
  Production Order / Production Machine — ``garment_production`` (this
  module studies and improves those, it does not duplicate them)
* Employee / Operator — ``garment.hr.employee`` (HR & Payroll)
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'garment_style_library',
        'garment_production',
        'garment_hr',
    ],
    'data': [
        'security/garment_ie_management_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_ie_allowance_type_data.xml',
        'views/garment_ie_operation_views.xml',
        'views/garment_ie_allowance_type_views.xml',
        'views/garment_ie_smv_views.xml',
        'views/garment_ie_time_study_views.xml',
        'views/garment_ie_skill_matrix_views.xml',
        'views/garment_ie_line_balance_views.xml',
        'views/garment_ie_capacity_study_views.xml',
        'views/garment_ie_method_study_views.xml',
        'views/garment_ie_motion_study_views.xml',
        'views/garment_ie_workstation_views.xml',
        'views/garment_ie_work_sampling_views.xml',
        'views/garment_ie_productivity_record_views.xml',
        'views/garment_ie_improvement_views.xml',
        'views/garment_ie_ai_insight_views.xml',
        'views/garment_ie_dashboard_views.xml',
        'views/garment_ie_management_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
