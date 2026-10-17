# Nelsis Bond Demo Data (Odoo 17 Community)

Demo-data module for the **Nelsis Bond Warehouse Suite**. All names, numbers, licenses, LCs, Bills of
Entry and documents are **fictitious (DEMO-...)**. No statutory rate, limit or legal reference is
loaded; compliance parameters are created with `is_statutory = False`.

## Install
1. Install the suite first (`nelsis_bond_warehouse`, `nelsis_bond_dashboard` and their dependencies).
2. Put `nelsis_bond_demo` in your addons path, update the apps list, install **Nelsis Bond Demo Data**.
3. Install on a **test / demo database only**.

The data is created in `post_init_hook` by calling the real workflow methods as 13 persona users
(maker, checker, approver are always different people), so every ACL and segregation-of-duties
rule of the suite is exercised.

## Demo users (password for all: `Demo@1234`)
demo_compliance_officer, demo_compliance_reviewer, demo_compliance_approver, demo_license_officer,
demo_license_manager, demo_lc_officer, demo_lc_manager, demo_store, demo_inspector, demo_approver,
demo_controller, demo_manager, demo_auditor.
**Change or delete these users before the database is reachable by anyone else.**

## Load log and re-run
Every step runs in its own savepoint. A failing step never blocks installation.
Open **Bond Demo Data > Load Log** (administrators) to see done / failed / skipped steps and
use **Re-run loader** to retry only the steps that are not loaded yet.

## What is loaded
Users, partners, products (lot tracked), bonded locations, classification requests, compliance rules
(all stages, exceptions, evaluations), licenses with securities / renewals, entitlements with
amendments and utilization, LCs in every state with shipments / BoE / amendments, consignments and
receipts in every stage, commercial files, bond transfers / issues / adjustments / non-bonded
issue and return, bond verification, reconciliations in every status, dashboard alerts.

## Known limits (findings, not bugs of this module)
The suite's stock guard blocks bonded returns and positive bonded adjustments (the
`bond_allow_inbound` / `bond_allow_debond` contexts are never set by any module), so the demo
contains only negative bonded adjustments and returns only for non-bonded stock.

Statically validated only (compile, XML parse, field-name cross-check); not run against a live Odoo.

## Purchase data (added)
Unit `u15_purchase` (needs `nelsis_bond_purchase`; users `demo_purchase_officer`, `demo_purchase_manager`):
* P1 bonded import on LC DEMO-LC-0009: consignment created from the order, BoE DEMO-BOE-0010, one receipt validated
  (order 40% received), one waiting for approval, commercial file created from the order, entitlement warning on the tan line.
* P2 bonded import on the approved LC DEMO-LC-0006, no consignment yet. P3 local order with a standard receipt.
* P4 draft RFQ, P5 cancelled. P6 / P7 are linked afterwards to the existing consignments B and C and synchronised
  (received quantities appear on the orders).
