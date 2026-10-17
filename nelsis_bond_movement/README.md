# nelsis_bond_movement (Odoo Community 17)

Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
Module 05 of the Nelsis Bond Warehouse suite: bonded transfers, issues, returns, adjustments.

## Install
1. Copy `nelsis_bond_movement` into your addons path; restart Odoo; update the apps list.
2. Back up the database first. Install via Apps, or: `odoo -d DB -i nelsis_bond_movement`.
3. Run tests: `odoo -d TESTDB -i nelsis_bond_movement --test-tags /nelsis_bond_movement --stop-after-init`.
4. Rollback: uninstall the module (removes only its own models/fields); restore the backup if required.

## Setup (required before use)
* Inventory > Configuration > Locations (or Bond Movements > Configuration > Bond Locations): set each internal
  location's *Bond Classification* and tick *Authorized for Bond Movements*. Requires the Controller group.
* Assign users: Preparer, Approver, Bond Classification Controller (Settings > Users > Bond Warehouse Movements).
* System parameter `nelsis_bond_movement.require_customs_reference` (default True): bonded documents need a
  license, LC or Bill of Entry reference.

## Design
* Stock is posted only through standard `stock.move` / `stock.move.line`; `stock.quant` is never written. No balances are stored.
* Workflow: Draft > Submitted > Approved > Validated (> Reversed). Preparer cannot approve own document.
* Duplicate posting: row lock, state check, unique `move_id`. Negative stock: availability check (reserved stock excluded).
* Validated documents are read-only and undeletable; reversal needs a reason and creates a counter stock move.
* `stock.move.bond_movement_id` links every move to its bond document for the bond stock ledger.

## Assumptions / integration points (nothing invented)
* The LC module's technical name/fields were not provided, so `license_ref`, `lc_ref`, `boe_ref` are Char fields.
  After the shared contract is approved, replace them with Many2one fields to the LC / `bond.warehouse.*` models.
* `_compliance_checks()` is the extension hook for the entitlement / storage-period / document rule engine.
  No legal limits, entitlements or storage periods are hard-coded. Regulatory rules must be verified
  from NBR/Customs sources and reviewed by a qualified Bangladesh customs professional.
* `'license': 'LGPL-3'` is a placeholder; Nelsis Tech should confirm the intended license.
* Tests were written but have not been executed against a live Odoo 17 instance.
