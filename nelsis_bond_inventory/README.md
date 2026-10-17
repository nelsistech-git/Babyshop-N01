# nelsis_bond_inventory (Module 04) - Odoo Community 17
Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.

## Install
1. Backup the database and filestore.
2. Copy `nelsis_bond_inventory` into your addons path; restart Odoo.
3. Apps > Update Apps List > install "Nelsis Bond Inventory" (or `-i nelsis_bond_inventory`).
4. Upgrade: `-u nelsis_bond_inventory`. Rollback: restore the backup (uninstall does not remove history safely).
5. Tests: `odoo-bin -d <testdb> -i nelsis_bond_inventory --test-tags /nelsis_bond_inventory --stop-after-init`

## First configuration
* Inventory > Bonded Warehouse > Configuration > Settings (Administrator): set the LC model technical name ONLY after reading it from the real LC addon source; set variance tolerance (internal policy, not a legal limit).
* Configure document types required for bonded receipts only after review by a qualified customs professional.
* Make a location bonded / product bond-eligible via Classification Requests (evidence attachment + approver).
* Bond-eligible products must be lot/serial tracked.

## Groups
Bond Receipt Officer < Inspector/Document Verifier < Approver < Manager (maker-checker on approvals).

## Design notes / assumptions
* No own stock balance: receipts post through stock.picking/move/move.line; the report is a SQL view on stock.quant.
* Direct validation/cancel of a bond receipt's picking is blocked; stock into bonded locations is allowed only via a bond receipt or bonded-to-bonded transfer. Contexts `bond_allow_inbound` / `bond_allow_debond` are reserved for later approved modules (adjustment, return, de-bonding).
* Damaged/rejected quantities are tracked on the receipt but not stocked (no quarantine location in this module).
* LC and customs-document links are loose References (LC model name configured; `bond.warehouse.document` offered if installed). A hard Many2one to the LC model needs its real manifest/models.
* Expiry uses its own lot field (`bond_expiry_date`), not product_expiry.
* Manifest license is "Other proprietary" - confirm the licence you intend.
* Passing software validation is not legal compliance; no legal limits are hard-coded.
