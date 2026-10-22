# garment_supplier — GAP-UPGRADE Implementation Notes

Upgrade pass against `specs_txt/Supplier Management System.txt` (Module 11 SRS,
Parts 1-3). The module already implemented a solid core (supplier master,
category, product/price, document expiry, rating/scorecard, audit, CAPA,
risk, AI risk prediction + recommendation). This pass closed the remaining
SRS gaps and fixed the `attrs=` view bug.

## Bug fix: `attrs=` → Odoo 17 direct attribute syntax

Converted **10** instances of the deprecated `attrs="{...}"` syntax to direct
`invisible="..."` expressions (no `states=` usage was found anywhere in the
module):

- `views/garment_supplier_views.xml` — 9 instances (3 header buttons, 1
  `web_ribbon` widget, 1 stat button, 4 Blacklist-page fields).
- `views/garment_supplier_audit_views.xml` — 1 instance (Move to Next Stage
  button).

All new views written in this pass use the direct-expression syntax from
the start; `xmllint --noout` and manual review confirm zero remaining
`attrs=`/`states=` in the module.

## SRS gaps closed

1. **Section 5 / 6 — Supplier Types**: `supplier_type` only had
   Material/Service/Logistics. Added `processing` (printing/embroidery/
   washing/dyeing/finishing) and `compliance` (testing lab/certification
   provider/inspection agency) — the SRS names 5 supplier-type groups, not
   3. Mirrored the same two groups + three new sub-types on
   `garment.supplier.category` (`group`, `sub_type` selections) and seeded
   3 new compliance categories in `data/garment_supplier_category_data.xml`.
2. **Section 8 — Registration Management**: added `registration_source`
   (Internal Creation / Supplier Portal / Invitation Link) — the SRS names
   these three intake channels explicitly; only "internal creation" existed
   implicitly before.
