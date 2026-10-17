# Nelsis Bond Purchase (Odoo 17 Community)

Connects standard **Purchase** with the Nelsis Bond Warehouse suite. Depends on `purchase_stock`,
`nelsis_bond_warehouse` (LC, commercial, license, inventory, movement, reconciliation) and
`nelsis_bond_dashboard`.

## What it does
| Area | Behaviour |
|---|---|
| Purchase type | Local / Import - Bonded / Import - Non-Bonded on every purchase order. Local orders behave exactly as standard Odoo. |
| Links | LC, commercial file and (bonded) entitlement on the order; smart buttons on the order, LC, commercial file, consignment and bond receipt. |
| Confirmation checks | Bonded: LC required (setting), products bond-eligible with HS code and lot tracking, one line per product/unit, entitlement availability. Any LC: supplier and currency must match, LC not on hold/closed, orders must fit LC amount + tolerance. Each of LC limit / entitlement is Off / Warn / Block (Settings > Purchase > Bonded Purchase). |
| Receiving | Bonded orders create **no standard receipt**. Create a consignment from the order, add the Bill of Entry, open it and receive through the bond receipt workflow. |
| Sync on receipt | A validated bond receipt: sets `purchase_line_id` and the order price on the stock move (received quantity and valuation follow the order); fills BoE / LC / license / entitlement references on the transfer before validation (so lots inherit them); links the transfer to the LC (and shipment) and the commercial file; posts a note on the order. |
| Order status | `receipt_status` of a bonded order follows received quantities (pending / partial / full). |
| Retro-link | Set the purchase order on an existing consignment and press **Sync Bond Data** on the order: consignment lines, already-validated receipt moves, LC and commercial-file links are aligned. Safe to repeat. |
| Dashboard | Two cards (awaiting receipt, confirmed bonded orders without LC) and one inactive alert rule. |

## Roles
`Bond Warehouse Suite / Purchase Officer` and `Purchase Manager` (imply Purchase user / manager plus LC user, commercial user, bond inventory user).
Suite Operator / Manager also see the bond tab of the order.

## Known limits (stated, not hidden)
* Entitlement check counts **validated utilization only**; other open orders are not reserved against it.
* The LC check compares order totals with the LC amount in the same currency. No conversion is made.
* Bonded orders need one order line per product and unit (needed to match receipts to lines).
* Moves linked to an order afterwards (retro-link) keep their old unit price.
* The checks are software controls, not an official customs approval.
