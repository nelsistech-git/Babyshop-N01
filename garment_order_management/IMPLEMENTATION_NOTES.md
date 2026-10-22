# garment_order_management — Implementation Notes

Module 9 of the Nelsis Smart Garment suite: the central `garment.order`
document. Built against
`/tmp/nelsis_project/specs_txt/Garment Order Management System.txt`.

## Models created (11)

| Model | Purpose | SRS section(s) |
|---|---|---|
| `garment.order` | Order Master — buyer PO, style/brand/season, factory, status workflow, progress, risk, MRP/capacity snapshot | 6-8, 39, 41 |
| `garment.order.line` | Style / Color / Size-range / Qty / Price / Value / Delivery Date | 10 |
| `garment.order.size` | Size ratio & quantity breakdown per line | 13 |
| `garment.order.color` | Buyer/factory color code, Pantone, lab dip, shade group, approval | 12 |
| `garment.order.shipment` | Partial shipment tracking (shipped/pending/balance qty) | 28-30 |
| `garment.order.allocation` | Multi-factory / line allocation & order-split tracking | 14, 27-28 |
| `garment.order.risk` | Material/Production/Buyer/Shipment risk factors (manual + AI) | 18-19, 46 |
| `garment.order.document` | Document checklist (PO, tech pack, BOM, cost sheet, export docs...) | 9, 17, 51 |
| `garment.order.revision` | Post-confirmation change log (qty/style/color/size/date/price) | 44-45 |
| `garment.order.approval` | Approval-stage log (received → merch review → cost verification → planning review → management approval → released) | 15 |
| `garment.order.delay` | Delay & recovery planning | 32-33 |

## SRS sections covered

- **6-8** Order Master + status workflow (Draft → PO Received → Confirmed →
  TNA Created → Material Planning → Production Running → Quality Checking →
  Ready For Shipment → Shipped → Completed → Closed, plus Cancelled).
- **8-9** Buyer PO fields + document checklist/attachments.
- **10-14** Order lines, color info, size ratio breakdown (with an
  onchange auto-calculating quantity from ratio %), quantity breakdown by
  style/color/size/factory (factory breakdown lives on
  `garment.order.allocation`).
- **15-17** Approval workflow log + validation rules enforced in
  `_check_confirmation_prerequisites()` / `_check_production_release_prerequisites()`
  (approved costing, approved BOM, buyer PO, delivery date, sample
  approval before confirmation; approved BOM, active TNA, materials
  planned, capacity confirmed before production release) + the document
  checklist.
- **18-19, 46-48** Order risk (manual `garment.order.risk` log) and AI Order
  Risk Prediction / AI Delivery Prediction / AI Allocation Optimization —
  implemented by extending the shared `garment.ai.engine` abstract model
  (from `garment_buyer_crm`, the pattern already used by every sibling
  module) with a transparent, rule-based scorer in
  `models/garment_ai_engine.py` (works with or without an external AI
  provider, same fallback contract as the rest of the suite).
- **21-23** Planning integration fields (`bom_id`, `tna_id`, `costing_id`)
  and `action_release_to_production()`, which validates prerequisites and
  posts the release details to the chatter. **Deliberately does not create
  an actual Manufacturing/Production Order record** — per the task
  instructions, `garment_production` (built concurrently by a sibling
  agent) owns that model and will add its own `Many2one` back to
  `garment.order`; this module exposes exactly the fields a production
  module needs to hook into (`name` as natural key, `style_id`,
  `buyer_id`, `quantity`, `delivery_date`/`shipment_date`, `state`).
- **24-26** Material Requirement (`required_fabric_qty` = quantity ×
  `fabric_consumption_per_pc`), Material Availability (`material_status`,
  available/reserved/incoming/shortage), Production Capacity
  (required/available/shortage). Simplified: these are entered/tracked as
  plain fields on the order rather than live-computed from
  `garment.warehouse` stock or a real MRP engine — that belongs to the
  Warehouse/Production modules; `garment_warehouse` is intentionally **not**
  a dependency of this module.
- **27-29** Multi-factory allocation (`garment.order.allocation`) and
  partial shipment (`garment.order.shipment`) with shipped/pending/balance
  quantity.
- **30-31** Order tracking via per-stage progress fields (material,
  cutting, sewing, finishing, inspection) and a computed overall
  `progress` %. A dedicated stage-transition log model was not added;
  chatter (`mail.thread`, `tracking=True` on `state`) already gives a
  timestamped audit trail of every status change, which was judged
  sufficient rather than inventing a second logging model.
