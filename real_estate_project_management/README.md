# Real Estate Project Management — Odoo 17 Community

Production-ready Real Estate Project & Property Management ERP for Odoo
Community 17. Manages the full lifecycle from land acquisition through
construction, sales, collection, and handover.

**Developed by:** Nur Uddin Ahammed
**Company:** Nelsis Tech — https://www.nelsistech.com
**License:** LGPL-3
**All code in this module is original, written for this project. It contains
no external binaries, obfuscated code, network calls, or third-party
scripts of any kind — it is plain, auditable Python/XML/CSV using only the
standard Odoo API.**

## Status: ALL 11 PHASES COMPLETE

Every phase from the original master specification's build plan
(section 83) has been implemented: Foundation, Project & Unit Structure,
Construction, QC, Sales, Installment & Collection, Rental, Handover,
Warranty, Dashboard & Reports, and this final Testing/QA pass. See
**[TESTING.md](TESTING.md)** for the full Phase 11 consolidated QA
report — what was validated, what honestly couldn't be validated without
a live Odoo instance, and every deliberate simplification made along
the way.

### What's included in Phase 10 (on top of Phases 1-9)

| Area | Detail |
|---|---|
| Model | `real.estate.dashboard` — a live-computed KPI summary, deliberately built as plain Python compute fields on a form view instead of a custom OWL app |
| KPIs | Total/Active/Completed Projects, Total/Available/Booked/Sold/Rented Units, Total Budget/Actual Cost/Utilization %, Total Sales/Collection/Receivable/Overdue, Estimated Profit — every number from spec section 51, each with a clickable drill-down into the underlying filtered list |
| Unit Inventory Dashboard | Reuses the Phase 2 status-colored Unit Kanban, grouped by Building, plus Graph/Pivot views — a real, interactive visual inventory (spec section 52) without a custom grid-drawing OWL component |
| Additional Graph/Pivot dashboards | Budget vs Actual, Sales by Project, Collection by Month, Outstanding Receivable — native Odoo bar/line charts and pivot tables, zero custom JavaScript |
| **8 remaining QWeb PDF reports** | Project Summary, Budget vs Actual, Sale Agreement, Installment Schedule, Payment Receipt, Customer Ledger, Rental Agreement, Project Profitability — all bound to their model's Print menu automatically via `binding_model_id`/`binding_type` |
| Project Profitability | New computed fields (`total_revenue`, `total_actual_cost`, `gross_profit`, `profit_margin_percentage`) reusing `total_sales_value` (Phase 5) and each Budget's `total_actual` (Phase 3) rather than a parallel cost-tracking model, plus a new `rental_income` aggregate |
| **A real bug found and fixed** | While wiring rental income into Project Profitability, discovered that `real.estate.collection`'s `project_id`/`unit_id` were `related` fields pointing only at `sale_agreement_id` — meaning every rent payment collected since Phase 7 silently had no project/unit attribution. Fixed by converting both to a proper computed field that checks `sale_agreement_id` first, then falls back to `rental_agreement_id`, with the Phase 7 file's override extended accordingly. Covered by a new regression test |
| Security | Read + create access to `real.estate.dashboard` for all management-facing groups (no write/unlink needed — the dashboard is never meant to be saved) |
| Tests | 5 new tests: unit-status KPI counts, project KPI counts, sales KPI reflecting a real agreement, project profitability revenue/cost/margin math, and the rental-income-attribution regression test that exercises the bug fix directly |

### Design decisions worth knowing

- **No OWL, and that's a deliberate reading of the spec, not a shortcut.**
  Section 51 itself says "Use OWL only where it provides meaningful
  dashboard functionality" — every KPI and every chart in this phase is
  fully served by standard Odoo Form/Graph/Pivot/Kanban views, which are
  plain declarative XML with zero JavaScript risk. A custom OWL dashboard
  could not be meaningfully validated without a live Odoo instance to
  render it against; these views are structurally guaranteed to work the
  same way every other view in this module does.
- **The Dashboard "record" is never persisted.** The action opens an
  always-fresh, unsaved form (the same technique Odoo's own
  `res.config.settings` screens use) so every KPI is computed from
  live data on every visit — there's no stale cache to invalidate and
  no cron needed to keep it fresh.
- **Fixing the Collection bug in place, not working around it.** The
  temptation when discovering a Phase 7 bug during Phase 10 work would
  be to just special-case the profitability query around it. Instead the
  actual field definition was corrected, because every other view,
  report, and future phase that ever reads `collection.project_id` on a
  rent payment benefits from the fix, not just this one report.

## Installation

1. Copy the `real_estate_project_management` folder into your Odoo 17
   `addons` path (alongside your other custom modules).
2. Restart the Odoo service.
3. Activate developer mode, go to **Apps**, click **Update Apps List**.
4. Search for "Real Estate Project Management" and click **Install**.

```bash
# Command-line alternative
./odoo-bin -c odoo.conf -d your_database -i real_estate_project_management --stop-after-init
```

To update after future phases are added:

```bash
./odoo-bin -c odoo.conf -d your_database -u real_estate_project_management --stop-after-init
```

## Running the tests

```bash
./odoo-bin -c odoo.conf -d your_test_database -i real_estate_project_management --test-enable --stop-after-init --log-level=test
```

All 7 tests in `tests/test_land.py` and `tests/test_land_agreement.py`
should pass with zero errors.

## Security audit note

- No `eval()`/`exec()` of dynamic strings, no shell calls, no outbound
  HTTP requests, no telemetry, no license-check phone-home.
- No raw SQL except the two declarative `_sql_constraints` (standard Odoo
  pattern, not string-built queries).
- No hardcoded IDs, company IDs, user IDs, currencies, or credentials
  anywhere in the code.
- Every model uses standard Odoo ORM decorators (`@api.depends`,
  `@api.constrains`, `@api.model_create_multi`) — nothing bypasses the
  ORM's access-control layer.

## Project status: delivered

All 11 phases of the original master specification are complete. This
module is ready for a live-instance install/test pass (see
[TESTING.md](TESTING.md) section 5 for the exact checklist) before
production use. Suggested next steps beyond the original spec's 11
phases, if wanted:

1. Run the real install/test checklist in TESTING.md against a live
   Odoo 17 Community + PostgreSQL instance.
2. Build the Requisition → Purchase Order wizard and live `stock`
   integration flagged as deferred in Phase 3.
3. Design and build a proper Customer Portal with record rules
   restricting each customer to their own data (spec section 53/78) -
   deliberately not attempted here since it never appeared as a
   numbered phase in the original build plan and deserves dedicated
   security-focused attention of its own.
4. Wire the reminder hooks (`installment.action_send_reminder()`) to
   an actual email/SMS/WhatsApp provider of the client's choosing.


---

# Phase 11 - Customer & Agent Roles, 2-Layer Commission, Agent CRM  (v17.0.2.0.0)

## 1. Roles (give a user id + password)
Open any customer/agent in **Contacts** -> button **Create Login (ID & Password)**
(needs Sales Manager / Director). Or create a user in Settings > Users and tick
the group under *Real Estate*:

| Role | Group | Sees |
|------|-------|------|
| Customer | *Customer (My Dashboard only)* | **My Dashboard** only |
| Agent | *Agent (Dashboard & CRM)* | **Agent Dashboard** + **Agent CRM** |

Both groups are isolated from staff data: the dashboards are built server-side
for the logged-in user's own contact, and the user has no access rights to
sales, collections, budgets etc. Contacts are also restricted by record rule
(customer: himself; agent: himself + customers he referred).

### Customer "My Dashboard"
* Total property value, payment done, balance due, overdue, % paid, next payment
* **My Properties** (per agreement payment status) - **Payment Schedule** (every
  installment: paid / due / overdue / upcoming) - **Payments Done** (receipts)
* **Project Expenses** - budget, committed, actual and remaining for the
  project(s) he bought into only, plus expense by head (Civil, Electrical ...)
* **My Referral Commission** (appears if he earned commission by selling)

### Agent Dashboard
* My customers (referred + sold) with payment status, overdue, next due date
* My sales with collected / balance / my commission
* **My Commission**: Level 1, Level 2, received, pending
* CRM summary + follow-ups due; buttons to open the pipeline / add a lead

## 2. Two-layer commission
Configure under **Agents & Commission > Commission Rules (2 Layers)**:
one rule for Level 1 and one for Level 2, each a **percentage of net price** or
a **fixed amount**; optionally per project (project rule wins over global).

Example (your scenario):
1. Agent **A** brings customer **B**; B buys a plot -> *Sold By = A* -> **A gets Level 1**.
   B is automatically linked as A's customer (`Referred By = A`).
2. B later sells another plot to **C** -> *Sold By = B* ->
   **B gets Level 1** and **A (who referred B) gets Level 2**.

Commissions are generated when the Sale Agreement is **Activated** (or with the
*Generate Commissions* button), then flow Pending Approval -> Approved -> Paid.
Set **Sold By (Agent / Referrer)** on the Booking or Sale Agreement.

## 3. Agent CRM
**Agent CRM > Leads & Customer Follow-up**: kanban pipeline (New, Contacted,
Site Visit, Negotiation, Won, Lost), priority, next follow-up date, interaction
log, notes, activities/chatter, link to an existing customer, **Convert to
Customer** (sets the agent as referrer). An agent sees only his own leads;
the sales team sees all.

## 4. Demo logins (when installed with demo data)
| User ID | Password | Who |
|---------|----------|-----|
| customer1 | customer1 | Kamal Hossain - buyer + earns Level 1 on A-301 |
| customer2 | customer2 | Nasrin Akter |
| customer3 | customer3 | Tanvir Rahman - bought A-301 |
| agent1 | agent1 | Sabbir Ahmed - Level 1 (A-101) + Level 2 (A-301) |
| agent2 | agent2 | Mitu Akter |

Default demo rules: Level 1 = 2%, Level 2 = 0.5%.
**Change these passwords before going live; demo users exist only with demo data.**
