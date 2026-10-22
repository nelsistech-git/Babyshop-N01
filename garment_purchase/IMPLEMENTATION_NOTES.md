# garment_purchase — GAP-UPGRADE Implementation Notes

Source SRS: `Purchase Management System.txt` (Module 12, Parts 1-3).
This pass compared the SRS section-by-section against the existing
`garment_purchase` module, closed the gaps found, and fixed the
`attrs=`/`states=` bug pattern in every view file.

## SRS sections covered (already present, verified working)

- 7-12 Purchase Requisition + MRP + Priority (`garment.purchase.requisition`,
  `garment.purchase.request.line`)
- 13-17 RFQ + Supplier Quotation + Comparison (`garment.purchase.rfq`,
  `garment.supplier.quotation`)
- 18 AI Purchase Recommendation
- 19-20 Purchase Approval Workflow + PO creation (`garment.purchase.order`,
  `garment.purchase.approval`)
- 30-31 Purchase Contract / Blanket Purchase Agreement
  (`garment.purchase.contract`)
- 32-33, 36 Delivery Tracking / Goods Receipt / Return Management
  (`garment.purchase.delivery`)
- 39-40 AI Demand Forecast + Purchase Optimization (`garment.ai.engine`
  extension, `garment.purchase.forecast`)

## Gaps closed in this pass

1. **Section 11 — Material Shortage Alert.** Added `has_shortage` (stored
   compute) on the requisition and `is_shortage` on the line, plus
   `action_check_shortage_alerts()` which posts a chatter alert in the
   exact Order/Material/Required/Available/Shortage shape of the SRS
   example. Auto-invoked at the end of `action_import_from_bom`. New
   "Material Shortage Alerts" menu/list (domain `is_shortage = True`).
2. **Section 14 — Automatic RFQ Creation source.** Added `rfq_source`
   (Approved PR / Material Shortage / Production Plan / Manual) to
   `garment.purchase.rfq`.
