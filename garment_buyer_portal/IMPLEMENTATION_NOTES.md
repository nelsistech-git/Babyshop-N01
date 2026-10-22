# garment_buyer_portal — Implementation Notes

Module 10 of the Smart Complete Garment Software suite: **Buyer Portal Management System**.
Built strictly as a **read-access + buyer-approval-action layer** over the real transactional
modules (`garment_order_management`, `garment_sample_management`, `garment_logistics`,
`garment_techpack`, `garment_style_library`, `garment_quality`) via `portal.mixin`
additions and a `CustomerPortal` controller extension. No order/sample/shipment/techpack/
quality data is duplicated anywhere in this module.

## SRS sections covered

| SRS section | Coverage |
|---|---|
| 5 — User Types | `res.groups` (internal: Portal Support Staff / Coordinator / Manager / Managing Director) + `res.partner.garment_portal_role` (external: Buyer Admin / Buyer Merchandiser / Buyer QA / Buyer Logistics) |
| 6-7 — Buyer Account / User Management | Reuses `garment.buyer` + `garment.buyer.contact` (garment_buyer_crm); a portal login is `garment.buyer.partner_id` or a child `res.partner` contact, both stamped with the new `res.partner.garment_buyer_id` field so a buyer can have multiple portal users |
| 8 — Buyer Dashboard | `home()` controller override injects Active Orders / Sample Status / Shipment Status cards into `/my` |
| 9-10 — Order Tracking / Order Details | `/my/orders`, `/my/orders/<id>` over `garment.order` |
| 11, 27 — Buyer TNA Visibility/Collaboration | **Deliberately deferred** — not in this task's model/dependency scope (`garment_tna` was not in the assigned depends list); Order Timeline (SRS 9) is still covered via `garment.order`'s own `material/cutting/sewing/finishing/inspection_progress` fields, which give the buyer an equivalent stage-by-stage view without a hard TNA dependency |
| 12 — Sample Approval Portal | `/my/samples`, `/my/samples/<id>`; buyer decision flows through the unified Approvals inbox |
| 13, 16 — Buyer Comment / Communication Center | `garment.portal.message` (new model) — Comment → Assigned Team → Action Taken → Response Submitted → Buyer Confirmation, `/my/messages` |
| 14 — Document Center | Order document checklist already portal-visible via `garment.order.document` (existing portal ACL in garment_order_management); attachments on messages/approvals cover ad-hoc sharing. A dedicated `/my/documents` aggregator page is deferred (would only re-list documents already reachable from Orders/Approvals) |
| 15 — Notification System | Portal notifications piggy-back on `mail.thread` chatter/followers already on `garment.order`/`garment.sample`/etc.; WhatsApp/SMS channels are out of scope (no gateway configured in this suite) |
| 17 — Mobile Responsive | All templates use Bootstrap grid classes (`row`/`col-md-*`) inherited from `portal.portal_layout` |
| 18-19 — AI Buyer/Approval Assistant | Deferred — no AI engine hook requested for this module in scope; `garment.ai.engine` pattern from sibling modules could be reused later |
| 20, 40-41 — Portal/Buyer Analytics | Deferred — covered structurally by buyer_crm's own `ai_lead_score`; a dedicated portal analytics report is future work |
| 21-22 — Buyer Registration & Approval | `garment.portal.access.request` (new model): Registration Request → Sales Review → Management Approval → Portal Account Created → Welcome Email Sent, using the standard Odoo `portal.wizard` to actually grant access |
| 23-25 — Portal Security / Access Control / Data Visibility | `base.group_portal` + `ir.rule` scoped on `buyer_id.partner_id = user.partner_id.commercial_partner_id` (see "Multi-user buyer contacts" below); no portal ACL is granted on cost/margin/supplier models anywhere in the suite, so those stay invisible by construction |
| 26, 32 — Buyer Approval Workflow / Document Approval | `garment.portal.approval.action` (new model) unifies Tech Pack / Sample / Style buyer sign-off and writes the decision back onto the *real* `garment.tech.approval` / `garment.sample.approval` / `garment.style.approval` records (and the parent document's status) |
| 28 — Production Tracking | Basic view = `garment.order` stage/progress fields (already on the Order Details page); Advanced view (cutting/sewing/finishing/QC split) = the same 5 progress fields, already itemised in the Order Timeline table |
| 29 — Quality Portal | `/my/quality`, `/my/quality/<id>` over `garment.quality.inspection`, restricted to `state in (approved, released)` so the buyer never sees an in-progress internal inspection |
| 30-31 — Shipment Tracking / Map Tracking | `/my/shipments`, `/my/shipments/<id>` over `garment.shipment` + `garment.container`; live GPS/vessel-API tracking (31) is explicitly "Future integration" in the SRS itself — not built |
| 33 — Buyer Report Center | Deferred — the list/detail pages already surface every field the SRS's four report types ask for; a dedicated downloadable-PDF report is future work |
| 34 — Buyer Portal API | Deferred — the task scope is the Odoo portal (`/my`), not a JSON/REST API; the controller design (thin routes over `sudo()` domain-scoped searches) would extend cleanly to a `type='json'` API controller later |
| 35-37 — DB Design | The SRS's own suggested technical names (`garment.buyer.user`, `garment.buyer.company`, `garment.buyer.approval`, `garment.buyer.comment`, `garment.buyer.document`, `garment.buyer.notification`, `garment.buyer.activity`) are **not** created 1:1 — per `MODEL_MAP.md` the buyer master is `garment.buyer` (garment_buyer_crm) and buyer documents are `garment.buyer.document` (already exists); this module adds only the four models the task specifically calls for: `garment.portal.access.request`, `garment.portal.approval.action`, `garment.portal.message`, `garment.portal.activity.log` |
| 38 — Portal UI Design | Main menu (Dashboard/Orders/Samples/Shipments/Quality/Approvals/Messages) added to `/my` via `portal.portal_my_home` inheritance |
| 39 — Advanced AI Buyer Intelligence | Deferred (see 18-19) |
| 42-45 — Feedback / Complaint / Meeting / Document Expiry | Deferred — these are buyer-relationship-management features that belong conceptually in `garment_buyer_crm` (which already owns `garment.buyer.communication` and the expiring-document cron on `garment.buyer.document`), not the portal-access layer; out of this module's assigned scope |
| 46 — Buyer Portal Audit Trail | `garment.portal.activity.log` (new model), written on every login/view/download/approval-decision/comment from the controller |
| 47-49 — Performance / Testing / Acceptance | Structural (pagination via `portal_pager`, `sudo()` + `ir.rule` domain scoping keeps queries indexed on `buyer_id`); functional testing is out of scope for this code-generation task |
| 50 — Future Digital Collaboration | Explicitly "Future" in the SRS — not built |

## Models created

- `garment.portal.access.request` — Buyer Portal Access Request (registration & approval workflow)
- `garment.portal.approval.action` — Buyer Portal Approval Action (unified Tech Pack/Sample/Style buyer sign-off, writes back to the real approval records)
- `garment.portal.message` — Buyer Portal Message (buyer ↔ factory thread)
- `garment.portal.activity.log` — Buyer Portal Activity Log (audit trail)

## Existing models extended (`_inherit`)

- `res.partner` — `garment_buyer_id`, `garment_portal_role`, `garment_portal_department`, activity-count stat button
- `garment.buyer` (garment_buyer_crm) — keeps `partner_id.garment_buyer_id` in sync
- `garment.sample` (garment_sample_management) — adds `portal.mixin`
- `garment.shipment` (garment_logistics) — adds `portal.mixin`
- `garment.techpack` (garment_techpack) — adds `portal.mixin`
- `garment.quality.inspection` (garment_quality) — adds `portal.mixin`
- (`garment.order` already had `portal.mixin` and an `access_url` override in garment_order_management — untouched)

## Multi-user buyer contacts (SRS section 7)

Two sibling modules (`garment_sample_management`, `garment_logistics`) already ship a
`base.group_portal` `ir.rule` on `garment.sample`/`garment.shipment` keyed on the exact
login partner (`buyer_id.partner_id = user.partner_id`), matching `garment_order_management`'s
equivalent rule on `garment.order`. That only covers a buyer's *single* company-level portal
partner. Since Odoo ORs multiple rules for the same model+group, this module adds a second,
broader rule on those same three models — `buyer_id.partner_id = user.partner_id.commercial_partner_id`
— so a buyer's additional named portal users (created as child contacts under
`garment.buyer.partner_id`, per SRS section 7) also see their buyer's orders/samples/shipments.
The three new models this module owns, plus the portal grants it adds for
`garment.techpack` / `garment.quality.inspection` / `garment.style.approval`, use the
`commercial_partner_id` pattern directly.

## Dependency note

The task brief listed `garment_order_management, garment_sample_management, garment_logistics,
garment_techpack, garment_style_library, garment_buyer_crm, portal` as the depends. This module
also depends on **`garment_quality`**, because the task explicitly requires surfacing
`garment.quality.inspection` (owned by `garment_quality`, per `MODEL_MAP.md`) — that model
cannot be referenced without the dependency. `garment_tna` and `garment_bom_management` were
deliberately **not** added since TNA/BOM visibility was not in the task's enumerated read-list
(see the SRS-11/27 row above).

## Controller routes

`/my` (dashboard cards + menu), `/my/orders[/<id>]`, `/my/samples[/<id>]`,
`/my/shipments[/<id>]`, `/my/quality[/<id>]`, `/my/techpacks/<id>`, `/my/approvals[/<id>]`
+ `POST /my/approvals/<id>/action`, `/my/messages` + `POST /my/messages/new` +
`POST /my/messages/<id>/confirm`, and the public (no login) self-service
`/buyer-portal/register` + `POST /buyer-portal/register/submit`.

## Validation

- `python3 -m py_compile` — all 15 `.py` files pass.
- `xmllint --noout` — all 9 `.xml` files pass.