- **32-33** Delay & recovery planning (`garment.order.delay`).
- **34** Buyer portal tracking: `portal.mixin` + an `ir.rule` restricting
  portal users to their own orders (`buyer_id.partner_id = user.partner_id`).
  Costing (`costing_id`) is field-restricted with `groups='base.group_user'`
  so portal users never see it; internal models (`garment.order.risk`,
  `garment.order.allocation`, `garment.order.revision`,
  `garment.order.delay`, `garment.order.color`, `garment.order.size`) have
  **no** portal ACL row at all, keeping supplier/internal-production data
  out of the buyer portal per the SRS access matrix.
- **35-36, 37, 39-41, 51** Mobile app / multi-dashboard requirements are UI
  surfaces on top of this same data model (tree/kanban views + filters
  already group by buyer/status/risk/country); no separate mobile-specific
  backend model was needed. Export/Bangladesh fields (HS Code, buyer
  country, shipment mode, forwarder) are on the order header. Database
  design (section 39) mapped 1:1 to the models table above.
- **42-45** Security groups + record rules (see below) and the Order
  Locking System: `is_locked` is set automatically on confirmation;
  `garment.order.write()` blocks `style_id`/`delivery_date`/`shipment_date`
  changes and `garment.order.line.write()` blocks `quantity`/`unit_price`/
  `style_id` changes once locked (SRS: "Restricted changes: Quantity,
  Price, Delivery Date, Style Information") unless the user is an Order
  Manager or an Order Revision is used instead. Closed orders are fully
  read-only to non-managers via the same `write()` override.
- **49-50** API / EDI / IoT / courier integration: **deferred**. No sibling
  module in this suite ships an HTTP controller (verified against all 13
  other modules), so no `garment_order_management/controllers` package was
  added — this would be new suite-wide plumbing beyond one module's scope.
  The data model exposes everything a future controller would need
  (`name`, `state`, `progress`, buyer/style/qty/dates).
- **52-54** Non-functional / testing / acceptance criteria: satisfied by
  the model, security, view and validation design above (no separate
  artifact needed).
- **55** Future Smart Factory Order Automation: explicitly out of scope
  (documented as a roadmap item in the SRS itself).

## Cross-module integration (see MODEL_MAP.md)

- `garment.buyer` (`garment_buyer_crm`) — `buyer_id`, buyer-portal record
  rule via `buyer_id.partner_id`, merchandiser-assignment record rule via
  `buyer_id.assigned_merchandiser_id`.
- `garment.style` / `garment.style.category` (`garment_style_library`) —
  `style_id` (header) and `garment.order.line.style_id` (multi-style
  orders); `product_category_id` related field.
- `garment.merch.order.confirmation` / `garment.merch.quotation`
  (`garment_merchandising`) — `merch_order_confirmation_id` as the origin
  hand-over document, with an onchange that pre-fills buyer/style/dates/
  factory/currency from it; `quotation_id` traced through as a related
  field.
- `garment.bom` (`garment_bom_management`) — `bom_id`, checked in both
  confirmation and production-release validation.
- `garment.costing` (`garment_costing`) — `costing_id`, checked in
  confirmation validation (must be `status == 'approved'`).
- `garment.tna` (`garment_tna`) — `tna_id`, checked in production-release
  validation (must be `status in ('active', 'monitoring')`).
- `garment.techpack` / `garment.sample` (`garment_techpack`,
  `garment_sample_management`) — not stored as `Many2one` fields; exposed
  as `techpack_count` / `sample_count` smart buttons that search by
  `style_id`, matching SRS section 11 ("System automatically retrieves ...
  Tech Pack ... Sample Approval").
- `garment.ai.engine` (`garment_buyer_crm`, abstract model) — extended in
  `models/garment_ai_engine.py` with `predict_order_risk()`,
  `predict_order_delivery()` and `optimize_order_allocation()`.
- Deliberately **not** referenced: `garment.warehouse`/`garment.material`
  (material availability is tracked as plain fields, not live stock — see
  above) and any production/shipment/finance model — those modules are
  expected to add their own `Many2one` back to `garment.order`, per the
  task instructions.

## Validation / definition-of-done

- `python3 -m py_compile` — all `.py` files pass clean.
- `xmllint --noout` — all `.xml` files pass clean.
- Every model has tree+form views; `garment.order` additionally has a
  search view with filters/group-bys (buyer, status, merchandiser, risk,
  country, delayed, active).
- Every model has `ir.model.access.csv` rows (base user read-only,
  merchandiser, department manager, order manager, plus portal read-only
  where the SRS access matrix allows it).
- All 9 `ir.actions.act_window` records are reachable from the module's
  own root menu ("Order Management").
- No deprecated `attrs=`/`states=` view syntax used anywhere in this
  module (verified with a repo-wide grep).
