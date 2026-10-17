# Nelsis Bond Reconciliation (Module 06) - Odoo Community 17

Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.

## What it does
* **Bond Register** (`bond.warehouse.register`) - read-only SQL view over validated Odoo stock movements, grouped per license / LC / BoE / product / lot / location.
* **Stock Ledger** (`bond.warehouse.ledger`) - one row per internal location touched by a validated move line, with in/out quantities, running balance, LC/BoE, user and approval details.
* **Reconciliation** (`bond.warehouse.reconciliation`) - Draft > In Progress > Discrepancy Found > Review > Approval > Reconciled > Closed; reopen only by a Manager with a recorded reason.
* **12 reports** - PDF, CSV, XLSX (only if `xlsxwriter` is installed) and on-screen list/pivot/graph.

No second inventory balance is stored. Stock quantities always come from standard `stock.move.line` / `stock.quant`.

## Install
1. Copy `nelsis_bond_reconciliation` into your addons path.
2. Back up the database first.
3. Apps > Update Apps List > install **Nelsis Bond Reconciliation**, or run `odoo-bin -d <db> -i nelsis_bond_reconciliation --stop-after-init`.
4. Optional: `pip install xlsxwriter` for XLSX export.
5. Add users to *Bond Reconciliation / User* or *Manager*.

## First-time setup
1. Inventory > Configuration > Locations: set **Bond Classification** (Bonded / Non-Bonded) on top-level locations. Children inherit.
2. Transfers: fill Bond tab (License, LC, Bill of Entry, Entitlement). On validation, references are copied to lots that have none.
3. Product: set **HS Code (Bond)**.
4. Inventory adjustments: a Manager approves them (Moves History or Ledger list > Action > *Approve Bond Adjustment*). Unapproved adjustments are never counted in a reconciliation.

## Calculation
Closing = Opening + Receipts + Returns In + Transfers In - Issues - Returns Out - Transfers Out + Approved Adjustments.
* Only `done` move lines. Draft / cancelled / waiting are never counted.
* Movements between two locations inside the chosen scope are ignored (net zero). *Transfers In/Out* are movements crossing the scope boundary from/to other internal locations and are 0 for a closed scope. This is the one deliberate extension of the formula in the brief.
* Movement classification (by the other location's type): supplier -> Receipt in / Return Out out; customer or production -> Return In in / Issue out; inventory-loss -> Adjustment; returned moves (`origin_returned_move_id`) -> Return In/Out; internal/transit -> Transfer.
* All quantities are converted to the product's UoM.
* Odoo stock comparison = current `stock.quant` quantity minus validated movements dated after the period end. It is switched off when LC/BoE/license/entitlement filters are used (quants are not split by those references).

## Security
* `group_bond_recon_user`: view register/ledger, prepare reconciliations, print reports, submit transfers for bond verification.
* `group_bond_recon_manager`: verify/reject transfers, approve adjustments, approve/close/reopen reconciliations. Approver cannot be the preparer (set system parameter `nelsis_bond_reconciliation.allow_self_approval` = `1` to allow).
* Multi-company record rules on all new models.

## Assumptions to confirm against the approved contract
* The approved shared contract and the LC module source were not provided, so **no LC module is referenced**; LC / BoE / license references are stored as text on transfers and lots. Link them to the LC addon and to `bond.warehouse.license` once their exact technical names are known.
* This module defines `bond.warehouse.register` and `bond.warehouse.reconciliation`. If Module 01 already defines these names, rename here or switch to `_inherit`.
* Security group XML IDs are this module's own; map them to the contract's IDs if they differ.
* Licence validity is checked only if a model `bond.warehouse.license` exists with a `name` field and a date field named one of expiry_date / date_expiry / valid_until / valid_to / date_end / date_to. Otherwise the exception report says it was not checked.
* No legal limits, entitlement quantities, storage periods or document requirements are built in. "Required documents" in report 9 are user options.
* The regulatory source matrix (NBR SROs, Bangladesh Customs) was NOT researched in this deliverable.

## Statutory safety
Every report carries a notice: internal management report, not an official statutory customs form, not verified for submission. Have formats and calculations reviewed by a qualified Bangladesh customs professional.

## Testing status
`tests/test_bond_reconciliation.py` has 17 tests (opening/closing, transfers, UoM, scope, discrepancies, adjustments, workflow, register vs Odoo stock, all 12 reports). They were **not executed** here (no Odoo/PostgreSQL environment). Run:
`odoo-bin -d <testdb> -i nelsis_bond_reconciliation --test-tags nelsis_bond --stop-after-init`

## Upgrade / rollback
Upgrade: back up, replace folder, `-u nelsis_bond_reconciliation`. Views are re-created automatically. Rollback: restore the backup; uninstalling removes the views, reconciliations and added columns (not stock data).
