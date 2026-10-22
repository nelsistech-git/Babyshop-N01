# garment_commercial_export — Implementation Notes

Module 18 of the Smart Complete Garment Software suite, built from
`specs_txt/Commercial & Export Management System.txt` (Parts 1-3).
Depends on `garment_finance` (Module 13) and `garment_logistics`
(Module 12) only, per the build brief — every other existing-module
model this SRS touches (`garment.buyer`, `garment.style`,
`garment.supplier`, `garment.material`, `garment.bank.account`, …) is
reached transitively through those two dependencies, the same pattern
`garment_finance` itself already uses for `garment.merch.order
.confirmation`.

## Relationship to garment_finance's existing LC / export-document models

`garment_finance` already owns the two models this SRS's DB design table
(section 46) is built around: `garment.lc` and
`garment.export.documentation`. This module does **not** duplicate
either one — it extends both with `_inherit`, plus builds the deeper
customs/bond/incentive layer the SRS wants that `garment_finance`
never claimed.

| SRS Model (section 46/47) | Handling in this module |
|---|---|
| `garment.master.lc` / Master, Export, Back-to-Back, Sight, Usance LC (sections 11-13, 16-18) | **Extends** `garment_finance.garment.lc` (`garment_lc_export.py`) — adds `lc_type`, `master_lc_id` self-reference for BTB, `supplier_id`, separate `issuing_bank_id`/`advising_bank_id`/`buyer_bank_id`, and live `utilized_amount`/`balance_amount`/`utilization_pct` computed from the LC's linked export documents (Master/Export LC) or import permissions (BTB LC). No new LC model. |
| LC Amendment (section 14) | **New** `garment.lc.amendment` (child of `garment.lc`) — `garment_finance`'s `garment.lc` only kept a bare `amendment_count` integer; this gives it the structured old-value/new-value/reason/approval record and keeps that counter in sync. |
| `garment.export.document` / Export Document Master (sections 21-24) | **Extends** `garment_finance.garment.export.documentation` (`garment_export_documentation_export.py`) — adds more `document_type` options (GSP/Inspection/Insurance/Beneficiary Certificate/EXP copy), an HS Code link, buyer-portal sharing flag, and two new child line models: `garment.export.doc.line` (Commercial Invoice product lines) and `garment.export.doc.carton` (Packing List carton detail). No new "export document" or "commercial invoice" model — Certificate of Origin was already a `document_type` value in `garment_finance`'s model and is reused as-is. |
| `garment.exp.form` (section 25) | **New** — the SRS gives EXP its own Commercial Officer → Bank Verification → EXP Approval → Shipment workflow, distinct from `garment.export.documentation`'s simple draft/issued/submitted/accepted lifecycle, so it is a dedicated model rather than another `document_type` value. Links to a `garment.export.documentation` invoice and a `garment.shipment`. |
| `garment.import.permission` (IP, section 26) | **New**. `import_category` covers the Import Material Tracking list from section 19 (fabric/accessories/chemical/spare parts/machinery/raw material) as one Selection field instead of five separate models. Links to a Back-to-Back `garment.lc` (`lc_type = 'back_to_back'`). |
| `garment.utilization.permission` (UP, section 27) | **New**, modeled as `garment.utilization.declaration` — Bangladesh customs practice uses "Utilization Declaration (UD)" for this same bonded-warehouse consumption document; the build brief also names it "UD". Field names (imported/consumed/remaining quantity, export reference) follow the SRS's UP field list exactly. |
| `garment.bond.register` (section 28) | **New**, plus a new `garment.bond.license` parent the SRS's Bond Management System narrative describes (Bond License) but the DB table omits — the register needs a licence to belong to. |
| Customs Documentation / HS Code (sections 29-30) | **New** `garment.customs.document` (Bill of Entry/Export, Customs Declaration) and `garment.hs.code` master. |
| `garment.export.payment` / Bangladesh Bank Reporting (sections 32-33) | **Not duplicated.** `garment_finance.garment.receivable` already tracks buyer/invoice/amount/received/outstanding/aging for exactly this. `garment_receivable_export.py` extends it with `exp_form_id`, `realizing_bank_id`, `realization_date` and `bb_reporting_status` for the central-bank reporting angle the SRS adds on top. |
| Export Incentive (section 34) | **New** `garment.export.incentive` — claim/approval/received tracking against a `garment.export.documentation` export reference, with `claim_amount` auto-computed from `export_value * incentive_rate` when a rate is set. |
| Commercial Document Checklist / buyer-specific requirements (section 20) | **New** `garment.commercial.doc.requirement` (buyer × document type × mandatory) — feeds the Shipment Readiness check below. |
| Shipment Readiness Dashboard (section 43) | `garment_shipment_export.py` extends `garment_logistics.garment.shipment` with a rule-based `commercial_readiness` compute that checks the shipment's export documents / EXP form / B/L against the buyer's `garment.commercial.doc.requirement` checklist. Production % and Quality approval readiness are intentionally left to `garment_production`/`garment_quality` — out of this module's two-dependency scope — so only the commercial-document leg is checked here. |
| AI LC Risk Prediction (section 38) | `garment_finance` already ships `predict_lc_realization_risk` (per-LC). This module adds the buyer-level companion, `predict_buyer_commercial_risk` (buyer risk rating, overdue receivables, country watch-list, credit limit breach), surfaced via a new "Run AI Commercial Risk Analysis" button on `garment.buyer` (`garment_buyer_export.py`). |
| AI Shipment Delay Prediction (section 39) | Already implemented on `garment_logistics.garment.shipment` (`predict_shipment_delay`) — **not duplicated**. |
| AI Commercial Document Verification (section 40) | **New** `verify_commercial_documents` on the shared `garment.ai.engine`, checking missing HS Code/PO, invoice-line vs total mismatch, carton-count vs total-cartons mismatch, LC-vs-invoice value mismatch, and missing attachment. Exposed as an "AI Document Verification" page + button on `garment.export.documentation`. |

