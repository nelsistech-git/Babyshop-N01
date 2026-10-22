# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 5: BOM (Bill of Materials) Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - BOM (Bill of Materials) Management System',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Fabric, trim and packaging material requirements, consumption, costing and approval',
    'description': """
Smart Complete Garment Software — BOM (Bill of Materials) Management System
=============================================================================
Module 5 of the Smart Complete Garment Software suite.

Defines every raw material, accessory, packaging material and production
input required to manufacture a garment style, and connects Style →
Tech Pack → BOM → Costing → Purchase Planning → Inventory → Production →
Accounting.

Key Features
------------
* BOM Master supporting Production / Sample / Costing / Buyer / Production
  Floor BOM types, with a full Draft → Active approval lifecycle
* Fabric BOM with net/gross consumption calculation and wastage breakdown
  (cutting/shrinkage/marker/process/shade/quality loss)
* Trim BOM (thread/zipper/button/label and other accessories)
* Packaging BOM (poly bag/carton/hang tag/barcode/tissue/hanger)
* Size-wise and Color-wise consumption breakdown
* Alternative Material management with buyer approval tracking
* Multi-stage approval workflow (Merchandiser → Technical → Costing →
  Purchase → Production → Approved) with approved-BOM locking
* BOM Change/Revision management with full history
* Supplier Mapping with approved/alternative/emergency supplier types and
  historical pricing
* Automatic material cost roll-up (fabric + trim + packaging + processing)
  and cost-per-piece calculation
* Purchase requirement calculation (Requirement − Available − Incoming)
  ready for the future Purchase/Inventory integration
* AI BOM Assistant: auto-suggest a starting BOM from the linked Style or
  Tech Pack's fabric/trim/label/packaging data, consumption prediction from
  historical BOMs, cost optimization suggestions and AI Risk Detection
  (material shortage / supplier delay / price increase) — extends the
  shared Garment AI Engine
* Full BOM Status Workflow (Draft -> ... -> Active -> Closed) wired to the
  BOM Approval Workflow, with an approval trail and activity notifications
* Consolidated Material Lines auto-synced from Fabric/Trim/Packaging BOM —
  the list read by Production Material Issue / Consumption
* BOM Template Management (Knit T-Shirt / Polo / Hoodie style templates)
* BOM Comparison Tool (Material / Consumption / Cost / Supplier diff)
* Material Reservation with automatic Shortage Alerts
* Material Price History with Supplier Ranking
* BOM Cost Variance Management (Estimated vs Actual)
* Bangladesh Garment Industry data (Yarn Count, Dye Lot, Shade Band, Marker
  Efficiency, Wash Loss) and Compliance tracking (GOTS/GRS/OEKO-TEX/RCS/HIGG)
* Simple JSON REST API (GET/POST/PUT /api/bom) matching the SRS API spec
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'account', 'garment_buyer_crm', 'garment_style_library', 'garment_techpack'],
    'data': [
        'security/garment_bom_management_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_bom_template_data.xml',
        'views/garment_bom_views.xml',
        'views/garment_fabric_bom_views.xml',
        'views/garment_trim_bom_views.xml',
        'views/garment_packaging_bom_views.xml',
        'views/garment_material_consumption_views.xml',
        'views/garment_material_alternative_views.xml',
        'views/garment_bom_price_history_views.xml',
        'views/garment_bom_supplier_views.xml',
        'views/garment_bom_approval_revision_views.xml',
        'views/garment_material_reservation_views.xml',
        'views/garment_bom_template_views.xml',
        'wizard/garment_bom_compare_wizard_views.xml',
        'wizard/garment_bom_template_apply_wizard_views.xml',
        'report/garment_bom_report.xml',
        'views/garment_bom_dashboard_views.xml',
        'views/garment_bom_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
