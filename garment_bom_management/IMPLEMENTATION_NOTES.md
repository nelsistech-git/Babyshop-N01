# IMPLEMENTATION_NOTES — garment_bom_management

Gap-upgrade pass against `specs_txt/BOM (Bill of Materials) Management System.txt`
(SRS Module 5, Parts 1-3). The module already worked; this pass closed the gaps
between the SRS and the existing code, and fixed the `attrs=`/`states=` bug
pattern. Nothing pre-existing was renamed or removed — `garment.bom` /
`garment.bom.line` keep every field `garment_production` already links to.

## Bug fix: `attrs=` / `states=`

4 instances of the deprecated Odoo <17 view syntax were found and converted to
direct attribute expressions (`invisible="..."`, `required="..."`):
- `views/garment_bom_views.xml` — 3 (two header buttons, one `web_ribbon` widget)
- `views/garment_bom_approval_revision_views.xml` — 1 (revision "Approve" button)

`grep -rn "attrs=\|states="` across the whole module now returns nothing.

## SRS sections covered (already present, left as-is)

§4 BOM Types, §5 BOM Master fields, §6 Status Workflow (selection), §7 Header
Info, §16 Alternative Material Management, most of §20 Cost Calculation, most
of §21 Supplier Mapping, §31 Odoo Database Design (all 10 base models already
existed), §33 Security Groups (all 7 SRS roles already existed).

## SRS gaps closed in this pass

- **§6/§17 Status ↔ Approval Workflow wiring** — the BOM previously had the
  `status` selection but no way to move through it except jump straight to
  `active`. Added `action_submit_material_review` /
  `action_submit_technical_approval` / `action_submit_merchandising_approval` /
  `action_submit_costing_approval` / `action_submit_production_approved`,
  each creating the matching `garment.bom.approval` stage record and posting
  to chatter, plus header buttons per status.
- **§8 BOM Line Management / MODEL_MAP integration** — `garment.bom.line`
  existed but was never populated (no UI, nothing wrote to it), even though
  `garment_production.garment_production_consumption.bom_line_id` points at
  it for Material Issue. Added `garment.bom.action_sync_material_lines()`
  (consolidates Fabric/Trim/Packaging BOM into `line_ids`, called
  automatically before `production_approved` / final approval) plus a
  "Material Lines" notebook page. `garment.bom.line` also gained
  `buyer_material_code`, `is_restricted`/`restriction_reason`,
  `issued_qty`/`consumed_qty` and a `source_ref` Reference field for
  traceability back to the originating Fabric/Trim/Packaging line.
