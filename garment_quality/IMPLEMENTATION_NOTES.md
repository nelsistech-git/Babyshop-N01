# garment_quality — Implementation Notes

Module 16: Smart Garment ERP — Quality Management System (QMS)

This module merges three overlapping SRS revisions into one coherent design:

* `Quality Management System.txt` — base QMS (source doc numbers itself "Module 15")
* `Garment Quality Management System (QMS).txt` — later, more detailed revision ("Module 40")
* `Advanced Garment Quality Management System (QMS).txt` — advanced QMS ("Module 32")

All three describe essentially the same quality lifecycle (Incoming → Cutting →
Sewing Inline → End Line → Washing → Finishing → Final/AQL → Buyer Approval →
Shipment Release) at increasing levels of detail, with different technical
names proposed for overlapping models across the three documents. Where
names conflicted, the most descriptive / most structurally sound name was
kept and the alternates are noted in the model docstrings.

Because the three source SRS documents each used the module number "15",
"32" or "40" for this module, and "15" is already claimed by the sibling
`garment_production` module in this build, this module's manifest header
uses **Module 16** for consistency with the rest of the built suite's
numbering — a purely cosmetic renumbering, not a scope change.

## Models created (17)

| Model | Purpose |
|---|---|
| `garment.quality.standard` | Buyer / product / process quality standard master (AQL level, tolerance, packaging rules) |
| `garment.quality.defect.code` | Defect code / master library (category, defect group, severity, department, 4-point value) |
| `garment.quality.checkpoint` | Stage-specific inspection checklist template (Incoming/Fabric/Accessory/Cutting/Sewing Inline/End Line/Washing/Finishing/Final) |
| `garment.quality.checkpoint.line` | Checklist items of a checkpoint template |
| `garment.quality.inspection` | Unified inspection document for every stage — the module's central document |
| `garment.quality.inspection.checklist.line` | Checklist execution lines on an inspection |
| `garment.quality.measurement.line` | Measurement check lines (chest/length/sleeve/etc. spec vs. actual vs. tolerance) |
| `garment.quality.defect` | Individual defect occurrence log, linked to an Inspection or AQL Inspection and a Defect Code |
| `garment.aql.inspection` | AQL sampling & Final Inspection, with buyer portal approval and shipment release control |
| `garment.quality.test.report` | Lab / physical test reports (shrinkage, GSM, color fastness, pull strength, etc.) |
| `garment.quality.rework` | Repair / rework management with re-inspection result |
| `garment.quality.capa` | CAPA (Corrective And Preventive Action) — general quality-process CAPA |
| `garment.quality.rca` | Root Cause Analysis (5-Why / Fishbone / Pareto) |
| `garment.quality.complaint` | Buyer quality complaint management with resolution workflow |
| `garment.quality.audit` | Quality audit (Internal / Buyer / Compliance / Process / Pre-Production / Inline / Social) |
| `garment.quality.audit.finding` | Findings recorded on a quality audit |
| `garment.quality.ai.analysis` | AI quality insight log (risk prediction, defect trend, supplier score, computer-vision, IoT) |

## SRS sections covered

Every feature area named across the three SRS documents' acceptance
criteria is modeled:

* Incoming material inspection (fabric/trim/accessory) tied to GRN — ✅ `garment.quality.inspection` (`inspection_type in incoming_material/fabric/accessory`) + `grn_id`/`grn_line_id`/`material_id`
* Cutting QC — ✅ `inspection_type = cutting`, `cutting_batch_no`
* Sewing Inline QC — ✅ `inspection_type = sewing_inline`, `sewing_line`, `operation`
* End Line QC — ✅ `inspection_type = endline`
* Washing QC — ✅ `inspection_type = washing`
* Finishing QC — ✅ `inspection_type = finishing`
* Final Inspection / AQL — ✅ `garment.aql.inspection` with automatic accept/reject decision logic
* Defect logging with defect codes/categories — ✅ `garment.quality.defect.code` (master) + `garment.quality.defect` (occurrence log), seeded with ~24 common garment defect codes across Fabric/Accessory/Cutting/Sewing/Washing/Finishing
* Quality checkpoints across Cutting/Sewing/Finishing/Packing — ✅ `garment.quality.checkpoint` (+ seed data for 6 stage templates)
* CAPA (corrective/preventive action) — ✅ `garment.quality.capa`, linkable from a Defect, Inspection, Complaint or Audit
* Root Cause Analysis (5-Why/Fishbone/Pareto) — ✅ `garment.quality.rca`
* Repair / Rework — ✅ `garment.quality.rework`
* Test reports (shrinkage, color fastness, GSM, pull strength) — ✅ `garment.quality.test.report`
* Buyer complaint management — ✅ `garment.quality.complaint`
* Quality audits (internal/buyer/compliance/process/social) — ✅ `garment.quality.audit`
* Pass/Fail/Hold disposition workflow — ✅ `state`/`disposition` fields with statusbar on `garment.quality.inspection` and `garment.aql.inspection`
* Buyer Quality Approval Portal — ✅ `garment.aql.inspection` and `garment.quality.complaint` inherit `portal.mixin`, with `ir.rule` scoping portal buyers to their own buyer's records
* Quality dashboards (list/kanban/pivot/graph) — ✅ tree/kanban/pivot/graph views on `garment.quality.inspection`, pivot on `garment.quality.defect`
* AI quality prediction / defect trend / supplier score / computer vision / IoT monitoring — ✅ `garment.quality.ai.analysis` (see "Deliberately simplified" below)

