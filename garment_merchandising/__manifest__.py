# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 6: Merchandising Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Merchandising Management System',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Merchandiser workspace connecting inquiry, review, quotation, negotiation and production handover',
    'description': """
Smart Complete Garment Software — Merchandising Management System
=======================================================================
Module 6 of the Smart Complete Garment Software suite — the commercial
coordination hub that turns an RFQ into a confirmed, production-ready order.

This module intentionally does NOT duplicate BOM (Module 5), Tech Pack
(Module 3) or Sample Development (Module 4) — it coordinates and reviews
them from the merchandiser's seat, and owns the commercial workflow that
sits on top: inquiry triage, internal review, quotation, negotiation,
order confirmation and production handover.

Key Features
------------
* Buyer Inquiry workspace — builds on the Buyer CRM RFQ with merchandiser
  assignment, workload-aware routing and per-inquiry style lines
* Internal Review Checklist (product/compliance/commercial) gating the
  move to costing/quotation
* Merchandising Calendar — RFQ, costing, sample, booking, production,
  inspection, shipment and LC deadlines in one timeline
* Quotation Management with a full Draft → Accepted/Rejected/Expired
  status flow and cost-sheet-aware pricing
* Negotiation Management with full round-by-round history
* Order Confirmation (merchandising-side) and a formal Production Handover
  checklist + multi-role approval chain
* Merchandising Dashboard — pipeline value, win rate, RFQ turnaround,
  merchandiser workload
* AI Merchandising Assistant: quotation price suggestion from the linked
  BOM cost sheet, negotiation counter-offer suggestion, and workload-based
  merchandiser recommendation — extends the shared Garment AI Engine
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'calendar', 'account', 'garment_buyer_crm', 'garment_style_library',
                'garment_techpack', 'garment_bom_management'],
    'data': [
        'security/garment_merchandising_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/garment_merch_inquiry_views.xml',
        'views/garment_merch_review_checklist_views.xml',
        'views/garment_merch_calendar_views.xml',
        'views/garment_merch_task_views.xml',
        'views/garment_merch_quotation_views.xml',
        'views/garment_merch_negotiation_views.xml',
        'views/garment_merch_order_confirmation_views.xml',
        'views/garment_merch_handover_views.xml',
        'report/garment_merch_quotation_report.xml',
        'views/garment_merch_dashboard_views.xml',
        'views/garment_merch_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
