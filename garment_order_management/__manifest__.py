# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 9: Garment Order Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Order Management',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Central buyer order (garment.order) — PO intake, style/color/size breakdown, approval, '
               'production release, multi-factory allocation, shipment, risk & delay tracking',
    'description': """
Smart Complete Garment Software — Garment Order Management System
===================================================================
Module 9 of the Smart Complete Garment Software suite.

The central control point of the whole ERP suite — the actual Sales /
Production Order (``garment.order``) that ties Buyer, Merchandising,
Costing, BOM, TNA, Production, Quality and Shipment together, from
Buyer PO receipt through shipment and order closure.

Key Features
------------
* Order Master (``garment.order``) — buyer PO details, style/brand/season,
  factory, merchandiser, currency, Incoterms, export/shipment terms,
  full status workflow (Draft -> PO Received -> Confirmed -> TNA Created ->
  Material Planning -> Production Running -> Quality Checking ->
  Ready For Shipment -> Shipped -> Completed -> Closed / Cancelled)
* Order origin linkage to the Merchandising Order Confirmation
  (``garment.merch.order.confirmation``) hand-over document
* Order Line (style/colorway/size-range/qty/price/value/delivery date) —
  one order can carry multiple styles
* Structured Color Information per line (buyer/factory color code, Pantone,
  lab dip reference, shade group, approval status)
* Size Ratio & Quantity Breakdown per order line with automatic quantity
  calculation from ratio percentages
* Order Approval Workflow (Order Received -> Merchandising Review ->
  Cost Verification -> Planning Review -> Management Approval -> Released
  For Production) with a full approval-stage log
* Order Validation Rules — confirmation blocked without approved costing,
  approved BOM, buyer PO, delivery date & completed sample approval;
  production release blocked without approved BOM, active TNA, planned
  materials & available capacity
* Order Document Checklist (Buyer PO, Tech Pack, BOM, Cost Sheet, Artwork,
  Measurement Chart, Sample Approval, export documents...) with
  Completed / Pending / Missing status tracking
* Material Requirement (Order Qty x BOM Consumption) & Material
  Availability tracking (Available / Partial / Shortage / Delayed)
* Production Capacity check (required vs. available vs. shortage)
* Multi-Factory / Multi-Line Order Allocation and Order Split management
  (style-wise, color-wise, quantity-wise, factory-wise, shipment-wise)
* Partial Shipment tracking with shipped / pending / balance quantity
* Real-time Order Tracking — per-stage progress (material, cutting, sewing,
  finishing, inspection) with an automatically computed overall %
* Order Delay & Recovery Planning (delay reason, delay days, recovery plan)
* Order Locking after confirmation — quantity/price/delivery/style changes
  require a logged Order Revision; closed orders become read-only
* AI Order Risk Prediction, AI Delivery Prediction and AI Order/Factory
  Allocation Optimization — extends the shared Garment AI Engine with a
  transparent rule-based scorer (works with or without an external
  AI provider configured)
* Buyer Portal order tracking (status, progress, shipment, documents) while
  costing, supplier and internal production data stay hidden from buyers
* Order Register, Progress, Delivery & Profitability reporting, and a
  printable Order Confirmation Sheet
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail', 'portal',
        'garment_buyer_crm', 'garment_style_library', 'garment_merchandising',
        'garment_bom_management', 'garment_costing', 'garment_tna',
        'garment_techpack', 'garment_sample_management',
    ],
    'data': [
        'security/garment_order_management_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/garment_order_views.xml',
        'views/garment_order_line_views.xml',
        'views/garment_order_shipment_views.xml',
        'views/garment_order_allocation_views.xml',
        'views/garment_order_risk_views.xml',
        'views/garment_order_document_views.xml',
        'views/garment_order_revision_views.xml',
        'views/garment_order_approval_views.xml',
        'views/garment_order_delay_views.xml',
        'report/garment_order_confirmation_report.xml',
        'views/garment_order_management_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
