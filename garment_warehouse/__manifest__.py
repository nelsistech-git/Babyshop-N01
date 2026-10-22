# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 11: Warehouse & Inventory Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Warehouse & Inventory Management System',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Warehouse/bin management, material master, stock ledger, cycle counting, fabric roll tracking, barcode/RFID',
    'description': """
Smart Complete Garment Software — Warehouse & Inventory Management System
=============================================================================
Module 11 of the Smart Complete Garment Software suite.

Note on source material: three overlapping SRS documents existed for this
domain (Inventory & Warehouse Management System, Garment Warehouse &
Inventory Management System, Garment Warehouse & Inventory Intelligence
System). This module is built from the largest and most detailed of the
three, whose own "Inventory Database Models" table names exactly 8
models — this module follows that list precisely rather than inventing
additional ones, folding closely related sub-features (material category,
batch/lot tracking, material reservation) into the 8 official models as
selections, embedded fields, or stock-move types.

This module introduces the Material Master (garment.material) that BOM,
Purchase and Sample have referenced only as free text so far — a natural
foundation for tighter integration in a future iteration, without
retrofitting five already-delivered modules today.

Key Features
------------
* Warehouse structure (Raw Material / Accessories / Chemical / Spare
  Parts / Finished Goods) and Zone → Rack → Shelf → Bin location hierarchy
* Material Master with min/max stock, reorder level, and live computed
  on-hand / reserved / available quantities
* GRN (Gate Entry + Goods Receipt + Quality Inspection integration) linked
  to Module 9 Purchase Orders and Deliveries
* Stock Movement ledger (Receipt / Issue / Return / Transfer / Adjustment
  / Reservation) — the single source of truth for on-hand quantity
* Fabric Roll tracking with batch/lot fields and full traceability
  (roll → order consumption)
* Barcode and RFID Tag management for warehouse automation, with
  scan-to-relocate and unauthorized-gate-movement flagging
* AI Inventory Intelligence: reorder point suggestion (reading Module 5
  BOM demand and Module 9 purchase forecasts), slow-moving stock
  detection, and putaway location suggestion — extends the shared
  Garment AI Engine

Gap-upgrade additions (union of the three Warehouse/Inventory SRS docs)
------------------------------------------------------------------------
* Bin-level capacity/utilization and location purpose (storage / gate /
  quality hold / staging) on top of the Zone-Rack-Shelf-Bin hierarchy
* Cycle Counting / Physical Inventory (garment.stock.count) with ABC
  classification, ledger-snapshot variance, and a Manager-approval step
  that posts audited adjustment stock moves
* Manager-approval gate on Adjustment / Return / Transfer stock moves
  (garment.stock.move.action_approve_movement), matching the SRS
  "Inventory Approval Rules"
* A "New Stock Transfer" wizard that posts the paired transfer_out /
  transfer_in moves together instead of two unlinked records
* Min/Max reorder: one-click Purchase Requisition creation from a
  low/out-of-stock material (links into garment_purchase)
* Stock aging (0-30 / 31-90 / 90+ day buckets), slow-moving and dead-stock
  flags, plus a daily scheduled action for low-stock/expiry/dead-stock
  activities
* Bangladesh fabric-roll fields: shade number + approval, lot number,
  relaxation time, inspection status; chemical batch/expiry/hazard
  fields and accessory color/size/buyer-approval on the material master
* Warehouse KPIs (space utilization, pending GRNs, low-stock count, GRN
  processing time) as smart buttons and dashboard pivots/graphs
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_style_library', 'garment_bom_management', 'garment_purchase'],
    'data': [
        'security/garment_warehouse_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_warehouse_data.xml',
        'data/ir_cron_data.xml',
        'views/garment_warehouse_views.xml',
        'views/garment_location_views.xml',
        'views/garment_material_views.xml',
        'views/garment_grn_views.xml',
        'views/garment_stock_move_views.xml',
        'views/garment_fabric_roll_views.xml',
        'views/garment_barcode_views.xml',
        'views/garment_rfid_tag_views.xml',
        'views/garment_stock_count_views.xml',
        'wizard/garment_stock_transfer_wizard_views.xml',
        'report/garment_grn_report.xml',
        'views/garment_warehouse_dashboard_views.xml',
        'views/garment_warehouse_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
