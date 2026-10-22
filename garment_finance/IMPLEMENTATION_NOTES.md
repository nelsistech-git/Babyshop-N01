# garment_finance — Implementation Notes (GAP-UPGRADE Pass)

This pass upgraded the already-working `garment_finance` module against
the two overlapping Finance SRS documents (Module 20 "Finance &
Accounting Management System" and Module 37 "Garment Finance, Accounting
& Commercial Management System", the later/deeper document). It closed
five functional gaps, fixed a view-syntax bug, and left every existing
model, field and workflow in place.

## Avoiding conflict with `garment_commercial_export`

Before touching any file, `garment_commercial_export/models/` was read in
full. That module already `_inherit`s three of this module's models:

- `garment.lc` — adds `lc_type` (Master/Export/Back-to-Back/Sight/
  Usance), `master_lc_id`/`btb_lc_ids`, `supplier_id`,
  `issuing_bank_id`/`advising_bank_id`/`buyer_bank_id`,
  `amendment_ids` (structured `garment.lc.amendment`),
  `export_documentation_ids`, `import_permission_ids`, and the
  `utilized_amount`/`balance_amount`/`utilization_pct` LC-utilization
  computation.
- `garment.export.documentation` — adds extra `document_type` values
  (EXP Form Copy, GSP Certificate, etc.), `po_number`, `hs_code_id`,
  `buyer_document_shared`, `line_ids`/`carton_ids`, and AI document
  verification.
- `garment.receivable` — adds `exp_form_id`, `realizing_bank_id`,
  `realization_date`, `bb_reporting_status` (Bangladesh Bank reporting).

**None of those fields, methods or the `amendment_count`/
`action_record_amendment` mechanism on `garment.lc` were touched, renamed
or removed.** This pass only *added* new fields/methods to
`garment.lc` — it added none; the LC/export-doc/receivable models
themselves were left byte-for-byte unchanged in this pass, since
`garment_commercial_export` already owns their extension surface. New
functionality that could have been tempting to bolt onto `garment.lc` or
`garment.export.documentation` (e.g. a payment-approval angle) was
instead built as new, separate models (`garment.payment.approval.rule`,
`garment.bank.statement.line`, `garment.finance.statement`,
`garment.cash.flow.forecast`) that reference the existing models via
Many2one/search rather than inheriting or duplicating them. No new
`document_type` / `lc_type` selection values were added, and no
export-documentation or customs functionality was recreated — that stays
entirely owned by `garment_commercial_export`.

## Gaps closed

1. **Bank Reconciliation matching workflow** (SRS §19 Mod 20 / §17 Mod
   37 — "Bank Statement → Import → Match Transactions → Reconcile →
   Close"). Previously `garment.bank.transaction.action_reconcile()` just
   flipped a status flag with nothing to reconcile against. Added:
   - New model `garment.bank.statement.line` (imported/entered bank
     statement lines) with `action_auto_match()` — matches an unmatched
     statement line to exactly one unreconciled ERP transaction on the
     same bank account, same amount, within 5 days, and links both sides.
   - `garment.bank.transaction.reconciliation_status` extended with
     `matched` and `closed` states (was `unreconciled`/`reconciled`/
     `disputed`); `action_reconcile()` now requires the `matched` state
     first; added `action_close()`, `action_mark_disputed()`,
     `action_reset_to_unreconciled()`, and a `reconciliation_difference`
     compute field.
   - New form view for `garment.bank.transaction` (there was previously
     only a tree view) with the full statusbar/button workflow.

2. **Financial Statement / simplified P&L snapshot** (SRS §41-42, 46-47
   Mod 37; §6, 41, 46-47 Mod 20). New model `garment.finance.statement`:
   a point-in-time snapshot (Revenue/Cost/Gross & Net Profit/margins,
   Cash & Bank Balance, Receivable/Payable, Working Capital, Budget
   Allocated/Actual/Variance%) computed entirely from this module's own
   Receivable/Expense/Payment/BankAccount/Budget records via
   `action_generate()`. **This deliberately does not touch or replace
   Odoo Accounting's General Ledger, Trial Balance, statutory Balance
   Sheet or P&L Report** — the manifest's original scope decision (no
   double-entry bookkeeping reinvention) is preserved and explicitly
   documented in the model's docstring; VAT/Tax reporting and Fixed
   Asset/Depreciation were likewise left to the standard `account`
   module, for the same reason.

3. **Cash Flow Forecasting + AI Cash Flow Prediction** (SRS §31-32 Mod
   20; §18 Mod 37; AI §45 Mod 20 / §52 Mod 37). New model
   `garment.cash.flow.forecast`: opening balance (live bank balances),
   expected inflow (receivables due in the period), expected outflow
   (payments due + pending/approved expenses in the period), net cash and
   projected closing balance, plus `action_run_ai_analysis()` calling a
   new `garment.ai.engine.predict_cash_flow_risk()` method (HIGH/MEDIUM/
   LOW risk with reasons and a collection/payment-deferral recommendation
   — mirrors the SRS's own worked example). This is explicitly a
   forward-looking forecast, not the historical Operating/Investing/
   Financing Cash Flow *Statement*, which again stays with standard
   Accounting.

4. **Budget vs Actual Variance** (SRS §30 Mod 20 "Variance Analysis";
   §46 Mod 37 covers order/style-level cost variance, already owned by
   `garment_costing.garment.cost.variance` — not duplicated here). Added
   `variance_amount` (actual − budgeted), `variance_pct`, and a
   free-text `variance_reason` field to the existing `garment.budget`
   model, alongside the pre-existing `utilization_pct`/
   `remaining_amount`.

5. **Payment Approval Matrix / Financial Approval Workflow** (SRS §13 &
   50 Mod 20 — Supplier Invoice → Verification → Approval → Payment
   Request → Bank Payment → Reconciliation; §48 Mod 37). New model
   `garment.payment.approval.rule` — an amount-banded routing table
   (`min_amount`/`max_amount` → required `res.groups`), seeded with two
   default bands (Finance Manager up to ৳5,00,000; Finance Director
   above). `garment.payment` gained `approval_status` (draft → pending
   verification → pending approval → approved/rejected) with
   `action_submit_for_verification()`/`action_verify()`/
   `action_approve()` (raises if the current user isn't in the matrix's
   required group)/`action_reject()`/`action_reset_to_draft()`, plus
   verified/approved-by + timestamp fields. `garment.expense.
   action_approve()` was updated to run the same matrix check (the SRS
   approval workflow applies to both AP payments and factory expenses)
   with no new fields needed there beyond a computed
   `required_approver_group_id`.

## Bug fix: `attrs=`/`states=` → Odoo 17 direct attributes

Grepped `views/*.xml` for the deprecated syntax and converted all 3
instances found:

- `views/garment_expense_views.xml` — Approve button:
  `attrs="{'invisible': [('status', '=', 'approved')]}"` →
  `invisible="status == 'approved'"`.
- `views/garment_budget_views.xml` — Move to Next Stage button:
  `attrs="{'invisible': [('status', '=', 'closed')]}"` →
  `invisible="status == 'closed'"`.
- `views/garment_lc_views.xml` — Move to Next Stage button:
  `attrs="{'invisible': [('workflow_stage', '=', 'payment_received')]}"`
  → `invisible="workflow_stage == 'payment_received'"`.

All newly-written view XML in this pass uses direct attribute
expressions from the start; a final `grep -rn "attrs=\|states="` over the
whole module returns zero matches.

## New files

- `models/garment_bank_statement_line.py`, `models/
  garment_payment_approval_rule.py`, `models/garment_finance_statement.py`,
  `models/garment_cash_flow_forecast.py`
- `views/garment_bank_statement_line_views.xml`, `views/
  garment_payment_approval_rule_views.xml`, `views/
  garment_finance_statement_views.xml`, `views/
  garment_cash_flow_forecast_views.xml`
- `data/garment_payment_approval_rule_data.xml` (2 seed matrix rules)
- All four new models: security access rows added (base.group_user
  read-only, Finance Officer read/write/create, Finance Manager full),
  and menu items wired under Banking / a new "Financial Reports" submenu
  / Configuration so every new action is reachable.
- `__manifest__.py`'s `data` list and description updated accordingly.

## Deliberately not done (and why)

- VAT/Tax Management (SRS §37-40 Mod 20, §39 Mod 37) and Fixed Asset /
  Depreciation Management (SRS §33-36 Mod 20, §50-51 Mod 37): both are
  standard, audited Odoo Accounting (`account.tax`, `account.asset` via
  the Accounting app) territory, consistent with this module's existing
  "DELIBERATE SCOPE DECISION" not to reinvent bookkeeping. Adding
  garment-specific wrappers for these was out of scope for this pass.
- Multi-Company Accounting (SRS §6 Mod 37): most models here already
  carry (or inherit) `company_id` where it existed before this pass;
  extending `company_id` to every remaining model was left out to keep
  this pass focused on the five functional gaps and the view-syntax bug
  called out for this task.

## Validation

- `python3 -m py_compile` — every `.py` file in the module: **all pass**.
- `xmllint --noout` — every `.xml` file in the module: **all pass**.
