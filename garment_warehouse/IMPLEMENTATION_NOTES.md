# garment_warehouse — Gap-Upgrade Implementation Notes

Baseline: this module already implemented the 9 models (`garment.warehouse`,
`garment.location`, `garment.material`, `garment.grn`, `garment.grn.line`,
`garment.stock.move`, `garment.fabric.roll`, `garment.barcode`,
`garment.rfid.tag`) plus the AI-engine extension. This pass reconciled it
against the union of all three source SRS documents (Module 13 "Inventory &
Warehouse Management System", Module 31 "Garment Warehouse & Inventory
Intelligence System", Module 39 "Garment Warehouse & Inventory Management
System"), closed the gaps, and fixed the `attrs=`/`states=` bug pattern.
**No existing model, field, or method was renamed or removed** — every
change below is additive, since `garment_production`, `garment_maintenance`
and `garment_iot_platform` already depend on this module's models.

## Bug fix: `attrs=` / `states=` -> Odoo 17 direct attributes

Found and converted **6 instances** across 2 files (the only files that had
any):
- `views/garment_grn_views.xml` — 2 buttons (`gate_status`, `status`)
- `views/garment_stock_move_views.xml` — 4 fields/buttons (`state`,
  `move_type` x3)

All converted to direct `invisible="..."` expressions, matching the pattern
already used consistently across the other 27 modules in the suite (e.g.
`invisible="status not in ('a', 'b')"`).

## SRS gaps closed

1. **Multi-location / bin management** — `garment.location` gained
   `location_type` (Zone/Rack/Shelf/Bin), `location_purpose`
   (Storage/Gate-Dock/Quality Hold/Staging — for RFID gate and QC-hold
   areas from the SRS), and computed `occupied_qty` / `utilization_percent`
   from the stock ledger. Added a proper form + search view (it previously
   had only an editable tree).

2. **Cycle Counting** (new models `garment.stock.count` /
   `garment.stock.count.line`) — Draft -> In Progress (snapshots system
   qty from the ledger) -> Submitted -> Approved. Approval requires the
   Warehouse Manager group and posts one audited `adjustment_in`/
   `adjustment_out` stock move per variance line, so the stock ledger stays
   the single source of truth. Lines carry the material's ABC class
   (related, stored) for count-frequency planning.

3. **Min/Max Reorder** — `garment.material.action_create_purchase_requisition()`
   raises a `garment.purchase.requisition` (+ line) pre-filled from the
   shortage, one click from a low/out-of-stock material. A daily
   `ir.cron` (`_cron_daily_warehouse_alerts`) also schedules a To-Do
   activity (dedup'd against already-open ones) for low stock, expiry
   risk (<=30 days) and dead stock, per the SRS "Inventory Workflow
   Automation" rules.

4. **Aging / slow-moving stock analysis** — `garment.material` gained
   stored `stock_age_days`, `aging_bucket` (0-30/31-90/90+), `is_slow_moving`
   (90+ days), `is_dead_stock` (240+ days, matching the existing AI
   threshold), plus search filters and a Stock Aging graph/pivot dashboard
   (`action_garment_warehouse_aging_dashboard`).

5. **Fabric roll lot/shade tracking** — added `lot_number`, `shade_number`
   + `shade_approval_status`, `relaxation_time`, `inspection_status`
   (Bangladesh Garment Warehouse Standards section), and extended `status`
   with `damaged`/`rejected` (Fabric Inventory Status section) with
   matching action buttons.

6. **RFID/barcode scanning workflows** — `garment.barcode` gained
   `usage_type` (material/roll/carton/location/batch, per the SRS Barcode
   Types list) and a `location_id`; `action_scan()` now accepts a scanned
   location and relocates the linked fabric roll, making "Scan -> Stock
   Update" real instead of just logging a timestamp. `garment.rfid.tag`
   gained `movement_authorized` + a `gate_event = 'unauthorized'` state and
   `action_flag_unauthorized()` for the "Smart Warehouse Gate" unauthorized-
   movement alert.

7. **Warehouse KPIs** — `garment.warehouse` gained smart-button stats
   (Locations / Pending GRNs / Low-Stock Materials) and a computed
   `space_utilization_percent`. `garment.grn` gained `completed_date` +
   computed `processing_hours` (Receiving KPI). A Stock Count accuracy
   pivot (`action_garment_stock_count_dashboard`) covers the Inventory KPI
   (stock accuracy / turnover) from the "Warehouse Performance Analytics"
   section.

8. **Inventory Approval Rules** — Adjustment / Return / Transfer stock
   moves (`adjustment_in`, `adjustment_out`, `return`, `transfer_in`,
   `transfer_out`) are now created in `draft` and require
   `action_approve_movement()` (Warehouse Manager group) before they count
   towards on-hand quantity — the SRS "Stock Adjustment ... require
   approval" rule. Stock Count approval posts its adjustment moves
   pre-approved (the count approval itself is the managerial approval
   event) via a `skip_adjustment_approval` context flag.

9. **Internal Stock Transfer** — new `garment.stock.transfer.wizard`
   (Stock menu -> "New Stock Transfer") creates the paired `transfer_out`/
   `transfer_in` moves together under one reference, instead of relying on
   a store keeper to create two unlinked moves by hand.

10. **Chemical safety / batch tracking on the material master** — added
    `batch_number`, `expiry_date` (+ computed `expiry_alert`),
    `hazard_category`, `storage_condition` (Chemical Store Management /
    Chemical Safety Control sections).

11. **Accessories fields** — `color`, `size`, `buyer_approval_status` on
    the material master (Accessories Inventory Information / Bangladesh
    Accessories Store Requirements).

12. **GRN Quality Hold** — `garment.grn.line.quality_status` gained
    `on_hold` + a `hold_reason` field (Material Quality Hold System
    section).

13. **ABC Classification** — `garment.material.abc_classification`
    (A/B/C) with `action_classify_abc()` ranking all of a company's
    materials by inventory value (top 20% = A, next 30% = B, rest = C),
    used by Cycle Counting to prioritise count frequency.

## Deliberately simplified / deferred

- **Negative Inventory Override** (SRS "Inventory Approval Rules") is not
  separately gated — an issue move that would drive available qty negative
  still posts. Blocking it needs a same-material row lock across concurrent
  moves that is out of scope for this pass; the Adjustment/Return/Transfer
  approval gate covers the higher-value part of that SRS section.
- **CCTV Integration** (Module 31, explicitly marked "(Future)" in the
  source SRS) is not implemented — out of scope by the SRS's own admission.
- **Smart Rack / Digital Picking / Automated Warehouse Gate hardware
  integration** is left as the existing AI-engine `suggest_putaway_location`
  plus the new `location_purpose='gate'` marker; a real IoT/gate connector
  belongs in `garment_iot_platform` (which already depends on this module's
  models) rather than being duplicated here.
- **Finished Goods carton/packing** (SRS "Carton Management", "Packing
  Management System") is intentionally not modeled here — `garment.packing.carton`
  / `garment.packing.order` already exist in `garment_production`, and
  `garment_warehouse` does not depend on `garment_production` (the
  dependency runs the other way), so duplicating carton tracking here would
  create overlapping models against the house-style rule.
- `occupied_qty` / `space_utilization_percent` sum raw stock-move quantity
  per location across whatever materials/UoMs share that bin. This is
  correct for the common single-material bin case the SRS examples assume,
  but is only an approximate operational indicator (documented via field
  `help=`) if a bin genuinely mixes materials measured in incompatible
  units — full multi-UoM normalization was out of scope.
- The `state` statusbar widget on `garment.stock.move` is still directly
  clickable in the UI (pre-existing pattern in this module, e.g. `done` /
  `cancelled` were already reachable that way); the new approval gate is
  enforced in `create()`/`action_approve_movement()`, not via a hard UI
  lock on the statusbar widget itself.

## Cross-module links (unchanged models, only new references)

- `garment.material.action_create_purchase_requisition()` creates
  `garment.purchase.requisition` / `garment.purchase.request.line`
  (`garment_purchase`, already a listed dependency).
- No new `depends` entries were needed — all new cross-references target
  `garment_purchase`, which was already a dependency.

## Validation

- `python3 -m py_compile` — all `.py` files pass.
- `xmllint --noout` — all `.xml` files pass.
- Every `<record>`/`<menuitem>` id referenced via `ref=` across the module
  resolves to a locally-defined id (or a known external one such as
  `base.group_user`, `mail.mail_activity_data_todo`, or a model id).
- Every field referenced in a view/search/report belongs to that view's
  declared model (including the correct child model inside each
  `One2many` sub-tree).
- `__manifest__.py`'s `data` list includes every new file, in a
  security -> data -> views -> wizard -> report -> dashboard -> menus
  load order (menus last, per house style).