## Deliberately simplified / deferred

* **AI Quality Prediction, AI Root Cause Detection, AI Defect Trend
  Analysis, AI Supplier Quality Score, Computer Vision Quality Inspection,
  IoT Quality Monitoring** (all three SRS docs, various sections) are
  consolidated into a single structured log model, `garment.quality.ai.
  analysis`, rather than 5-6 separate near-identical models. A real
  ML/computer-vision/IoT pipeline is out of scope for an Odoo Community
  addon; this model gives the quality team a place to review AI-generated
  insights (from a future external service, via API/webhook, or entered
  manually) and to link them to a follow-up Inspection or CAPA. No actual
  prediction logic is implemented.
* **Digital Signature Integration** (base QMS SRS sec. 20/55, Advanced
  QMS SRS sec. 56) is not implemented as a separate e-signature model;
  Odoo's standard chatter/activity trail on every document (via
  `mail.thread`/`mail.activity.mixin`) is used as the audit trail instead.
* **Quality API Integration** (`POST /api/quality/inspection/create`
  etc., all three docs) is not implemented — no REST controller was
  requested by the SRS beyond the endpoint sketch, and building a public
  API is a separate concern from the ERP model layer. The models are
  structured so a future `garment_quality_api` extension module could add
  these controllers without changes here.
* **Mobile Application** (all three docs) — no native/PWA mobile app is
  built; Odoo's responsive web client and existing Binary/attachment
  fields (photo evidence on Inspection/Defect) cover the "photo capture",
  "defect entry" and "digital signature via chatter" requirements from a
  browser or tablet. Offline mode is out of scope for Odoo Community.
* **AQL sample-size lookup table** (ANSI/ASQC Z1.4 lot-size → sample-size
  tables) is not hard-coded; `lot_size`, `sample_size`, `inspection_level`
  and the accept/reject numbers are entered by the inspector (as the SRS
  examples themselves show manually-keyed values), and the pass/fail
  decision is computed automatically from the defect counts. A follow-up
  could add the standard table as seed data and an `onchange` to
  auto-populate sample size and accept/reject numbers.
* **Quality Cost Management** (`Rework Cost`, `Rejection Cost`, `Delay
  Cost` — base QMS SRS sec. 50, Advanced QMS SRS sec. 49) is not
  separately modeled; it depends on Finance module cost centers
  (`garment.cost.center`, `garment.expense` in `garment_finance`) that
  were judged out of this module's direct scope. A future
  `garment_finance` integration could add a computed quality-cost field
  driven by `garment.quality.rework`/`garment.quality.defect` quantities.

## Cross-module integration — how and why

* **`garment.style`** (garment_style_library) — Many2one on almost every
  document (`garment.quality.inspection`, `garment.aql.inspection`,
  `garment.quality.defect`, `garment.quality.capa`,
  `garment.quality.complaint`, `garment.quality.audit`,
  `garment.quality.checkpoint`, `garment.quality.ai.analysis`).
* **`garment.grn` / `garment.grn.line` / `garment.material`**
  (garment_warehouse) — Many2one on `garment.quality.inspection` for
  incoming material inspection (`inspection_type` in
  `incoming_material`/`fabric`/`accessory`), and on
  `garment.quality.test.report`.
* **`garment.supplier`** (garment_supplier) — Many2one on
  `garment.quality.inspection`, `garment.quality.test.report`,
  `garment.quality.capa`, `garment.quality.audit`,
  `garment.quality.ai.analysis`.
  **Note:** `garment_supplier` already has its own
  `garment.supplier.capa` and `garment.supplier.audit` models, scoped to
  *supplier compliance* audits/CAPA. This module's
  `garment.quality.capa`/`garment.quality.audit` are deliberately kept
  separate — they are the *production-floor / quality-process* CAPA and
  audit (triggered by a defect, an inspection, a buyer complaint or an
  internal/process audit), with an optional `supplier_id` link for when a
  quality issue happens to be supplier-caused. This is called out again in
  both model docstrings so a future reviewer doesn't merge them
  incorrectly.
