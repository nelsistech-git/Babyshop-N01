# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 13: Finance, Accounting & Commercial Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Finance, Accounting & Commercial Management System',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Cost centers, budgets, expenses, payments, receivables, bank reconciliation, LC and export docs',
    'description': """
Smart Complete Garment Software — Finance, Accounting & Commercial Management System
========================================================================================
Module 13 of the Smart Complete Garment Software suite — starts the
Finance phase, built from the largest of three overlapping SRS documents
(Finance & Accounting Management System, Commercial & Export Management
System, and this merged Finance+Commercial doc), which already combines
both domains.

A DELIBERATE SCOPE DECISION: this module does NOT reinvent double-entry
bookkeeping, a General Ledger, P&L/Balance Sheet/Cash Flow statements,
Fixed Assets or Depreciation — Odoo Community's standard Accounting app
(the 'account' module) already provides complete, audited implementations
of all of those, and this suite already relies on it for payment terms
and incoterms (account.payment.term / account.incoterms) since Module 1.
Install and configure the standard Accounting app alongside this module
for full bookkeeping; this module adds the garment-industry layer on top
of it: cost centers by department/factory, budget planning and variance,
expense and vendor payment tracking, buyer receivables, bank transaction
reconciliation, and full Letter of Credit + export documentation
lifecycle management, none of which the standard Accounting app covers
out of the box.

Key Features
------------
* Chart of Accounts (garment-industry categories: Assets/Liabilities/
  Income/Expenses) and Cost Center management (Cutting/Sewing/Washing/
  Finishing/Quality/Maintenance/Administration)
* Budget planning (Annual/Monthly/Department/Production) with live
  actual-vs-budget variance (variance amount/%, narrative reason)
* Expense management and Vendor Payment approval, both gated by a
  configurable amount-banded Payment Approval Matrix (Finance Manager /
  Finance Director thresholds)
* Vendor Payment tracking (linked to Module 9/10 suppliers) and Buyer
  Receivable tracking (linked to Module 1 buyers) with aging
* Bank Account master and Bank Transaction ledger with a full Bank
  Reconciliation matching workflow: import/enter Bank Statement Lines,
  auto-match against ERP transactions, Reconcile, then Close
* Financial Statement snapshots (simplified P&L / position / budget
  status) and forward-looking Cash Flow Forecasting, built entirely from
  this module's own operational data — NOT a replacement for Odoo
  Accounting's audited GL/Trial Balance/Balance Sheet/P&L
* Letter of Credit (LC) Master with the full workflow (Buyer Order → LC
  Received → Verification → Bank Approval → Procurement → Production →
  Shipment → Export Documents → Payment Received), LC Document checklist,
  and amendment tracking
* Export Documentation (Invoice / Packing List / Shipping Documents)
  linked to Module 12 shipments
* AI Financial Intelligence: cash flow / receivable risk prediction,
  budget variance alerts, and LC realization risk assessment — extends
  the shared Garment AI Engine
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'account', 'garment_buyer_crm', 'garment_supplier', 'garment_logistics'],
    'data': [
        'security/garment_finance_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_account_data.xml',
        'data/garment_cost_center_data.xml',
        'data/garment_payment_approval_rule_data.xml',
        'views/garment_account_views.xml',
        'views/garment_cost_center_views.xml',
        'views/garment_budget_views.xml',
        'views/garment_expense_views.xml',
        'views/garment_payment_approval_rule_views.xml',
        'views/garment_payment_views.xml',
        'views/garment_receivable_views.xml',
        'views/garment_bank_account_views.xml',
        'views/garment_bank_statement_line_views.xml',
        'views/garment_bank_transaction_views.xml',
        'views/garment_lc_views.xml',
        'views/garment_lc_document_views.xml',
        'views/garment_export_documentation_views.xml',
        'report/garment_lc_report.xml',
        'views/garment_finance_statement_views.xml',
        'views/garment_cash_flow_forecast_views.xml',
        'views/garment_finance_dashboard_views.xml',
        'views/garment_finance_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
