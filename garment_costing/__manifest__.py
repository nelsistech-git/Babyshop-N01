# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 7: Garment Costing Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Costing Management System',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'FOB costing, manufacturing cost, profit margin, revision history and buyer price negotiation',
    'description': """
Smart Complete Garment Software — Garment Costing Management System
=======================================================================
Module 7 of the Smart Complete Garment Software suite.

Sits directly on top of the BOM (Module 5): material cost is READ from the
linked BOM's fabric/trim/packaging cost roll-up rather than recalculated,
so there is exactly one place a fabric or trim price lives. This module
adds everything BOM does not own — manufacturing cost (CM), overhead,
profit margin, FOB price, multi-level approval, cost locking, version
history, supplier price comparison, currency/exchange rate management,
and estimated-vs-actual variance analysis.

Key Features
------------
* Costing Master (Preliminary / Final / Revised) linked to Style, Buyer,
  Sample and BOM, with material cost pulled live from the BOM cost roll-up
* Manufacturing Cost (CM) — direct labor, machine cost, factory overhead,
  and an SMV × Cost-per-Minute calculation mode
* Per-operation cost breakdown (cutting/sewing/washing/finishing/packing)
* Additional cost management (testing/inspection/sample/development/
  freight/commission/bank charge)
* FOB Price = Material + CM + Overhead + Profit, with percentage or fixed
  profit margin
* 4-level Cost Approval Workflow (Merchandising → Costing Team → Finance
  → Management) with cost locking after approval
* Costing Version/Revision history with structured change reasons
* Supplier Price History and comparison (price/quality/delivery/compliance)
* Currency & Exchange Rate management, with automatic FOB conversion to the
  company currency using the latest applicable rate
* Estimated vs Actual Cost Variance analysis (material/labor/overhead)
* Buyer Price Negotiation history (submitted/target/negotiated/final price)
* Payment Terms (LC/TT/DP/DA/Advance) and Incoterms (FOB/CIF/CFR/EXW/FCA)
  with automatic CIF/CFR price adjustment
* AI Costing Assistant: cost prediction from historical styles, cost
  optimization suggestions, cost saving analysis, AI margin protection
  warning, an AI Cost Simulation ("what if fabric price rises 10%?") wizard,
  and buyer price/negotiation range prediction — extends the shared Garment
  AI Engine
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_buyer_crm', 'garment_style_library', 'garment_techpack',
                'garment_bom_management', 'garment_merchandising'],
    'data': [
        'security/garment_costing_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_exchange_rate_data.xml',
        'views/garment_costing_views.xml',
        'views/garment_cm_cost_views.xml',
        'views/garment_cost_revision_views.xml',
        'views/garment_price_history_views.xml',
        'views/garment_cost_variance_views.xml',
        'views/garment_exchange_rate_views.xml',
        'views/garment_costing_approval_views.xml',
        'views/garment_cost_negotiation_views.xml',
        'views/garment_cost_payment_term_views.xml',
        'wizard/garment_cost_simulation_wizard_views.xml',
        'report/garment_costing_report.xml',
        'views/garment_costing_dashboard_views.xml',
        'views/garment_costing_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
