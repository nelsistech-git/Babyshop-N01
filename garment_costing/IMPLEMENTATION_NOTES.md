# Implementation Notes — Garment Costing Management (GAP-UPGRADE pass)

Date: 2026-08-24
Scope: gap-fill of `garment_costing` against `specs_txt/Garment Costing Management System.txt`
(SRS Module 8, Parts 1–3), plus the mandatory `attrs=`/`states=` → Odoo 17 syntax fix.

## SRS sections already implemented before this pass (unchanged)

Sections 6–8 (Costing Master, status workflow, costing types), 9–12 (material cost
read live from BOM), 13–15 (CM / SMV costing), 16 (additional costs), 17 (FOB
formula), 20 (AI cost prediction / optimization / buyer price), 21–22 (revision
history), 23 (supplier price history + recommendation), 25 (variance analysis),
39–41 (4-level approval, cost locking, audit trail via chatter tracking).

## Gaps closed in this pass

1. **§19 Buyer Price Negotiation** — new model `garment.cost.negotiation`
   (`models/garment_cost_negotiation.py`), a `garment.costing.negotiation_ids`
   One2many: negotiation date, submitted/target/negotiated/final price,
   notes, approval status. Tree+form views, stat button on the costing form,
   standalone menu under Review.
2. **§26 Cost Saving Analysis** — `garment.ai.engine.suggest_cost_saving()`
   added (`models/garment_ai_engine.py`): identifies Material Saving
   (cheaper BOM alternative on file), Supplier Saving (cheaper supplier for
   the same material reference in Price History), and Production Saving
   (CM disproportionately high vs material cost) — returns a note plus
   `expected_saving_per_unit` / `annual_saving_estimate`, now stored on
   `garment.costing` and populated by "Run AI Analysis".
3. **§28 Payment Terms Management** — new model `garment.cost.payment.term`
   (LC/TT/DP/DA/Advance, payment %, due date, bank requirement), a
   `payment_term_ids` One2many on the costing so a single costing can split
   payment across several terms (e.g. 30% TT advance + 70% LC).
4. **§29 Incoterms Management** — `incoterm` selection (FOB/CIF/CFR/EXW/FCA),
   `international_freight_cost`, `insurance_cost` and a computed
   `incoterm_price` on `garment.costing` (FOB, or FOB+Freight for CFR, or
   FOB+Freight+Insurance for CIF), folded into `_compute_totals`.
5. **§24 Currency — automatic conversion** — `garment.exchange.rate.get_rate()`
   model method (latest rate on/before a given date) plus a computed
   `fob_price_company_currency` on `garment.costing` that applies it
   ("USD Cost x Exchange Rate = BDT Cost").
6. **§18 Profit Margin formula** — added the actual computed
   `profit_margin_actual_pct` (`Profit Amount / FOB Price x 100`), distinct
   from the input `profit_margin_pct` (which only drives the calculation
   when the margin type is Percentage, not Fixed).
7. **§43 AI Margin Protection** — computed `margin_risk_note`, warns on the
   form (and is filterable in the search view) when the actual margin falls
   below the recommended minimum of 8%.
8. **§43 AI Cost Simulation** ("what happens if fabric price increases
   10%?") — new transient wizard `garment.cost.simulation.wizard`
   (`wizard/`): simulates a % change on material/CM/overhead cost and shows
   the resulting FOB, profit impact, and required price adjustment to
   protect the current margin — read-only, never writes to the costing
   record; a "Create Revision from Simulation" button opens a pre-filled
   Cost Revision for the user to confirm and persist.
9. **§30–33 Dashboards & Reports** — added Cost by Product Category graph,
   Material Cost Distribution (pie), Profit Margin Trend (line-by-month),
   a Profitability Report (list+pivot+graph, colour-coded by margin), and a
   Cost Variance Report (pivot) — all as native Odoo graph/pivot/tree views
   under a new "Reports" menu, consistent with how the rest of the suite
   builds dashboards (no external JS framework).

## Deliberately simplified / deferred

- **§27 Buyer Quotation Management** — the SRS's own §35 DB design lists a
  `garment.quotation` model, but per `MODEL_MAP.md` and the house-style
  cross-module rule, the buyer-facing quotation document already exists as
  `garment.merch.quotation` / `garment.merch.quotation.line` in
  `garment_merchandising`; `garment.costing.quotation_id` already links to
  it. A second quotation model was **not** created here to avoid a second
  place where quotation price/terms live. "Delivery Terms" from that
  section is covered by the new `incoterm` field; "Payment Terms" by the
  new `garment.cost.payment.term` lines.
- **§34 Buyer Quotation PDF** — deferred to `garment_merchandising`, the
  actual owner of the quotation model; only the existing Cost Sheet PDF
  (`report/garment_costing_report.xml`) lives in this module.
- **§21 "New Version" field** — interpreted as the revision's own
  `version_number` (the version being created), so no extra forward-link
  field was added on top of the existing `previous_version_id`.
- **§9.2 Fabric Cost Components / §10 Trim list / §11 Packaging list** —
  itemised fabric/trim/packaging types are owned by the BOM module
  (`garment_bom_management`); this module intentionally reads only the
  aggregated `fabric_cost_total` / `trim_cost_total` / `packaging_cost_total`
  roll-ups from `garment.bom`, per the module's original design note ("one
  place a fabric or trim price lives") — unchanged in this pass.
- No custom OWL/JS dashboard was built for §30–32's "Executive Dashboard" —
  implemented instead as standard Odoo graph/pivot/list actions (bar/pie/
  line charts, profitability & variance reports), which is the idiomatic
  Odoo Community approach and matches how other dashboards in this suite
  are built.

## Cross-module models linked

- `garment.style`, `garment.buyer` (via style), `garment.style.category`,
  `garment.sample`, `garment.bom` (existing, unchanged)
- `garment.merch.quotation` (existing `quotation_id`, unchanged)
- No new cross-module dependencies were added; `depends` in
  `__manifest__.py` is unchanged.

## attrs=/states= → Odoo 17 syntax fix

11 occurrences of the deprecated `attrs="{...}"` syntax were found and
converted to direct attribute expressions (no `states=` usage was found):

- `views/garment_costing_views.xml` — 6 occurrences (button/widget
  `invisible` on `is_locked`, field `invisible` on `profit_margin_type`)
- `views/garment_cm_cost_views.xml` — 4 occurrences (group `invisible` on
  `calculation_mode`)
- `views/garment_cost_revision_views.xml` — 1 occurrence (button
  `invisible` on `approval_status`)

## New files added

```
models/garment_cost_negotiation.py
models/garment_cost_payment_term.py
views/garment_cost_negotiation_views.xml
views/garment_cost_payment_term_views.xml
wizard/__init__.py
wizard/garment_cost_simulation_wizard.py
wizard/garment_cost_simulation_wizard_views.xml
```

All registered in `__manifest__.py` → `data`, `__init__.py` (`from . import
wizard`), `models/__init__.py`, and `security/ir.model.access.csv`.

## Validation

- `python3 -m py_compile` on every `.py` file: **passes, no errors**.
- `xmllint --noout` on every `.xml` file: **passes, no errors**.
