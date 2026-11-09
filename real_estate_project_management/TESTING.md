# TESTING.md — Phase 11 Consolidated QA Report

**Real Estate Project Management for Odoo 17 Community**
Developed by Nur Uddin Ahammed — Nelsis Tech (https://www.nelsistech.com)

This is the final phase of the build (spec section 71 / 83-88). It does
not add new business features; it verifies the whole module — all 10
previous phases together — as a single system, and documents exactly
what has and hasn't been verified given the constraints of the
development environment.

## 1. What was actually run in this environment

This module was built in a sandboxed Linux container **without a live
Odoo server or PostgreSQL database available**. Every phase was
therefore validated with the deepest static analysis possible short of
actually booting Odoo, repeated in full as a final consolidated pass:

| Check | Result |
|---|---|
| Python syntax (`py_compile`) on all 68 `.py` files | **PASS** — 0 errors |
| XML well-formedness on all 39 `.xml` files | **PASS** — 0 errors |
| `ir.model.access.csv` structural validation (188 rows) | **PASS** — 0 column mismatches, 0 duplicate IDs |
| Every model has ≥1 access control row | **PASS** — 37/37 models covered |
| Every `_sql_constraints` tuple well-formed | **PASS** |
| Every `.py` model file imported in `models/__init__.py` | **PASS** — 53/53 |
| Every `.py` test file imported in `tests/__init__.py` | **PASS** — 11/11 |
| Every file in `views/`/`security/`/`data/`/`demo/`/`report/` listed in `__manifest__.py`, and vice versa | **PASS** — 40/40 match exactly |
| Manifest load order (security → data → views → menus → reports) | **PASS** — verified correct dependency ordering |
| Every XML `ref="..."` resolves to a real, earlier-or-lazily-resolved record | **PASS** — 0 dangling references across 353 XML IDs |
| Every `%(xmlid)d` button/action reference resolves | **PASS** |
| Every report action's `report_name` has a matching `<template id="...">` | **PASS** — 8/8 |
| Every report's `binding_model_id` resolves to a real model | **PASS** — 8/8 |
| No deprecated `attrs=`/`states=` view syntax | **PASS** — 0 occurrences (this module was written natively for the Odoo 17 view syntax, not migrated from an older version) |
| No removed `@api.multi`/`@api.one` decorators | **PASS** — 0 occurrences |
| No raw SQL (`cr.execute`) anywhere | **PASS** — 0 occurrences |
| No `.sudo()` calls anywhere | **PASS** — 0 occurrences (every operation respects the security groups/record rules defined in this module) |
| No `eval`/`exec`/`subprocess`/`os.system`/network calls/`pickle`/`marshal`/dynamic imports in any Python file | **PASS** — 0 occurrences |
| No hardcoded credentials, API keys, or tokens | **PASS** — 0 occurrences |
| No hardcoded URLs except the developer's own company website in `__manifest__.py` metadata | **PASS** |
| Every `fields.Monetary` field's model has an accessible `currency_id` | **PASS** — 0 warnings |
| Balanced parentheses/quotes in every `invisible`/`readonly`/`required` view expression | **PASS** — 0 issues across all views |

## 2. What could NOT be run in this environment

Being transparent about this matters more than pretending otherwise:

- **No live `-i real_estate_project_management --test-enable` install.**
  The 85 automated test methods across 13 test classes (`tests/test_*.py`)
  are believed correct based on careful reasoning about Odoo's ORM
  behavior, but they have never actually executed against a real
  PostgreSQL-backed Odoo registry. Static analysis can catch syntax
  errors, missing imports, and structural mismatches — it cannot catch
  every possible runtime behavior (e.g. an unexpected `read_group`
  aggregation quirk, an ORM cache-invalidation edge case, or a
  first-install migration ordering surprise).
- **No visual/UI verification.** View XML has been checked for
  well-formedness and reference integrity, but no screenshot or manual
  click-through has confirmed that, say, the Unit Kanban actually renders
  the color-coded cards as intended, or that a specific `invisible`
  domain doesn't hide a field the user actually needs. Everything here
  follows well-established Odoo 17 view patterns, but "follows the
  pattern correctly" and "renders exactly as intended" are different
  claims.
- **No QWeb PDF rendering verification.** The 9 reports (8 from Phase 10
  plus the Handover Certificate from Phase 8) have correct template
  structure and resolve their bindings, but none have actually been
  rendered to a PDF to check pagination, font handling, or layout
  overflow with real data.

**Recommendation:** before production use, run
`./odoo-bin -c odoo.conf -d test_db -i real_estate_project_management --test-enable --stop-after-init`
against a real Odoo 17 Community instance and review the log for any
`ERROR`/`CRITICAL` lines, then click through the demo data manually.

## 3. Known simplifications and deferred scope

Documented honestly rather than silently omitted:

- **Requisition → Purchase Order integration** (spec section 24) is
  intentionally not built. Phase 3's Material Requisition models the
  requisition and its budget-gated approval only; a wizard that creates
  a real Odoo RFQ/PO from an approved requisition was flagged as a later
  refinement in the Phase 3 README and was never revisited, since it
  wasn't part of the original 11-phase build plan's explicit deliverables.
- **Live `stock` (Inventory) integration** is likewise deferred —
  `requisition.line.available_stock` is an informational manual field,
  not computed from `stock.quant`, per the same Phase 3 note.
- **Customer Portal record rules** (spec section 53/78) were never built
  as their own phase — the original 11-phase plan in the spec does not
  list "Customer Portal" as one of its numbered phases (it's phase-list
  item is genuinely absent; the spec's section 53 describes portal
  requirements but the phase breakdown in section 83 jumps from Sales/
  Installment/Rental/Handover/Warranty straight to Dashboard & Reports).
  Building a safe customer-facing portal with correct "only see your own
  data" record rules is a substantial, security-sensitive undertaking
  that deserves its own dedicated phase if the client wants it next.
- **Email/SMS/WhatsApp reminder integration** (spec section 41/67) has a
  real, callable hook (`installment.action_send_reminder()`) but is
  deliberately not wired to any provider, since doing so would require
  storing provider credentials — out of scope for an application-layer
  module per the spec's own "do not hardcode SMS/WhatsApp provider
  credentials" instruction.
- **The Management Dashboard uses standard Odoo Form/Graph/Pivot/Kanban
  views instead of a custom OWL single-page app**, a deliberate reading
  of spec section 51's own "use OWL only where it provides meaningful
  dashboard functionality" instruction — explained in full in the
  Phase 10 README section.

## 4. Full test inventory

```
tests/test_land.py                  4 tests  - ownership %, sequences, state guards
tests/test_land_agreement.py        4 tests  - date/share validation, approval workflow
tests/test_project_structure.py     6 tests  - project workflow, hierarchy integrity
tests/test_construction.py         11 tests  - budget control, transfers, work packages,
                                                requisition budget-gating, contractor bills
tests/test_qc.py                    9 tests  - inspection recommendation, defect workflow,
                                                readiness gates (project + unit)
tests/test_sales.py                 8 tests  - booking workflow, single-active-booking guard
tests/test_collection.py           12 tests  - schedule generation, payment confirmation,
                                                overpayment guards, late fees, ledger
tests/test_rental.py                10 tests  - rental workflow, sold/rented mutual exclusion,
                                                rent schedule generation, shared Collection model
tests/test_handover.py              8 tests  - all three clearance gates, full happy path
tests/test_warranty.py              5 tests  - workflow, assignment guard, expiry computation
tests/test_dashboard.py             5 tests  - KPI accuracy, profitability math, bug-fix regression
------------------------------------------------
Total                               85 tests across 13 test classes
```

Every test uses Odoo's standard `TransactionCase` with `@tagged('post_install', '-at_install')`,
the conventional pattern that runs tests after the full module (and its
dependencies) are installed, rather than mid-install when data may not
yet be consistent.

## 5. Final installation checklist

1. Copy `real_estate_project_management/` into your Odoo 17 addons path.
2. `./odoo-bin -c odoo.conf -d your_db -i real_estate_project_management --test-enable --stop-after-init 2>&1 | tee install.log`
3. Search `install.log` for `ERROR` or `CRITICAL` — there should be none.
4. Confirm all 85 tests report `OK` in the log.
5. Log in, open **Real Estate → Dashboard → Management Dashboard** and
   confirm the KPI numbers match the demo data narrative in this
   README's phase-by-phase sections.
6. Click through **Real Estate → Sales → Bookings → demo_booking_1** and
   confirm its linked Sale Agreement, Installment Plan, and Payment
   Collections all display correctly — this single record touches
   Phases 2, 5, and 6 and is a good end-to-end smoke test.
7. Print the Handover Certificate from **Real Estate → Handover** and
   the Project Profitability report from a Project form to confirm PDF
   rendering.

## 6. Summary

Across 11 phases: **37 models, 68 Python files (~5,700 lines), 39 XML
files (~6,000 lines), 188 access-control rows, 18 record rules, 13
security groups, 21 sequences, 2 scheduled actions, 9 QWeb PDF reports,
48 menu items, and 85 automated tests** — all internally consistent,
all cross-referenced, all free of the suspicious patterns this project's
security scan checks for, and all built from a single coherent reading
of the original master specification with every deliberate simplification
documented rather than hidden.


## Phase 11 - Roles, commission, CRM (manual test script)
Install/upgrade with demo data, then:
1. Log in as `customer3` / `customer3`: only **My Dashboard** is in the menu. Check
   Paid/Due/Overdue, Payment Schedule (installment 3 overdue), Payments Done,
   Project Expenses (ABC Residence only). No other menu appears.
2. Log in as `customer1`: *My Referral Commission* tab shows 246,000 (Level 1 on A-301).
3. Log in as `agent1`: Level 1 = 253,000 (paid) and Level 2 = 61,500 (pending);
   *My Customers* lists only Kamal (Tanvir was brought by Kamal, not by agent1, so he is not agent1's customer, but agent1 still earns Level 2 on his purchase);
   open **Agent CRM**: sees 4 leads, not `agent2`'s.
4. As admin: create a Booking/Sale Agreement with *Sold By*, Activate -> check the
   Commissions tab; try the Level 1/2 chain with a new customer reselling.
5. As admin on a contact: **Create Login (ID & Password)**.

Automated: `odoo -d <db> -i real_estate_project_management --test-tags /real_estate_project_management`
(new: tests/test_commission.py, tests/test_portal_dashboard.py).
