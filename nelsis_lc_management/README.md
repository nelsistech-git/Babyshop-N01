# Nelsis LC Management (Odoo Community 17)

Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.

Technical name: `nelsis_lc_management` · Depends on: `base`, `mail`, `stock` (all Community).

## Status of this delivery
Written against Odoo 17 conventions and statically checked (Python syntax, XML well-formedness,
XML-ID and field cross-references). It has **not** been installed or run on an Odoo 17 server,
and the test suite in `tests/` has **not** been executed. Run the steps below on a staging
database first.

## What it does
* LC lifecycle: Draft → Submitted for Review → Approved → Opened → Shipment/Documentation →
  Partially Utilized/Cleared → Fully Cleared → Closed, plus Hold, Cancel, Return-to-Draft.
* Amendments (amount, expiry, latest shipment date) with approval; before/after values are
  snapshotted at approval and never overwritten. Pending amendments do not change the LC.
* Shipments, Bills of Entry, configurable document checklist, append-only audit log.
* Receipt traceability: `stock.picking` gets `lc_id` / `lc_shipment_id` link fields only.
  The module never creates stock moves, move lines or quants and never validates a picking.
* Daily reminders (expiry, latest shipment date, pending documents) as activities; each
  reminder is sent once per LC/document (flag reset when an approved amendment moves a date).
* Kanban dashboard, graph/pivot utilization reports, printable LC summary + checklist (PDF).

## Amount definitions (single LC currency, no conversion)
* Current approved amount = original + sum of **approved** amendment changes
* Utilized = invoice value of shipments in Shipped … Received (Planned and Cancelled excluded)
* Planned = invoice value of Planned shipments
* Balance = Current − Utilized; over-utilization is blocked beyond current × (1 + tolerance %)
* LC value is never treated as bonded stock or statutory entitlement.

## Roles (Settings → Users)
| Role | Rights |
|---|---|
| LC User | create/edit own Draft LCs, submit; sees own LCs only |
| LC Officer | all LCs; documents, shipments, BoE, amendments, hold/cancel, link receipts |
| LC Manager | approve LCs/amendments, close, reset, configuration |
| Bond Warehouse Officer | read LCs past review; link receipts (implies Inventory User) |
| Compliance / Audit | read-only on everything incl. audit log |

Every workflow method re-checks the caller's group on the server; privileged writes run
through `sudo()` and direct `state` writes from the client are rejected.
To link receipts an Officer also needs Inventory access (the link button lives on stock data).

## Compliance (not pre-filled)
No statutory limits, duty rates, entitlement formulas or mandatory document lists are
hard-coded. Seeded document types are all *not required by default*. Use
LC Management → Configuration → **Compliance Mapping** to record rule/SRO references from
https://bangladeshcustoms.gov.bd/relevant/bonded_warehouse and
https://nbr.gov.bd/regulations/sros/customs-sros/eng, then have each reviewed by your
authorized customs professional. Software validation is not legal compliance.

## Integration contract for nelsis_bond_warehouse
* Model `nelsis.lc` is authoritative for LC data; fields `lc_number`, `state`, `partner_id`,
  `current_amount`, `bond_license_ref` (free text).
* `stock.picking.lc_id` / `lc_shipment_id` link receipts; bond addon should depend on
  `nelsis_lc_management` and reuse these fields rather than adding its own.
* Groups: `nelsis_lc_management.group_lc_{user,officer,manager,bond_officer,auditor}`.
* Sequences: `nelsis.lc`, `nelsis.lc.shipment`.

## Install
1. **Back up** the database and filestore (`pg_dump -Fc db > db.dump`; copy filestore).
2. Copy `nelsis_lc_management` into an addons path, restart Odoo, Apps → Update Apps List.
3. Install on staging: `odoo -d staging -i nelsis_lc_management --stop-after-init`
4. Run tests: `odoo -d test_db -i nelsis_lc_management --test-tags /nelsis_lc_management --stop-after-init`
5. Assign roles; review LC Management → Configuration → Settings.

## Upgrade / rollback
* Upgrade: `odoo -d db -u nelsis_lc_management --stop-after-init` (back up first).
* Rollback: restore the dump and filestore taken in step 1. Uninstalling drops LC tables and
  the `lc_id` / `lc_shipment_id` columns on `stock.picking` (link data is lost, stock is not).

## Known assumptions / limits
* Fresh module: no migration from an earlier custom LC addon is provided. If you have one,
  provide its source so a migration script can be written against its real model names.
* Multi-currency conversion is not performed; reports pivot per currency.
* The `icon=` attribute on header buttons assumes Odoo 17 ViewButton support.
