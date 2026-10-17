# Nelsis Commercial Management (nelsis_commercial) - Odoo Community 17
Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.

## Install
1. Copy `nelsis_commercial` into your addons path, restart Odoo, Update Apps List.
2. Install "Nelsis Commercial Management" (depends only on base, mail, stock).
3. Commercial > Configuration > Settings: choose your existing LC model in "LC Model".
   (Never guessed: the LC link is a Reference field to whatever model you select. No LC data is copied.)
4. Commercial > Configuration > Compliance Matrix: enter your own reviewed rules (source, effective date).
   Only active "Required" rules block progress. No statutory rule is hard-coded.
5. Assign users to the Commercial groups (User / Officer / Manager / read-only LC, Bond Warehouse, Audit).

## Key behaviour
- Stock is never written. Receipts are linked (stock.picking); comparison reads validated stock moves only.
- Verification, clearance, completion and discrepancy approval are enforced server-side (write + constraints).
- Documents are versioned; verified/superseded records are locked; deletion of audit records is blocked.
- Attachments: type/size policy, checksum duplicate check, bound to the document record for access control.
- Different unit categories are never converted: flagged "Unit Review Needed".

## Tests
`odoo -d <db> -i nelsis_commercial --test-tags /nelsis_commercial --stop-after-init`
(Written but NOT yet executed in a real Odoo 17 instance.)

## Known limits / to confirm
- Required-document check is per commercial file (not per shipment).
- Returns/backorders on receipts are not netted in the quantity comparison.
- Bond Warehouse addon links (nelsis_bond_warehouse) are not coded: its technical contract was not provided.
- Legal rules need review by a qualified Bangladesh customs professional.
