# Implementation Notes — Garment Merchandising (GAP-UPGRADE pass)

Date: 2026-08-24
Scope: `garment_merchandising` — reconciled against both source SRS documents:
- `Merchandising Management System.txt` (Module 2, base spec)
- `Garment Merchandising Management System.txt` (Module 34, advanced spec)

## 1. Bug fix — deprecated `attrs=` / `states=` (Odoo 17 removed both)

Converted **7** occurrences to direct attribute expressions across 4 view files:

| File | Count |
|---|---|
| `views/garment_merch_order_confirmation_views.xml` | 2 |
| `views/garment_merch_inquiry_views.xml` | 2 |
| `views/garment_merch_quotation_views.xml` | 2 |
| `views/garment_merch_handover_views.xml` | 1 |

e.g. `attrs="{'invisible': [('status', '!=', 'draft')]}"` → `invisible="status != 'draft'"`.
A repo-wide grep after the fix (`grep -rn "attrs=\|states=" views/ report/`) returns no matches.

## 2. SRS gaps closed

### garment.merch.inquiry (SRS-2 §7 Buyer Inquiry Management)
The model previously covered only the "Basic Information" and "Assignment" groups. Added the
three sub-sections the SRS lists in full but the code omitted:
- **Product Details**: `product_description`, `fabric_type`, `fabric_composition`, `gsm`,
  `yarn_count`, `knit_type`, `weave_type`, `dyeing_type`, `washing_type`, `print_type`,
  `embroidery_type`, `finish_type`
- **Quantity**: `moq`, `order_quantity`, `size_breakdown`, `color_breakdown`,
  `destination_country_id`, `delivery_schedule`
- **Commercial Details**: `target_fob`, `currency_id`, `payment_term_id`, `incoterm_id`,
  `shipment_mode`, `port_of_loading`, `destination_port`
- Also added the missing header fields `buying_house` and `product_type`.
- New form notebook pages: Product Details / Quantity / Commercial Details.
- Attachments sub-section (Tech Pack, Artwork, Size Chart, ...) is intentionally **not**
  re-modeled as dedicated fields — `mail.thread` chatter already gives every inquiry a generic
  attachment area, and duplicating per-document Many2one fields here would fight with the real
  document-owning models (Tech Pack, Style, Document Management).

### garment.merch.style.line (SRS-2 §9 Style Development)
Added the highest-value missing fields from Product Specification / Material / Size / Color
groups without duplicating `garment.style`, `garment.style.color`, `garment.size.set` (the real
owners once "Create Style" is used): `factory_style_number`, `age_group`, `fit_type`,
`construction_type`, `main_fabric`, `size_range`, `color_name`, `pantone_code`.

### garment.merch.negotiation (SRS-2 §20 + SRS-34 §28 Buyer Price Negotiation)
- Added `mail.activity.mixin` (house-style requires both mixins on a top-level document; it only
  had `mail.thread`).
- Added `final_price`, `approved_by_id`, `approval_date` and an `action_approve()` method to
  close SRS-34 §28's "Buyer Offer / Factory Target Price / Final Price / **Approval**" flow —
  previously only the offer/counter-offer/decision fields existed, with no approval record.

### garment.merch.review.checklist
Added `mail.activity.mixin` (same house-style gap as negotiation). All SRS §11 checklist fields
were already present and correct — no field changes needed here.

### garment.merch.order.confirmation (SRS-2 §31 + SRS-34 §10/§33)
- **Order Booking fields** (SRS-34 §10: Color, Size, Terms) that were missing: `color`,
  `size_breakdown`, `payment_term_id`, `incoterm_id`.
- **Order Approval Workflow** (SRS-34 §33: Merchandiser → Merchandising Manager → Production
  Manager → Commercial Manager → Factory Head) — this multi-role sign-off chain did not exist at
  all; only the operational `status` field (draft→confirmed→...→completed) was present. Added a
  separate `approval_stage` field + 5 approver/approved-date field pairs + `action_next_approval_stage()`,
  mirroring the existing pattern already used on `garment.merch.handover`.
- Linked the new Task model (`task_ids`, `task_count`, `action_view_tasks`).

### New model — garment.merch.task (SRS-34 §5 department structure + §40 model list)
SRS-34 explicitly lists `garment.merch.task` as a database model and describes distinct
merchandiser roles (Senior/Junior/Production Merchandiser) with distinct task types (Sample
Follow-up, TNA Update, Documentation, Production Tracking, Delivery Follow-up), plus a
"Merchandiser Workload" dashboard chart (SRS-2 §34, SRS-34 §41-42) — none of this existed.
Added `garment.merch.task` (numbered, `mail.thread`/`mail.activity.mixin`, linked to Inquiry /
Order Confirmation / Buyer, with `task_type`, `department_role`, `priority`, `due_date`,
`is_overdue` (computed), `status` draft→in_progress→done/cancelled) with tree/form/kanban/search
views and a menu entry, plus a dashboard (graph+pivot) for merchandiser workload.