- **§9 Fabric BOM** — `fabric_code` and `fabric_name` fields were missing
  entirely (only the `fabric_role` category existed); added both, plus
  `padding` to the Fabric Role selection (SRS list had it, code didn't).
- **§11 Fabric Wastage** — added `wastage_approved_by_id` / `wastage_reason`
  (SRS wanted Approved By / Reason per wastage entry).
- **§12 Trim BOM** — added the SRS sub-fields that were missing:
  `thread_brand`, `zipper_slider_type`, `button_type`, `button_hole_type`,
  `label_artwork_reference`, `label_position`; added `tape`, `buckle`,
  `hook_loop` to Trim Type (SRS list had them, code didn't).
- **§13 Packaging BOM** — split `carton` into `inner_carton`/`master_carton`,
  added `silica_gel` to Packaging Type, added `packaging_size` and `weight`
  fields (SRS "Size"/"Weight" were missing).
- **§14/§15 Size/Color-wise BOM** — `garment.material.consumption` only
  linked to a Fabric line; SRS says color can also have "different trims...
  different packaging". Added `trim_bom_id`, `packaging_bom_id`,
  `artwork_reference`, and a computed `total_requirement` field (SRS names
  this explicitly and it did not exist).
- **§18 Change Reasons** — `change_reason` was free text only; SRS lists 6
  specific categories. Added `change_reason_category` selection plus
  `change_severity` (drives §39 below), kept the free-text field for details.
- **§19/§44 AI Assistant** — added `suggest_bom_risk_detection()` (Material
  shortage / Supplier delay / Price increase / Production impact risk) to
  the shared `garment.ai.engine`, wired to a new `ai_risk_note` field and the
  "Run AI Analysis" button; added `action_import_from_techpack()` (label +
  packaging specs from the linked Tech Pack, SRS §37.1's "From Tech Pack").
- **§21 Supplier Mapping** — added `supplier_code`, and a Supplier Ranking
  block (`quality_rating`, `delivery_rating`, `compliance_score`,
  `previous_issues_count`, computed `rank_score`) — SRS §21 explicitly asks
  for AI/system ranking and there was none.
- **§22 Material Price History** — this SRS section had zero code. Added a
  new model `garment.bom.price.history` (Material/Supplier/Previous
  Price/Current Price/Currency/Effective Date/Changed By/Reason, exactly the
  SRS "Price Record" fields), auto-logged from `garment.bom.supplier.write()`
  whenever `current_price` changes, plus a "Material Price Trend" graph.
- **§23 Purchase Requirement** — SRS formula
  `Purchase Qty = Requirement - Available - Incoming` (with Safety Stock)
  existed nowhere. Added `available_stock`/`reserved_stock`/`incoming_stock`/
  `safety_stock`/computed `purchase_qty` to Fabric/Trim/Packaging BOM lines,
  and `action_generate_purchase_requirement()` summarizing shortages to
  chatter. No hard `purchase`/`stock` dependency was added (see Deferred).
- **§27 Material Reservation** — a full SRS section with no code at all.
  Added new model `garment.material.reservation` (Order/Style/Material/
  Required/Reserved/Available/Shortage Qty) with an automatic Shortage Alert
  (`message_post` + BOM chatter note) when `shortage_qty > 0`, and a computed
  `material_availability_pct` roll-up on `garment.bom`.
- **§26/§38 Version/BOM Comparison** — no comparison tooling existed. Added
  wizard `garment.bom.compare.wizard` (Material/Consumption/Cost/Supplier
  diff between two BOMs), opened via a "Compare Versions" header button.
- **§34 Record Rules** — "Revision history cannot be deleted" was not
  enforced (admin group had `perm_unlink=1`). Set `perm_unlink=0` for every
  role on `garment.bom.revision` in the CSV **and** overrode
  `unlink()` to always raise, as defense in depth. "Cost fields restricted" /
  "Supplier pricing visible only to authorized users" — added `groups=` on
  the Commercial Information group, the Cost Variance page, and the
  `current_price`/`previous_price` fields (Costing/Purchase/Admin/Top
  Management only).
- **§35 API Specification** — added `controllers/main.py` implementing all
  5 listed endpoints (`GET/POST/PUT /api/bom[/<id>]`,
  `POST /api/bom/<id>/approve`, `GET /api/bom/<id>/requirements`),
  `auth='user'` so the existing security groups/record rules apply.
- **§36 Bangladesh Industry Data & Compliance** — added `yarn_count`,
  `dye_lot`, `shade_band`, `marker_efficiency_pct`, `wash_loss_pct` to Fabric
  BOM; `buyer_material_code`/`buyer_description`/`is_approved_mill`/
  `is_restricted`/`restriction_reason` (Buyer Requirements) on Fabric/Trim/
  Packaging BOM; and Compliance fields (`compliance_gots`, `compliance_grs`,
  `compliance_oekotex`, `compliance_rcs`, `compliance_higg_score`,
  `compliance_chemical_status`) on Fabric BOM (+ OEKO-TEX/chemical status on
  Trim BOM) — none of this existed before.
- **§37.2 BOM Template Management** — a whole SRS sub-section with no code.
  Added `garment.bom.template` / `garment.bom.template.line`, seed data for
  the SRS's own worked examples (Knit T-Shirt / Polo Shirt / Hoodie
  templates), and a binding wizard `garment.bom.template.apply.wizard`
  (Action menu on the BOM form) that creates Fabric/Trim/Packaging lines
  from the template.
- **§39 BOM Approval Matrix** — added `change_severity` on
  `garment.bom.revision` (auto-set to "major" for fabric/material-driven
  reasons) plus `technical_manager_approved`/`qa_manager_approved`/
  `buyer_approved` checkpoints that `action_approve()` now enforces for
  major changes before allowing approval.
- **§40 BOM Cost Variance** — added `actual_material_cost`, `cost_variance`
  (computed), `material_variance`, `consumption_variance`, `price_variance`,
  `wastage_variance` and `action_compute_cost_variance()` (soft cross-module
  pull from `garment.production.cost`/`garment.production.order` when that
  module is installed, entirely optional otherwise).
- **§41 Material Consumption Monitoring** — added `issued_qty`,
  `actual_consumption`, `returned_qty`, `wastage_qty` and computed
  `consumption_efficiency_pct` (`= Standard/Actual × 100`, the SRS formula)
  to `garment.material.consumption`.
- **§42 Barcode** — added a `barcode` field on `garment.bom` (defaults to
  the BOM Number), shown with `widget="barcode"` on the form.
- **§45 Notification System** — used the existing `mail.thread` /
  `mail.activity.mixin` infrastructure: approval-stage creation now
  `activity_schedule`s the approver and posts "approval pending"; a >5%
  cost-per-piece increase posts to chatter; a supplier or price change on
  `garment.bom.supplier` posts to the parent BOM; a reservation shortage
  posts and flips state. SMS/WhatsApp/Push channels are out of scope for a
  Community-only module (see Deferred).
- **§47 Module Dependencies** — `account.payment.term` was already
  referenced by `garment.bom.supplier.payment_term_id` but `'account'` was
  **not** in `depends` — a latent bug. Added `'account'` to `depends`.
- **§28/§29/§30 Dashboard & Reports** — added Fabric Consumption Trend, Trim
  Usage, Supplier Contribution and Material Price Trend graphs/pivots (all
  reachable from a new "Material & Cost Analysis" menu), plus three new
  print reports: Fabric Requirement Sheet, Trim Requirement Sheet, Material
  Shortage Report (alongside the existing BOM Cost Sheet).

## Deliberately deferred / simplified (and why)

- **Real Purchase/Inventory/Manufacturing integration** (SRS §23-25,
  actual PO/stock-move creation, `garment.fabric.roll` roll/RFID linkage).
  `garment_warehouse`, `garment_order_management` and `garment_production`
  all already depend on `garment_bom_management` — adding a depends back
  onto any of them would create a circular dependency. Purchase/stock
  quantities on Fabric/Trim/Packaging BOM lines are therefore plain
  manually-entered fields (`available_stock`, `incoming_stock`,
  `safety_stock`) with a computed `purchase_qty`, not a live stock read.
  A future dedicated Purchase/Warehouse integration pass should replace
  these with real `stock.quant`/`garment.material` links.
- **RFID hardware integration** (SRS §42 RFID Features/Workflow) — the same
  circular-dependency constraint applies to `garment.rfid.tag`
  (`garment_warehouse`). Only the BOM-side barcode field was added; RFID
  tag creation/scanning stays in `garment_warehouse`.
- **SMS / WhatsApp / Mobile Push notification channels** (SRS §45) — Odoo
  Community has no built-in gateway for these; only in-app
  (`mail.thread`/activities) notifications were implemented. A dedicated
  integration module would be needed for the other channels.
- **Mobile BOM Application** (SRS §43) — this is the `garment_mobile_platform`
  module's responsibility (session/device/offline-sync models already live
  there); the JSON API added here (§35) is what a mobile client would call.
- **Cost Variance auto-derivation** — `action_compute_cost_variance()` pulls
  `actual_material_cost` from `garment.production.cost` when that module is
  installed (soft `self.env.get(...)` lookup, never a hard dependency), but
  `consumption_variance`/`wastage_variance` stay manually editable — a true
  per-line derivation needs `garment.production.consumption` data mapped
  back through `garment.bom.line`, which is a Production-module-side report,
  not something this module should compute unilaterally.
- **IoT / Digital Twin / Automated Replenishment** (SRS §51 Future Smart
  Factory Enhancements) — explicitly future scope in the SRS itself; not
  implemented, matches `garment_iot_platform`'s separate scope.

## Existing-module models linked

`garment.style` / `garment.style.category` / `garment.style.color` /
`garment.size.set` (garment_style_library), `garment.buyer`
(garment_buyer_crm, via `style_id.buyer_id`), `garment.techpack` /
`garment.label.spec` / `garment.packaging.spec` (garment_techpack),
`res.partner` (suppliers), `account.payment.term`. Soft (non-dependency)
lookups added for `garment.production.order` / `garment.production.cost`
(garment_production) purely for the optional Cost Variance pull and the
"Production Orders" smart button — both degrade gracefully if that module
isn't installed.

## Validation

- `python3 -m py_compile` — every `.py` file in the module: **all pass**.
- `xmllint --noout` — every `.xml` file in the module: **all pass**.
- Cross-checked every `<field name="...">` in every view (including nested
  One2many sub-trees, resolved to the correct co-model) against the actual
  model field list — **0 mismatches**.
- Cross-checked `security/ir.model.access.csv`: every model defined by the
  module has at least one access row, and every row's `model_id:id` resolves
  to a real model — **0 ungranted models, 0 orphan rows**.
- Cross-checked every file in `security/`, `data/`, `views/`, `wizard/`,
  `report/` against `__manifest__.py`'s `data` list — **exact match both
  ways** (nothing missing, nothing orphaned).
- `grep -rn "attrs=\|states="` — **0 matches** across the whole module.
