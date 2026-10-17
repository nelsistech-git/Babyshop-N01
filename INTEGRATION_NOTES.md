# Nelsis Bond Warehouse Suite - integration notes

Add the folder containing these modules to the Odoo 17 `addons_path`, update the apps
list and install **`nelsis_bond_warehouse`** (Suite Core). It pulls in every other
module in the right order. Install `nelsis_bond_dashboard` afterwards.

Install order: compliance -> license -> lc_management -> commercial -> inventory ->
movement -> reconciliation -> **bond_warehouse (core)** -> dashboard.

## What was wrong in the separate zips
1. `nelsis_bond_warehouse` (old all-in-one) defined 7 models that other modules also
   define (`bond.warehouse.license / security / entitlement / movement / register /
   reconciliation / reconciliation.line`). Installing both would clash.
2. Three modules each kept their own bonded/non-bonded field on `stock.location`
   (`bond_status`, `bond_classification`, `bond_scope`) with no link between them.
3. Dashboard KPIs / alert rules used guessed fields (`entitled_qty`, `utilized_qty`,
   `storage_deadline`, register `state`, document states `pending/missing`).
4. Three separate role families with no single way to assign them.

## What was changed
* **nelsis_bond_warehouse** is now a thin core (v17.0.2.0.0). The duplicate models,
  their views, security and cron were removed; the dedicated modules own them.
  It adds: suite roles, classification sync, LC reference sync, LC model configuration.
* **One bond classification**: Bond Inventory `bond_status` (approved classification
  request) is the source of truth. Movement `bond_classification` and Reconciliation
  `bond_scope` are derived from it and read-only in the UI and refused on direct edit.
  Existing locations are aligned once when the core is installed.
* **Suite roles**: Suite Operator / Manager / Auditor imply the matching role of every
  module (dashboard roles included). Module roles still work on their own.
  The Bond Classification Controller (movement) is deliberately not implied.
* **LC link**: on install, `bond_lc_model_name` (Bond Inventory) and the LC model of
  Commercial Management are set to `nelsis.lc` where empty. A transfer's LC Number
  fills the bond LC reference (open transfers only, never overwrites).
* **Dashboard** (`nelsis_bond_dashboard`): entitlement ratio uses `used_amount /
  approved_total` (quantity basis only); document cards read `nelsis.commercial.document`
  (submitted / expired); outstanding reconciliations = not reconciled/closed; register
  rule uses `verification_state = pending`; the storage-deadline rule was removed
  because no module defines a storage period. Alert rules remain inactive on purpose
  (lead days are placeholders, not legal periods).
* `nelsis_bond_movement`: one small change in `models/stock_location.py` so the core can
  update the derived classification (context key `bond_suite_sync`).

## Not changed (still separate by design)
* Document-type masters exist in inventory, commercial and LC modules; shipments/BoE
  exist in both `nelsis_lc_management` and `nelsis_commercial`. Not merged, because that
  would alter modules that were to stay untouched.
* Each module keeps its own top-level app menu.
* No statutory value was added anywhere.

## Purchase integration (`nelsis_bond_purchase`, added)
* New module; see its README. Linked on the order (LC, commercial file, entitlement), on the
  consignment (`purchase_order_id`, `lc_shipment_id`, line `purchase_line_id`) and on bond receipts.
* A bond receipt now fills the transfer's BoE / LC / license / entitlement references **at creation**
  (all receipts, not only purchase ones) and links it to the LC and commercial file when validated.
* Demo: `nelsis_bond_demo` gains `u15_purchase` and two purchase personas. On an existing demo database use
  Bond Demo Data > Re-run loader.

## Install fixes found by a real Odoo 17 install (this release)
Pre-existing, the suite did not load. Fixed with hidden unrestricted fields / sudo reads only:
* movement form, reconciliation register list, commercial file line list, dashboard audit forms:
  fields used in domains or modifiers were missing or group-restricted (12 other form views got a hidden
  `company_id`);
* `nelsis_bond_license` utilization: value-basis check reads the move unit price with sudo;
* `nelsis_commercial` discrepancy computation reads validated transfers with sudo;
* demo: compliance rule step used `action_submit` (real method `action_submit_review`).

## Verification status
Installed and tested on Odoo 17.0 (Community, PostgreSQL 16): clean install of the full suite + purchase + demo
loads all 109 demo steps. Purchase tests: 13 of 13 pass. The suite's own tests: 26 of 199 fail with or without the
purchase addon (same list), so they are existing failures, not caused by it - mostly movement / reconciliation tests
whose location classification set-up no longer matches the code, plus one entitlement amendment test.
