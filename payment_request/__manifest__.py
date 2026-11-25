# -*- coding: utf-8 -*-
{
    'name': 'BBBL Payment Request (RTGS / BEFTN)',
    'version': '17.0.1.6.0',
    'category': 'Accounting/Finance',
    'summary': 'Vendor Payment Requisition with approval chain, auto WHT/WHVAT, '
               'and bank-ready RTGS / BEFTN forwarding letters.',
    'description': """
BBBL Payment Request (RTGS / BEFTN)
====================================
Developer : Nelsis Tech
Company   : Bit Body Bangladesh Limited

Overview
--------
Implements the Payment Requisition process exactly as used today (see the
uploaded Payment_Request_Form.xlsx / RTGS_Application_Form.pdf /
BEFTN_BBBL_....pdf):

1. When a supplier gives a bill/invoice, create a Payment Request line
   (optionally pulled straight from a posted Vendor Bill) - Bill Amount,
   Deduction/Adv. Adjustment, WHT (TDS) and WHVAT (VDS) are captured per
   line, Net Payment is computed automatically. WHT/WHVAT default from the
   vendor's "VAT %" / "TDS %" (custom_contacts) when set to "Including VAT
   & TDS", but always remain manually editable since Bangladesh withholding
   rates vary by service/section.
2. Approval chain: Draft -> Line Manager Approval -> Approved (by Head of
   Finance & Accounts, or by Executive/CEO/MD/Director instead when the
   amount exceeds the Executive Approval Threshold) - see the 2026-09-13
   note below for the full detail.
3. Once Approved, "Forward to Bank" generates:
   - One **RTGS Application** (Commercial Bank of Ceylon PLC format) per
     line with Payment Mode = RTGS.
   - One consolidated **BEFTN Request Letter** (BBBL letterhead format,
     multi-beneficiary table) covering every line with Payment Mode = BEFTN
     in the request, under one running Reference Number
     (e.g. BBBL/CBC Plc2026/342).
   Both report bodies are laid out to match the supplied PDF formats
   exactly, with every value coming from Odoo - nothing is retyped.
4. "Create Vendor Payment" posts the real accounting entry for a line linked
   to a Vendor Bill: Dr Accounts Payable (full Bill Amount, reconciled
   against the bill) / Cr Bank (Net Payment) / Cr TDS Payable (WHT) /
   Cr VDS Payable (WHVAT) - configure the three accounts + journal in
   Settings > Payment Request first.
5. Commercial module hand-off: a **TT (Telegraphic Transfer)** document can
   be "Forwarded to Accounting", auto-creating a linked Payment Request line
   pre-filled from the TT/Purchase Order, so TT-financed purchases flow
   through the same approval + accounting pipeline as LC financing already
   does through EDF Loan Management.
6. "Print Mushak 6.6 VDS" generates the NBR-format **Mushak 6.6 VDS
   (VAT Deducted at Source) Certificate** in Bengali, one certificate per
   Payment Request covering every line with WHVAT (Tk.) > 0, under a
   running Certificate No. assigned the first time it's printed. Company
   BIN/address and the vendor's BIN (Contact > Tax ID) are pulled in
   automatically; a bundled Unicode Bengali font (Noto Sans Bengali, SIL
   OFL) is embedded directly in the PDF so no server font install is
   needed.

2026-09-13: approval chain changed from the old bespoke Prepared -> Checked
-> Reviewed -> Approved chain (its own Checker/Reviewer/Approver groups) to
Draft -> Line Manager Approval -> Approved, matching the client's "P2P
Master Workflow" for the Payment stage. Reuses the SAME Line Manager /
Head of Finance & Accounts groups as Vendor Onboarding
(product_vendor_details) and the SAME Executive (CEO/MD/Director) group
and Executive Approval Threshold setting (default Tk 250,000, Settings >
Purchase - Vendor PI) as Purchase Orders (purchase_vendor_pi) - one
person's role assignment now covers all three chains. Below the
threshold, Head of Finance & Accounts gives the final approval; at or
above it, Executive approval is required INSTEAD of Head of Finance (an
either/or branch for Payment, at Rahat's explicit confirmation - unlike
the Purchase Order chain, where Executive approval is an extra step on
top of Head of Finance). The "Reviewed" step was dropped entirely (not
part of the new diagram); nothing on the printed RTGS/BEFTN bank letters
depended on it - those only print the company's fixed signatory name, not
who checked/reviewed/approved internally.

2026-10-10: "Debit Account (Our Bank)" and "Debit Account Branch" moved from the
request header to each LINE (dropdowns; accounts/branches can be added from the
dropdown). Vendor BIN added per line (auto-filled from the vendor, editable) and
printed on Mushak 6.6 and RTGS. BEFTN letters are now grouped per debit account.

2026-10-22: Mushak 6.6 rebuilt to match the NBR sample (BD Govt. emblem, 1st/2nd copy, inline treasury
challan, supplier challan No/Date from the Vendor Bill), one certificate per supplier on separate pages,
margins L 1.25in / R 1in. RTGS application now bound to the Payment Request (Print menu). Requisition
PDF no longer shrinks/blanks on long Purpose text. Vendor Bill gets VAT Challan No / Date.
    """,
    'author': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'account', 'contacts', 'hr', 'custom_contacts', 'commercial',
                'product_vendor_details', 'purchase_vendor_pi'],
    'data': [
        'security/payment_request_security.xml',
        'security/ir.model.access.csv',
        'data/payment_request_sequence.xml',
        'data/payment_request_branch_data.xml',
        'views/payment_request_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_bank_views.xml',
        'views/commercial_tt_views.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
        'reports/requisition_report_template.xml',
        'reports/report_actions.xml',
        'reports/rtgs_report_template.xml',
        'reports/beftn_report_template.xml',
        'reports/mushak66_assets.xml',
        'reports/mushak66_report_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}