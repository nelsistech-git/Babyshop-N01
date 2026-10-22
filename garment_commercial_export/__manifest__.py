# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 18: Commercial & Export Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Commercial & Export Management System',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Back-to-Back LC, EXP/IP/UD, bonded warehouse, customs, HS code, buyer document '
               'requirements and export cash incentive tracking on top of Finance\'s LC and export documents',
    'description': """
Smart Complete Garment Software — Commercial & Export Management System
=============================================================================
Module 18 of the Smart Complete Garment Software suite — the customs,
bonded-warehouse and export-incentive layer of Bangladesh garment export
compliance, built on top of Module 13's (garment_finance) LC and export
documentation foundation and Module 12's (garment_logistics) shipments.

A DELIBERATE SCOPE DECISION: garment_finance already owns ``garment.lc``
(the full LC workflow, buyer/bank/amount/expiry/status) and
``garment.export.documentation`` (Export Invoice / Packing List / Shipping
Instructions / Certificate of Origin, linked to a shipment). This module
does NOT re-create either — it EXTENDS both (Back-to-Back LC typing,
structured amendments, invoice/carton line detail, extra document types)
and adds the deeper customs/bond/incentive layer that garment_finance's
export documentation summary only touches lightly: Bond License and Bond
Register, Import Permission (IP) and Utilization Declaration (UD/UP), HS
Code master, Customs Documentation (Bill of Entry/Export, Declaration),
EXP Form workflow, buyer-specific document requirement checklists, and
Export Cash Incentive claim tracking. Proforma Invoice is likewise not
duplicated — see IMPLEMENTATION_NOTES.md for the full model-reuse map.

Key Features
------------
* Back-to-Back LC support on ``garment.lc`` (lc_type, Master LC self-
  reference, BTB supplier, separate issuing/advising/buyer bank, live
  utilized/balance amount) and structured LC Amendment tracking
  (``garment.lc.amendment``: old value / new value / reason / approval)
* Export Documentation (``garment.export.documentation``) extended with
  more document types (EXP/GSP/Inspection/Insurance/Beneficiary
  Certificate), an HS Code link, buyer-portal sharing flag, invoice
  product-line detail and carton-level packing list detail
* EXP Form (Export Registration Form) with the Commercial Officer -> Bank
  Verification -> EXP Approval -> Shipment workflow
* Import Permission (IP) and Utilization Declaration (UD) tracking
  imported-material consumption against production and export
* Bond Management System: Bond License master and Bond Register
  (material-wise imported / used / balance quantity against export
  reference), matching the SRS's bonded-warehouse Utilization Declaration
  process
* Customs Documentation (Bill of Entry, Bill of Export, Customs
  Declaration) and HS Code master with duty rate and country rules
* Buyer-specific commercial document requirement checklists
* Export Cash Incentive claim tracking (claim/approval/received amount)
* Export Payment Realization / Bangladesh Bank reporting fields added to
  garment_finance's ``garment.receivable``
* Shipment Commercial Readiness check added to garment_logistics'
  ``garment.shipment`` (EXP/customs/incentive linkage + a rule-based
  readiness note)
* AI Commercial Intelligence: buyer commercial risk (payment behaviour,
  bank/country risk) and rule-based commercial document verification
  (LC/invoice mismatch, missing documents) — extends the shared Garment
  AI Engine
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'garment_finance', 'garment_logistics'],
    'data': [
        'security/garment_commercial_export_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/garment_lc_export_views.xml',
        'views/garment_lc_amendment_views.xml',
        'views/garment_export_documentation_export_views.xml',
        'views/garment_exp_form_views.xml',
        'views/garment_import_permission_views.xml',
        'views/garment_utilization_declaration_views.xml',
        'views/garment_bond_license_views.xml',
        'views/garment_bond_register_views.xml',
        'views/garment_hs_code_views.xml',
        'views/garment_customs_document_views.xml',
        'views/garment_export_incentive_views.xml',
        'views/garment_commercial_doc_requirement_views.xml',
        'views/garment_shipment_export_views.xml',
        'views/garment_buyer_export_views.xml',
        'report/garment_exp_form_report.xml',
        'views/garment_commercial_export_dashboard_views.xml',
        'views/garment_commercial_export_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
