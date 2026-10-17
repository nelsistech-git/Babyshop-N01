# nelsis_bond_license (Module 02) - Odoo Community 17

Copyright (c) Nelsis Tech. All rights reserved. Developer / Product Owner: Nur Uddin Ahammed.
Manifest license value is `Other proprietary`; confirm the final licence terms before distribution.

## Scope
Bond licenses (+ renewals, suspension, cancellation), general bond / security instruments (+ renewal, release),
entitlements (+ amendments, utilization), audit trail, expiry cron and reminders, groups, record rules, tests.
Not included: LC model, inventory ledger, customs documents, receipts/issues (other modules).

## Dependencies
`base`, `mail`, `product`, `stock`. NO dependency on the LC addon or Module 01 (neither was supplied).
Integration points when they exist: (a) shared compliance-rule interface from Module 01 - this module
stores rule reference/verification fields itself (`bond.warehouse.rule.mixin`) and exposes
`license._is_valid_on(date)`; (b) LC link - add a Many2one to the real LC model once its technical name is known.
Menu root `menu_bond_warehouse_root` and groups `nelsis_bond_license.group_bond_license_{user,officer,manager}`
must be reconciled with the approved shared contract if Module 01 defines its own.

## Models
bond.warehouse.license, .license.renewal, bond.warehouse.security, bond.warehouse.entitlement,
.entitlement.amendment, .entitlement.utilization, bond.warehouse.history (audit), bond.license.type,
bond.factory.category (configurable masters), bond.warehouse.status.wizard.
Sequences: bond.warehouse.license / .license.renewal / .security / .entitlement / .entitlement.amendment / .entitlement.utilization.

## Key rules implemented (no legal values hard-coded)
* Activation requires a verified rule basis (company flag `Require Verified Regulatory Basis`, default on).
* Entitlement balances are stored computed fields (`inverse` blocks direct edits). Used = sum of VALIDATED utilization lines,
  each linked to exactly one `done` stock.move (partial unique index + constraint). Amount frozen at validation.
* Over-utilization blocked unless a manager records an exception authority reference + legal basis.
* Original amount/dates locked after activation; changes only through approved amendments (previous/new totals recorded).
* License expiry changes only via approved renewal. Validated records cannot be deleted; history rows are immutable.
* Reminders: company field `Bond Reminder Days` (default 60,30,15,7), daily cron schedules one activity per threshold.

## Install
1. Backup DB and filestore. 2. Copy folder into an addons path. 3. Update Apps list, install `Nelsis Bond Warehouse - License & Entitlement`
   (`odoo -d DB -i nelsis_bond_license --stop-after-init`). 4. Assign groups. 5. Create License Types and Factory Categories.
Officers need Inventory user rights to select stock moves. Reminder/verification settings: Settings > Companies > Bond Warehouse tab (needs admin).
Upgrade: `-u nelsis_bond_license`. Rollback: restore backup (uninstalling deletes data).
Tests: `odoo -d TESTDB -i nelsis_bond_license --test-tags /nelsis_bond_license --stop-after-init`.

## Assumptions to review
* stock.move `quantity` (done qty) and `price_unit` (company currency, per product UoM) used for utilization amounts.
* License valid-on-date = state active/expired and effective <= date <= expiry; suspended/cancelled never valid.
* Authorized location check: source OR destination of the move must be inside the license locations.
* Regulatory research (NBR SROs, Customs bonded warehouse page) has NOT been performed here; record each rule with source and reviewer.