3. **Sections 10, 37, 39 — Supplier Approval Workflow**: the `status`
   field's 5 stages existed, but the only action was `action_activate`
   jumping straight to Active with no per-stage approval or approver
   audit trail. Added `action_submit_purchase_review` /
   `action_approve_purchase_review` / `action_approve_quality_review` /
   `action_approve_compliance_review` / `action_approve_management`, each
   gated by the role named in the SRS section 37 Access Matrix
   (`has_group` checks against the module's existing security groups) and
   stamping a `*_by_id` / `*_date` pair per stage (new "Approval Workflow"
   form page). `action_activate` is kept as-is for backward compatibility.
4. **Section 13 — Price History**: the product line only had a single
   `previous_price` field (no real history). Added a new model
   `garment.supplier.price.history` (Material, Supplier, Unit Price,
   Currency, Effective Date, Validity, MOQ) as a One2many under
   `garment.supplier.product`, with an `action_log_price_history` button
   that snapshots the current price — matching the SRS's own
   year-over-year price example.
5. **Section 15 — Supplier Comparison**: no comparison tool existed.
   Added a transient wizard `garment.supplier.comparison.wizard` /
   `garment.supplier.comparison.line` comparing selected suppliers on
   Price (avg. product price), Quality/Delivery/Cost/Compliance (from the
   latest scorecard), Capacity and Payment Terms, with an overall score —
   reachable from Performance ▸ Compare Suppliers.
6. **Section 18 — Supplier Dashboard KPIs**: the existing graph/pivot
   dashboard covered "by Ranking" and a classification/rating pivot only.
   Added search filters for the remaining named KPIs: Approved, Top
   Suppliers (Platinum) and Expiring Documents (Active/Blacklisted/High-
   Risk filters already existed).
7. **Sections 19-20, 37-38 — Supplier Portal**: `garment.supplier` did not
   inherit `portal.mixin` (house-style requires it for
   buyer/partner-facing top-level documents) and there was no portal
   surface at all. Added `portal.mixin`, a new `controllers/portal.py`
   (`/my/supplier` dashboard — Purchase Summary/Delivery Status/Payment
   Status; `/my/supplier/profile` limited self-edit; `/my/supplier/
   documents` view + upload; read-only `/my/supplier/rfqs`,
   `/my/supplier/pos`, `/my/supplier/deliveries`), and
   `views/garment_supplier_portal_templates.xml`. All portal reads go
   through `.sudo()` scoped to the logged-in supplier's own record, never
   granting portal users direct model access — same pattern as
   `garment_buyer_portal`. Payment Status reads Module 12's
   `garment.payment` (which already has a direct `supplier_id` FK to this
   model), so `garment_finance` was added to `depends` (a real, structural
   dependency, not cosmetic).
8. **Section 33 — Reports**: only a combined "Supplier Profile" report
   existed. Added **Supplier Purchase Report** and **Supplier Delay
   Report** (both bound to `garment.supplier`, reading Module 9's PO/
   Delivery data by partner — no duplicate transactional storage).
9. **Section 45 — Bangladesh Garment Supplier Standards**: fabric
   (Composition, GSM, Width, Dyeing Process, Colour Fastness, Test
   Report) and accessories (Material Type, Size Specification, Colour
   Matching, Sample Approval) fields were entirely missing. Added them to
   `garment.supplier.product` behind a new `product_category` selector
   (Fabric / Accessory / Other) that shows only the relevant group, plus
   a new form view for the product line. Added BSCI/SEDEX/WRAP/ISO/
   OEKO-TEX/GOTS boolean certification flags to the supplier master
   (Compliance Certifications page), following the same boolean-checklist
   pattern already used on `garment.supplier.audit`.
10. **Section 47 — Document Expiry notification**: the "Certificate
    expires in 15 days" example was not implemented. Added
    `_cron_notify_expiring_documents` on `garment.supplier.document`
    (daily `ir.cron` in `data/ir_cron_data.xml`) that posts to the
    supplier's chatter and raises an activity for the Purchase Manager
    group for any document expiring within 15 days, with an
    `expiry_notified` flag so it fires once per expiry date.

## Deliberately simplified / deferred (with reason)

- **Section 41 — Supplier Contract Management**: not duplicated here.
  `garment.purchase.contract` already exists in Module 9
  (`garment_purchase`) — this was already correctly documented in the
  module description and remains unchanged.
- **Section 44 — Supplier API Integration** (external REST endpoints):
  no other module in the suite (including `garment_buyer_portal`)
  implements a public JSON/REST API layer; the closest equivalent —
  self-service via web routes — is now covered by the new Supplier
  Portal controller. A dedicated REST API is left for a future connector
  module rather than invented ad hoc here.
- **Section 46 — Supplier Material Traceability**: the SRS itself labels
  this "Future sustainability requirement" — left out of scope.
- **Section 47 — SMS/WhatsApp notification channels**: only the
  Email/chatter/activity channel is implemented; SMS/WhatsApp require an
  external gateway integration not available in this codebase.
- **Section 23 — Supplier PO Actions (Accept/Reject/Request Change/
  Confirm Delivery)**: the Supplier Portal shows POs and RFQs read-only.
  Adding supplier-initiated state transitions requires new methods on
  `garment.purchase.order` (Module 9), which is out of this task's scope
  (only `garment_supplier` was to be touched) — flagged for a follow-up
  task against `garment_purchase`.
- **Section 21 — Supplier Communication Center**: rather than a second,
  supplier-specific message-thread model duplicating
  `garment.portal.message` (buyer-side, in `garment_buyer_portal`), this
  reuses the chatter already provided by `mail.thread` on
  `garment.supplier` (Message Thread + File Sharing out of the box).

## Cross-module links (per MODEL_MAP.md)

No change to the module's existing links: `garment.purchase.rfq` /
`garment.purchase.order` / `garment.purchase.delivery` /
`garment.supplier.quotation` (Module 9, via `res.partner`), and newly,
`garment.payment` (Module 12, `garment_finance`, via a direct
`garment.supplier` FK) for the Supplier Portal's Payment Status. This
module's own `garment.supplier.audit` / `.capa` / `.risk` remain
supplier-level records, intentionally distinct from `garment_compliance`'s
factory-level `garment.compliance.*` models — no renaming or merging done.

## Validation

- `python3 -m py_compile` — all `.py` files compile cleanly.
- `xmllint --noout` — all `.xml` files (views, data, security, report,
  wizard) are well-formed.
- Manifest `data` list cross-checked against the filesystem: no missing
  files, no orphaned files left unregistered.