### Dashboard (SRS-2 §6/§34 + SRS-34 §13/§41-43)
The dashboard previously exposed only a Quotation graph/pivot. Added, in the same
graph/pivot/kanban act_window style already used across the suite (no custom JS dashboard exists
anywhere else in the 28-module suite, so none was introduced here):
- **Order Pipeline & Buyer Performance** — graph (order count/FOB value by status) + pivot
  (buyer × status, FOB value / quantity measures) on `garment.merch.order.confirmation`.
- **Merchandiser Workload** — graph + pivot on the new `garment.merch.task`, grouped by
  `assigned_to_id` × `status`.

### Deliberately deferred / out of scope
- **BOM, Costing, TNA, Sample Development, Tech Pack sections** (SRS-2 §10, §13-18, §21-24,
  §26-30) are owned by sibling modules (`garment_bom_management`, `garment_costing`,
  `garment_tna`, `garment_sample_management`, `garment_techpack`) per `MODEL_MAP.md` — this
  module's own manifest already states it intentionally does not duplicate them, and it still
  doesn't.
- **Gantt views** (SRS-2 §39) are not implemented — Odoo Community 17 ships no Gantt view type,
  and no other module in the suite uses one either; the Calendar view (already present) is the
  closest native substitute.
- **AI-Assisted Cost Prediction** (SRS-2 §24) — the existing `garment_ai_engine.py` extension
  already covers quotation price suggestion, negotiation counter-offer suggestion and
  workload-aware merchandiser assignment; fabric-price-trend / exchange-rate / historical-style
  AI features depend on data that lives in Costing/BOM (out of this module's scope) and were not
  duplicated here.
- **Order Risk Intelligence / AI Delivery Prediction** (SRS-34 §44-46) is already fully owned by
  `garment_order_management` (`garment.order.risk_level`, `ai_risk_reason`,
  `action_run_ai_risk_prediction`, etc.) — not re-implemented here.
- **Production Follow-up / Shipment Follow-up / Daily Production Update** (SRS-34 §34-36) are
  already covered by `garment.order` (cutting/sewing/finishing/inspection progress fields) and
  `garment.order.shipment` in `garment_order_management`, plus `garment.shipment` in
  `garment_logistics` — not duplicated here.
- **Buyer Communication** (SRS-34 §8) is already `garment.buyer.communication` in
  `garment_buyer_crm` — not duplicated here.

## 3. Cross-module references (garment_order_management / garment_plm)

Checked per the task brief whether `garment.merch.handover` / `garment.merch.order.confirmation`
should gain a Many2one to `garment.order` (order_management) or `garment.plm.project` (plm).

**Decision: no new `depends` added, and no new Many2one added in this direction.**
`garment_order_management`'s manifest already depends on `garment_merchandising`, and
`garment.order` already carries `merch_order_confirmation_id` (Many2one back to
`garment.merch.order.confirmation`) plus a derived `quotation_id`. `garment_tna` follows the same
pattern (`garment.tna.order_confirmation_id`). Adding a reverse dependency from
`garment_merchandising` onto `garment_order_management` (or `garment_tna`) would create a
circular module dependency, which Odoo rejects outright — so the existing "downstream module
points back via Many2one" direction is the correct and only valid one, and was left as-is.
`garment_plm` does not reference `garment_merchandising` at all (it links Style → Tech
Pack/BOM/Sample/Costing only) and nothing in either SRS document ties Merchandising Inquiry/Style
Development to a PLM stage-gate project, so no cross-reference was added there either.

Only new real dependency added: **`account`** (for `account.payment.term` /
`account.incoterms`, referenced by `garment.merch.quotation` since before this pass, and now also
by `garment.merch.inquiry` and `garment.merch.order.confirmation`) — the module referenced these
models without declaring the dependency; this is now fixed.

## 4. Validation

- `python3 -m py_compile` on every `.py` file in the module: **all pass**.
- `xmllint --noout` on every `.xml` file in the module (views, security, data, report):
  **all pass**.
- `grep -rn "attrs=\|states=" views/ report/`: **no matches** (all 7 converted).
- Manifest `data` list checked against the filesystem: every listed file exists; new files
  (`views/garment_merch_task_views.xml`) added to the list in dependency-safe order (security →
  data → views → report → dashboard → menus, menus last as required by house style).
- New model `garment.merch.task` has `ir.model.access.csv` rows for `base.group_user`,
  `group_merch_merchandiser`, `group_merch_manager`, and an `ir.rule` restricting merchandisers
  to their own assigned tasks (mirrors the existing inquiry rule).
