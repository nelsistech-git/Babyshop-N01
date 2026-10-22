# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 10: Supplier / Vendor Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Supplier / Vendor Management System',
    'version': '17.0.1.1.0',
    'category': 'Inventory/Purchase',
    'summary': 'Supplier master, registration, documents, performance scorecard, audits, CAPA and risk',
    'description': """
Smart Complete Garment Software — Supplier / Vendor Management System
=======================================================================
Module 10 of the Smart Complete Garment Software suite.

Owns the supplier MASTER, relationship, performance and compliance data.
Deliberately does not duplicate RFQ / Purchase Order / Delivery Tracking /
Contract Management — those transactional documents already live in
Module 9 (Purchase Management) and are simply referenced here by supplier.

Key Features
------------
* Supplier Master with classification (Strategic/Approved/Temporary/
  Blocked), registration details, and a 5-stage activation workflow
  (Registration → Purchase Review → Quality Review → Compliance Review →
  Management Approval → Active)
* Supplier Category management (Material: Fabric/Yarn/Trim/Packaging;
  Service: Washing/Printing/Embroidery; Logistics: Freight/Transport)
* Supplier Product Catalog with price, MOQ and lead time
* Supplier Document management with expiry tracking (Valid/Expiring Soon/
  Expired/Pending Verification)
* Supplier Performance Scorecard — Quality 40% + Delivery 30% + Cost 20%
  + Compliance 10% — with automatic Platinum/Gold/Silver/Restricted ranking
* Supplier Audit management (Factory/Quality/Social/Environmental) with a
  structured checklist and Planning → Execution → Findings → CAPA →
  Closure workflow
* Supplier Corrective Action (CAPA) tracking
* Supplier Risk register with blacklist management embedded on the
  supplier master
* AI Supplier Intelligence: risk prediction from delivery/quality history
  (reusing Module 9's delivery data), and supplier recommendation by
  material from the product catalog and scorecards — extends the shared
  Garment AI Engine
* Role-gated Supplier Approval Workflow with per-stage approver/date
  stamps (Purchase/Quality/Compliance Review, Management Approval)
* Supplier Price History log and a Supplier Comparison wizard (Price/
  Quality/Delivery/Capacity/Compliance/Payment Terms)
* Bangladesh Garment Supplier Standards: fabric (composition/GSM/width/
  dyeing/colour fastness/test report) and accessories (material type/size
  spec/colour matching/sample approval) tracking on the product catalog,
  plus BSCI/SEDEX/WRAP/ISO/OEKO-TEX/GOTS certification flags
* Document Expiry notification cron (chatter + activity reminder)
* Supplier Portal (/my/supplier) — dashboard, limited profile self-edit,
  document upload, and read-only RFQ/PO/Delivery views, reusing Module 9
  (Purchase) and Module 12 (Finance, for Payment Status) data
* Supplier Purchase Report and Supplier Delay Report (Module 9 data)
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_buyer_crm', 'garment_purchase'],
    'data': [
        'security/garment_supplier_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_supplier_category_data.xml',
        'data/ir_cron_data.xml',
        'views/garment_supplier_views.xml',
        'views/garment_supplier_category_views.xml',
        'views/garment_supplier_product_views.xml',
        'views/garment_supplier_price_history_views.xml',
        'views/garment_supplier_document_views.xml',
        'views/garment_supplier_rating_views.xml',
        'views/garment_supplier_audit_views.xml',
        'views/garment_supplier_capa_views.xml',
        'views/garment_supplier_risk_views.xml',
        'wizard/garment_supplier_comparison_wizard_views.xml',
        'report/garment_supplier_report.xml',
        'views/garment_supplier_dashboard_views.xml',
        'views/garment_supplier_portal_templates.xml',
        'views/garment_supplier_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