## Deliberately not modeled

* **Proforma Invoice** (`garment.proforma.invoice`, sections 9-10). This
  is functionally the pre-LC commercial quotation, and `garment
  _merchandising.garment.merch.quotation` (buyer/style/BOM cost
  sheet/currency/Incoterms/payment terms/total value/status workflow)
  already covers that ground. Adding a competing PI model would either
  duplicate it or require a third module dependency
  (`garment_merchandising`) beyond the two named in the build brief, so
  it is left to that existing model. `garment.lc` (via `garment_finance`)
  already carries `order_confirmation_id` forward into this module's LC
  extension, so the PI → LC Opening chain from section 10 is not broken,
  just not re-modeled here.
* **Export Order** (`garment.export.order`, section 48) — `garment
  .order` (`garment_order_management`) is already the real Sales/Export
  Order (buyer PO, style, quantity, value, shipment date, HS code, port
  of loading/destination, shipment mode, state) and is the closer match
  than building a second, thinner order model in this module.
* **Commercial Approval Workflow** as a standalone model (section 35) —
  implemented as `Selection` state fields with `tracking=True` and a
  statusbar directly on `garment.bond.license`, `garment.exp.form`, and
  `garment.export.incentive`, consistent with how `garment.lc`'s own
  workflow is modeled in `garment_finance`, rather than a generic
  cross-model approval-log table.
* **Commercial Calendar** (section 36) — no dedicated calendar model;
  `garment.bond.license.expiry_date`/`days_to_expiry`, `garment.lc
  .expiry_date` (existing) and `garment.exp.form`/`garment.export
  .incentive` dates are all standard `Date`/`Datetime` fields, so Odoo's
  built-in calendar/activity views already work against them without a
  dedicated aggregator model.

## Models added

`garment.hs.code`, `garment.bond.license`, `garment.bond.register`,
`garment.import.permission`, `garment.utilization.declaration`,
`garment.customs.document`, `garment.export.incentive`,
`garment.commercial.doc.requirement`, `garment.lc.amendment`,
`garment.export.doc.line`, `garment.export.doc.carton`,
`garment.exp.form` (12 new models) — plus `_inherit` extensions on
`garment.lc`, `garment.export.documentation`, `garment.receivable`,
`garment.shipment`, `garment.buyer` and the shared `garment.ai.engine`
(no new models, existing ones deepened).

## Validation

* `python3 -m py_compile` — clean on every `.py` file in the module.
* `xmllint --noout` — clean on every `.xml` file in the module.
* Every new model has an `ir.model.access.csv` row for `base.group_user`
  (read-only) and at least one role-specific group; extended existing
  models rely on their origin module's access rows (no new fields
  require new access rows).
* Manifest `data` list cross-checked against the files on disk: every
  listed file exists, and no created `.xml`/`.csv` file is left
  unreferenced.