* **`garment.buyer`** (garment_buyer_crm) — Many2one on
  `garment.quality.standard`, `garment.aql.inspection`,
  `garment.quality.complaint`, `garment.quality.audit`.
* **`garment_production`** — declared as a manifest `depends` per the
  task's integration instructions, **but no hard Many2one is used**. See
  "Production-side link" below.

## Production-side link (flag for follow-up integration review)

At the time this module was authored, the sibling `garment_production`
module (being built concurrently by another agent) exists on disk with
`garment.production.line`, `garment.work.center`, `garment.production.
machine` and `garment.operation.routing` models, but **does not yet
expose a Production Order model** (no `garment.production.order` or
equivalent was found).

Per the task's explicit hedging instruction, this module does **not**
create a hard `Many2one('garment.production.order', ...)` field. Instead,
every place a production-floor reference is needed uses a **plain `Char`
soft-reference field**, named `production_order_id` for traceability with
the originally-suggested field name, on:

* `garment.quality.inspection` (`production_order_id`, plus
  `cutting_batch_no`, `sewing_line`, `work_center`, `operation` — all
  `Char`)
* `garment.aql.inspection` (`production_order_id`)
* `garment.quality.defect` (`production_order_id`, `sewing_line`)
* `garment.quality.audit` (`production_order_id`)
* `garment.quality.ai.analysis` (`production_order_id`, `sewing_line`)

**Follow-up action required once `garment_production` stabilizes:**
convert these `Char` fields to real `Many2one` relations — most likely
`production_order_id` → whatever the sibling module's finished Production
/ Work Order model turns out to be, and `sewing_line`/`work_center` →
`Many2one('garment.production.line')` / `Many2one('garment.work.center')`
(both of which already exist and look stable as of this writing, but were
deliberately *not* hard-linked either, since the whole sibling module was
still being actively built in the same session and could still be
refactored before both modules are installed together). This is the
single biggest piece of technical debt in this module and should be the
first thing revisited in a follow-up integration pass.

## Order reference

No Order Management module exists yet in this suite (see MODEL_MAP.md:
`garment.merch.handover` / `garment.merch.order.confirmation` are the
closest existing things to an "order", and a future
`garment.order.management` module is expected to build the real Sales/
Production Order on top of them). Rather than reaching into
`garment_merchandising` for a single optional field, `order_reference` is
kept as free-text `Char` on `garment.aql.inspection` and
`garment.quality.complaint`. Convert to a real Many2one once the Order
Management module exists.

## Security

Five roles matching the SRS role tables across all three documents:

* `group_quality_production_view` — Production Supervisor: view
  defects/inspections, act on assigned CAPA (matches the SRS's
  "Production Manager: Corrective Action" responsibility)
* `group_quality_inspector` — QC Inspector: inspection entry, defect
  entry, test reports
* `group_quality_supervisor` (implies inspector) — line supervision,
  rework, AQL/Final Inspection entry (Final Auditor)
* `group_quality_manager` (implies supervisor) — QA Manager: full CRUD
  on every model, inspection planning, CAPA/RCA/audit/complaint
  management, configuration (standards/defect codes/checkpoints)
* `group_quality_director` (implies manager) — Quality Director/Head:
  full access, top of the hierarchy

Portal buyers (`base.group_portal`) get read-only access to their own
buyer's AQL/Final Inspections (with approve/reject actions gated by the
`buyer_approval_status` field and model methods, not by record rules) and
read+create access to their own buyer's Complaints, scoped via `ir.rule`.

## Validation performed

* `python3 -m py_compile` on every `.py` file — all pass.
* `xmllint --noout` on every `.xml` file — all pass.
* Every field referenced in every view (including nested one2many
  sub-trees, resolved against the correct child model) was checked
  against the actual model field definitions — no unknown fields.
* Every `ir.model.access.csv` row's `model_id:id` matches a model defined
  in this module, and every model defined in this module has at least one
  access row (no ungranted model).
* Every `res.groups` id referenced in `ir.model.access.csv` and in the
  security `ir.rule` records resolves to a group defined in
  `security/garment_quality_security.xml`.
* The manifest's `data` list matches exactly the `.xml`/`.csv` files
  present in the module (no missing, no extra), in security → data →
  views → menus order.
* No deprecated `attrs=`/`states=` view syntax is used anywhere.
