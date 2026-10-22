# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 9: Purchase Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Purchase Management System',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Purchase requisition, supplier RFQ/quotation, purchase order, contracts and delivery tracking',
    'description': """
Smart Complete Garment Software — Purchase Management System
=======================================================================
Module 9 of the Smart Complete Garment Software suite — the first module
of the Planning phase. Turns BOM fabric/trim/packaging requirements into
real purchase requisitions, supplier RFQs, quotations and purchase orders.

Note on naming: the source SRS proposed "garment.rfq" for the Supplier
RFQ model, but that technical name is already used by the Buyer CRM
module (Module 1) for buyer-side RFQ intake — a genuinely different
business object (buyer asking us for a quote, vs. us asking a supplier
for one). To avoid a real model collision this module uses
garment.purchase.rfq instead.

Key Features
------------
* Purchase Requisition (PR) sourced from BOM, Production, Planning,
  Manual or Maintenance requests, with department approval workflow
* Material Requirement Planning: Purchase Required = Requirement −
  Available − Incoming, with automatic shortage alerts and 4-level
  priority (Critical/High/Medium/Low)
* Supplier RFQ management with automatic creation from an approved PR
* Supplier Quotation intake and side-by-side comparison
  (price/quality/delivery/payment terms)
* Purchase Order creation with amount-based approval tiers
* Fabric-specific and Accessory-specific purchase line details
  (composition/GSM/width/color/Pantone for fabric; size/color/qty for
  accessories) embedded directly on the requisition and order lines
* Purchase Contract / Blanket Purchase Agreement management
* Delivery Tracking (ordered/delivered/pending quantity, delay days,
  return quantity/reason)
* AI Procurement Intelligence: material demand forecasting, purchase
  price-trend prediction, supplier delivery-delay risk prediction,
  automatic purchase planning, and supplier recommendation from
  quotation comparison — extends the shared Garment AI Engine
* Fabric Color Management (lab dip / shade band / buyer-supplier color
  code approval) and Fabric Booking Management
* Local Purchase (VAT, delivery location, challan) and Import Purchase
  (PI/LC/bank/shipment/ETA/port/freight/C&F, landed cost) data on the PO
* Purchase Exception Management (price increase, budget exceeded) and a
  lightweight department Purchase Budget Control check
* Purchase Invoice Matching: 3-way match of PO + Goods Receipt +
  Supplier Invoice (account.move)
* Purchase Quality Integration checklist on delivery (GSM/shade/
  shrinkage/color-fastness for fabric; size/color/quantity for
  accessories) and Delivery Performance (on-time %) reporting
* Supplier RFQ/PO portal integration (portal.mixin + own-record rules)
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'account', 'garment_buyer_crm', 'garment_style_library',
                'garment_bom_management', 'garment_costing', 'garment_hr', 'garment_order_management'],
    'data': [
        'security/garment_purchase_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/garment_purchase_requisition_views.xml',
        'views/garment_purchase_rfq_views.xml',
        'views/garment_supplier_quotation_views.xml',
        'views/garment_purchase_order_views.xml',
        'views/garment_purchase_contract_views.xml',
        'views/garment_purchase_delivery_views.xml',
        'views/garment_purchase_approval_views.xml',
        'views/garment_purchase_forecast_views.xml',
        'views/garment_purchase_fabric_booking_views.xml',
        'report/garment_purchase_order_report.xml',
        'views/garment_purchase_dashboard_views.xml',
        'views/garment_purchase_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
