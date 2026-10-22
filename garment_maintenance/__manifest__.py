# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 22/41: Maintenance & Asset Management System (CMMS)
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Maintenance & Asset Management (CMMS)',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Asset register, preventive/breakdown/calibration work orders, spare parts, '
               'downtime resolution, maintenance cost and MTTR/MTBF/OEE KPIs',
    'description': """
Smart Complete Garment Software — Maintenance & Asset Management System (CMMS)
=================================================================================
Merges two SRS documents into one coherent Computerized Maintenance Management
System (CMMS): "Maintenance & Asset Management System" (Module 22) and
"Garment Maintenance Management System (CMMS)" (Module 41). Both source
documents describe the same underlying factory maintenance operation with
different levels of detail; this module consolidates them into a single
design instead of building two overlapping sets of models.

Key Features
------------
* Non-production Asset Register (``garment.asset``) for utility assets
  (generator, compressor, transformer, chiller, HVAC, boiler) and facility
  assets (building, vehicle, computer, furniture, quality/testing
  instruments) with lifecycle, warranty and depreciation tracking.
  Production machinery is NOT re-modeled here — it reuses
  ``garment.production.machine`` from garment_production (see
  IMPLEMENTATION_NOTES.md).
* Maintenance Checklist templates, reusable across Preventive Maintenance
  Plans and Work Orders.
* Preventive Maintenance Plans / Schedules (daily / weekly / monthly /
  quarterly / yearly / custom interval) that generate Work Orders.
* Maintenance Work Orders covering Breakdown, Preventive, Calibration and
  AMC/Contract Service jobs, with priority-driven response targets,
  engineer inspection, manager cost approval, checklist execution, spare
  parts consumption and labor/spare/external cost roll-up.
* Work Orders are what RESOLVES ``garment.machine.downtime`` events already
  captured on the shop floor by garment_production — completing a breakdown
  Work Order closes the linked downtime record and returns the machine to
  running status.
* Spare Parts consumption against the shared Material Master
  (``garment.material``, category Spare Parts) with real stock-move
  postings, and a Spare Parts Reorder Request workflow that raises a real
  Purchase Requisition (``garment.purchase.requisition``, source =
  Maintenance Department) when stock falls below the reorder point.
* AMC / External Service Contract tracking against the shared Supplier
  Master (``garment.supplier``).
* Calibration Management for measurement/testing equipment with due-date
  and certificate-expiry tracking.
* Maintenance KPIs: MTTR, MTBF, Machine Availability, Breakdown Rate and PM
  Compliance % per machine/asset per period — complementing (not
  duplicating) the OEE already computed in garment_production
  (``garment.production.oee``).
* AI Predictive Maintenance insight log: breakdown risk prediction, spare
  parts demand forecasting and recommended maintenance scheduling.
* IoT sensor reading log (temperature, vibration, speed, power) with
  threshold-based maintenance alerting, for both production machines and
  other registered assets.
* Full chatter/tracking, statusbar workflows and role-based security for
  Maintenance Director / Manager / Engineer / Technician / Store Officer.

Cross-Module Integration
-------------------------
* Production machine & downtime — ``garment.production.machine`` /
  ``garment.machine.downtime`` (garment_production)
* Technician workforce — ``garment.hr.employee`` (garment_hr), extended
  in-place with maintenance specialization fields
* Spare parts / stock — ``garment.material`` / ``garment.stock.move`` /
  ``garment.warehouse`` (garment_warehouse)
* Spare parts reorder — ``garment.purchase.requisition`` /
  ``garment.purchase.request.line`` (garment_purchase)
* Service providers / calibration companies / AMC vendors —
  ``garment.supplier`` (garment_supplier)

See IMPLEMENTATION_NOTES.md for the full duplication-avoidance rationale.
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'portal',
        'garment_production',
        'garment_hr',
        'garment_warehouse',
        'garment_purchase',
        'garment_supplier',
    ],
    'data': [
        'security/garment_maintenance_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_maintenance_checklist_data.xml',
        'views/garment_asset_views.xml',
        'views/garment_maintenance_checklist_views.xml',
        'views/garment_maintenance_plan_views.xml',
        'views/garment_maintenance_workorder_views.xml',
        'views/garment_maintenance_spare_request_views.xml',
        'views/garment_maintenance_contract_views.xml',
        'views/garment_calibration_views.xml',
        'views/garment_maintenance_kpi_views.xml',
        'views/garment_maintenance_ai_prediction_views.xml',
        'views/garment_maintenance_iot_reading_views.xml',
        'views/garment_hr_employee_views.xml',
        'views/garment_maintenance_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
