# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 27: Advanced Analytics & Business Intelligence Platform
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Analytics & Business Intelligence',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Cross-module KPI framework, scheduled KPI snapshots, configurable tile dashboards '
               'and BI report scheduling built directly on the suite\'s own operational data',
    'description': """
Smart Complete Garment Software — Advanced Analytics & Business Intelligence Platform
=======================================================================================
Module 27 of the Smart Complete Garment Software suite.

This module is a genuine aggregation layer: it does not duplicate or shadow data
from any other module, it reads it. A KPI Definition points at a real model/field
already maintained by Order Management, Production, Quality, Costing, Finance or
HR, and a scheduled job calls the Odoo ORM's own ``read_group`` to compute and
store a periodic snapshot of it. Configurable dashboards are then built purely as
Odoo tree/kanban/graph/pivot views over those KPIs and snapshots — no custom OWL
widget, no external BI server, no fabricated machine-learning output.

Key Features
------------
* KPI Definition (garment.kpi.definition) — name, category (Production / Quality /
  Finance / Sales / Inventory / HR), department, source model, measure field,
  aggregation (sum/avg/count/min/max), optional group-by field and extra domain
  filter, frequency, target value and warning/critical thresholds
* KPI Snapshot (garment.kpi.snapshot) — one stored, timestamped, ``read_group``
  computed data point per KPI per period (optionally per group-by dimension),
  with variance vs. target and an on-target / warning / critical status
* Daily ``ir.cron`` job that walks every active KPI Definition, works out whether
  it is due for its configured frequency, and generates the snapshot(s) — a real
  scheduled ETL step, not a placeholder
* Dashboard Board (garment.dashboard.board) + Dashboard Tile (garment.dashboard.tile)
  — configurable tile dashboards; a tile is bound either to a KPI Definition (its
  tile shows the latest stored snapshot) or to its own raw source model + domain +
  measure (computed live on display) — rendered as a plain Odoo kanban-of-tiles
  view plus tree/form configuration screens, no JS/OWL involved
* Seed data ships an Executive, a Factory/Production, a Quality and a Finance
  dashboard board pre-wired to real KPIs over Order Management, Production,
  Quality, Costing, Finance and HR data
* Report Schedule (garment.report.schedule) — daily/weekly/monthly/yearly BI
  report definitions (recipients, format, delivery channel, send time) — fields
  only, the actual email/PDF rendering and delivery engine is deferred, see
  IMPLEMENTATION_NOTES.md
* Role-based access: BI Viewer, BI Analyst, Executive (read-only board access)
  and BI Manager (full access incl. report scheduling)

Deliberately Out of Scope (see IMPLEMENTATION_NOTES.md)
---------------------------------------------------------
Predictive analytics / AI insight generation, an AI chat assistant, Power BI /
external connector integration and actual outbound email or WhatsApp delivery
are all SRS items that would require either a genuine ML pipeline or a third
party integration outside a self-contained Odoo Community addon — they are
represented only where the SRS requires a configuration surface for them
(Report Schedule), and are explicitly flagged as deferred rather than faked.
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail',
        'garment_order_management',
        'garment_production',
        'garment_quality',
        'garment_costing',
        'garment_finance',
        'garment_hr',
    ],
    'data': [
        'security/garment_analytics_bi_security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/garment_kpi_definition_data.xml',
        'data/garment_dashboard_board_data.xml',
        'views/garment_kpi_definition_views.xml',
        'views/garment_kpi_snapshot_views.xml',
        'views/garment_dashboard_tile_views.xml',
        'views/garment_dashboard_board_views.xml',
        'views/garment_report_schedule_views.xml',
        'views/garment_analytics_bi_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