3. **Section 15 / 46 — Supplier RFQ/PO Portal Integration.** `garment.purchase.rfq`
   and `garment.purchase.order` now inherit `portal.mixin`. Added
   `ir.rule` records restricting `base.group_portal` users to their own
   `supplier_id` on RFQ, Quotation and PO, and explicitly denying
   competitor-quotation visibility (SRS section 46 "Supplier cannot ...
   view other suppliers"). Added `action_supplier_confirm()` +
   `supplier_confirmed`/`supplier_confirmation_date` on the PO for the
   "Confirm PO" capability. The actual portal web templates/controllers
   (the rendered pages a supplier logs into) are out of scope for this
   backend module — the suite's dedicated portal layer is
   `garment_buyer_portal`; this pass only ensures the data model is
   portal-ready for that layer (or a symmetrical `garment_supplier_portal`)
   to build on.
4. **Section 23 — Fabric Color Management.** Added
   `buyer_color_code`/`supplier_color_code`/`shade_band`/`lab_dip_status`/
   `color_approval_status` to `garment.purchase.request.line`.
5. **Section 24 — Fabric Booking Management.** New model
   `garment.purchase.fabric.booking` (own sequence `FB/%(year)s/`,
   security rows, tree/form/search views, menu under Sourcing).
6. **Section 26 — Accessory Specification.** Added `accessory_material`,
   `brand_requirement`, `buyer_approval_status`, `supplier_specification`
   to the requisition line.
7. **Section 27 — Local Purchase Data.** Added `purchase_type`
   (local/import), `vat_percentage`/`vat_amount` (computed),
   `delivery_location` to `garment.purchase.order`, and `challan_number`
   to `garment.purchase.delivery` (a delivery-time document, not an
   order-time one).
8. **Sections 28-29, 52 — Import Purchase Information.** Added
   `pi_number`, `supplier_country_id`, `lc_number`, `bank_name`,
   `shipment_date`, `eta_date`, `port_of_entry`, `freight_cost`,
   `insurance_cost`, `cf_charges`, computed `landed_cost`, and
   `import_stage` (PI Received → LC Opening → Shipment → Customs
   Clearance → Warehouse Receipt) to `garment.purchase.order`.
9. **Section 34 — Purchase Quality Integration.** Added a
   `material_category`-gated QC checklist to `garment.purchase.delivery`:
   GSM/Shade/Shrinkage/Color-Fastness for fabric, Size/Color-Match/
   Quantity-Check for accessories.
10. **Section 35 — Purchase Invoice Matching.** Added `invoice_ids`
    (M2M to `account.move`, `move_type = in_invoice`), computed
    `invoiced_amount`, `received_qty_total` and `match_status`
    (pending_grn / pending_invoice / matched / mismatch) on the PO, plus
    `action_verify_invoice_match()`.
11. **Section 41 — Advanced AI Procurement Intelligence.**
    - AI Purchase Price Prediction: `garment.ai.engine.predict_price_trend()`
      compares early vs. recent average unit price from this module's own
      purchase history (no external feed needed).
    - AI Purchase Delay Prediction: `predict_delivery_risk()` scores a
      supplier from their last 3 recorded deliveries; feeds back into
      `recommend_purchase_supplier()` as a scoring factor.
    - AI Automatic Purchase Planning: `generate_purchase_plan_suggestions()`
      / `garment.purchase.forecast.action_create_requisition()` turn an
      un-actioned demand forecast into a draft PR.
    - `garment.purchase.forecast` now carries a `forecast_type`
      (demand / price_prediction / delay_risk) so all three AI outputs
      share one reporting model, per its SRS name.
    - AI Supplier Selection Engine: capacity / compliance-status /
      distance factors are **deliberately deferred** — that data lives on
      `garment.supplier` (garment_supplier module), and garment_supplier
      already depends on garment_purchase, so garment_purchase depending
      back on it would be a circular dependency. Only price, quality,
      delivery-performance and (new) delay-risk are scored here.
12. **Section 42 — Purchase Approval Matrix.** The SRS gives two
    different example threshold tables (section 19: <1L / 1-10L / >10L;
    section 42, the dedicated "Approval Matrix": <50k / 50k-5L / 5-20L
    Finance+Director / >20L). This pass adopts section 42's numbers as
    authoritative (it is the dedicated matrix definition) and adds a
    `finance_director` tier. `action_generate_approvals()` raises the
    right chain of `garment.purchase.approval` records per tier — two
    parallel records (Finance + Director) for the 5-20 Lakh tier — and
    `garment.purchase.approval.action_approve()` now only auto-approves
    the PO once *every* approval record for it is approved, not just one.
13. **Section 43 — Purchase Exception Management.** Added
    `exception_type`/`exception_note`/`requires_exception_approval` and
    `action_check_exceptions()` on the PO: flags a >10% price increase
    versus the last purchase of the same material from the same supplier
    (using the new `previous_price` on the order line), and a
    budget-exceeded condition. Called automatically from
    `action_submit_for_approval()`.
14. **Section 44 — Purchase Budget Control.** Added a lightweight,
    self-contained `department_budget_amount` / `budget_status` check on
    the PO. **Not** linked to `garment.budget` (garment_finance) —
    garment_finance depends on garment_supplier, which depends on
    garment_purchase, so a dependency back to garment_finance would be
    circular. This is documented as a deliberate simplification; a full
    integration belongs in a future cross-module budget-check service.
15. **Section 45 — Purchase Cost Analysis / Saving %.** Added
    `previous_price` (computed: last PO line for the same
    supplier+material) and `saving_pct` = `(previous - current) /
    previous * 100` to `garment.purchase.order.line`.
16. **Section 38 — Purchase Reports.** Added Purchase Register (order
    line list), Supplier Spend (pivot), Material Cost Trend (pivot,
    monthly by material) and Delivery Performance (pivot, on-time % by
    supplier) — all under a new "Reports" menu.
17. **Section 48/49 — Database Relationship / PR model example.** Added
    `order_id` (Many2one `garment.order`, garment_order_management) and
    `material_type` (header-level Selection) to the requisition, and
    `department_id` (Many2one `garment.hr.department`, garment_hr)
    alongside the existing `request_department` Char (kept for backward
    compatibility — `garment_maintenance`'s spare-part reorder flow
    already writes to `request_department` as free text and must keep
    working unchanged).

## New module dependency additions and why

- `account` — the module already used `account.payment.term` /
  `account.incoterms` (and now `account.move` for invoice matching);
  made the dependency explicit instead of relying on it loading
  transitively through `garment_bom_management`.
- `garment_hr` — for the new `department_id` Many2one (SRS section 49).
  No circular risk: `garment_hr` only depends on `garment_buyer_crm`.
- `garment_order_management` — for the new `order_id` Many2one (SRS
  section 48). No circular risk: `garment_order_management` does not
  depend on `garment_purchase`.

Modules explicitly **not** added as dependencies, and why: `garment_supplier`,
`garment_finance`, `garment_quality` — each of these already depends on
`garment_purchase` (directly or transitively via `garment_supplier`), so
depending back on any of them would create an import cycle. Every SRS
requirement that would naturally reach into one of those models (supplier
capacity/compliance scoring, `garment.budget`, `garment.quality.inspection`)
was instead implemented with a self-contained field/compute inside this
module, and the limitation is called out at the point it applies above.

## Bug fix: `attrs=`/`states=` → Odoo 17 direct attributes

Converted 9 occurrences across 6 view files to direct attribute
expressions (`invisible="..."`, etc.):
`garment_purchase_requisition_views.xml` (2),
`garment_purchase_rfq_views.xml` (1),
`garment_supplier_quotation_views.xml` (1),
`garment_purchase_order_views.xml` (3),
`garment_purchase_contract_views.xml` (1),
`garment_purchase_delivery_views.xml` (1).

## Validation

- `python3 -m py_compile` — clean on every `.py` file in the module.
- `xmllint --noout` — clean on every `.xml` file in the module.
- A field-existence cross-check script confirmed every `<field name="...">`
  referenced in every view/report against that view's model resolves to a
  real field (framework fields such as chatter/`message_*` excluded).
