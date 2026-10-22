# garment_hr — Implementation Notes (Gap-Upgrade Pass)

This pass upgraded the already-working `garment_hr` module against both source SRS
documents (HRM Module 17, and the deeper Module 36 "Garment HR, Payroll & Workforce
Management System"), added the Bangladesh RMG payroll logic the module's own summary
already promised but didn't yet deliver, and converted every remaining `attrs=`/`states=`
view expression to Odoo 17 direct attribute syntax.

## Bug fixed: attrs=/states= (Odoo 17 removed syntax)

6 instances converted to direct attribute expressions, across 4 files:
- `views/garment_hr_payroll_views.xml` — 2 (Process / Mark Paid button visibility)
- `views/garment_hr_leave_views.xml` — 2 (Submit / Approve button visibility)
- `views/garment_hr_promotion_views.xml` — 1 (Approve button visibility)
- `views/garment_hr_candidate_views.xml` — 1 (Convert to Employee button visibility)

`grep -rn 'attrs=\|states='` across `views/` and `report/` now returns nothing.

## Bangladesh RMG payroll logic added (the module's own headline promise)

This was the biggest real gap: the original `garment.hr.payroll` had OT-multiplier and
PF-deduction *fields* but no wage-board grade table to calculate from, no gratuity at
all, and no employer-side PF. Closed with:

- **`garment.hr.salary.structure`** (new model) — the actual Wage-Board Grade table
  (SRS §12 "Employee Grade Management" / §34 "Salary Structure Management" / §33
  "Bangladesh Garment Payroll Rules — Minimum Wage Structure"): Basic/House Rent/
  Medical/Food/Transport per grade, flaggable as an official Wage-Board grade.
  `garment.hr.designation` now links to it via `salary_structure_id`.
- **Payroll `action_pull_salary_structure()`** — one-click pulls Basic/HRA/Medical/
  Food/Transport from the employee's designation grade.
- **`is_below_minimum_wage`** compute on payroll — flags a payslip whose Basic Salary
  undercuts its wage-board grade's Basic Salary (a real compliance signal SRS §33
  calls for).
- **OT at 2x** — already present as a default multiplier; now also auto-pullable from
  real Attendance records via `action_pull_attendance()` (which also fills
  Worked/Absent Days and Total Late Minutes for the period) instead of only manual entry.
- **Festival Bonus / Attendance Bonus / Production Incentive** — previously a single
  `bonus_type`/`bonus_amount` pair that could only represent one bonus at a time. Now
  itemised via two new models, **`garment.hr.bonus`** (Festival/Performance/Attendance/
  Production, with a "Suggest Amount = 1 Month Basic" helper for Festival Bonus) and
  **`garment.hr.incentive`** (Extra Production × Rate, per the SRS's own formula),
  both pullable into a payslip via `action_pull_bonuses_and_incentives()`. The old
  `bonus_type`/`bonus_amount` fields are kept as an "Other Bonus" catch-all so no data
  is lost.
- **Provident Fund** — employee deduction already existed; added
  `provident_fund_employer_contribution` (informational, matched employer share; not
  subtracted from Net Salary, since it isn't the employee's money).
- **Gratuity** — added `gratuity_accrual` on the payslip (a monthly provision estimate,
  informational) and full gratuity **payout** logic on the new `garment.hr.exit` model
  (see below), using the common Bangladesh RMG practice of "30 days' wages per
  completed year of service" (`gratuity_days_per_year`, editable per record — exact
  entitlement varies by service length band and company policy, so this is left
  configurable rather than hard-coded as a single statutory constant).
- **Payroll workflow** now matches SRS §34 exactly: Draft → HR Verified → Approved →
  Processed → Bank Transfer Initiated → Paid (previously only Draft → Processed →
  Bank Transfer → Paid, missing the explicit HR Verification / Payroll Approval
  steps). Existing `action_process`/`action_mark_paid` and their stored values are
  unchanged, so no existing payslip data breaks.

## Other genuine SRS gaps closed

- **Shift Management (SRS §25 / Module 36 §24)** — entirely missing before. Added
  `garment.hr.shift` (General/Morning/Evening/Night/Rotational/Overtime, with Break
  Time and Grace Period) and `garment.hr.shift.assignment` (Worker Shift Assignment,
  Module 36 §25 — also doubles as a simplified roster: see "Deferred" below).
  Attendance now has a `shift_id`, pulls Scheduled Start/End and Grace Period from it,
  and the Late/Present split now actually respects the Grace Period (previously any
  late arrival at all flipped status to Late, ignoring the shift's own configured
  grace window — a real bug against the Attendance Rule Engine spec in SRS §24).
  Attendance also gained `is_holiday`/`is_weekly_off` and matching status values —
  the Attendance Rule Engine's own SRS example lists Holiday and Weekly Off as
  outcomes, which the model couldn't represent before.
- **Employee Loan/Advance Management (SRS §51 / Module 36 §37)** — the payslip only
  had bare `advance_deduction`/`loan_recovery`/`advance_balance` amount fields with no
  workflow behind them. Added `garment.hr.loan` with the full
  Request → HR Approval → Finance Approval → Disbursement → Monthly Recovery flow.
- **Employee Complaint Management (SRS §52)** — missing entirely. Added
  `garment.hr.complaint` (Workplace/Salary/Supervisor/Safety/Welfare, Submit → HR
  Review → Investigation → Resolution).
- **Employee Exit Management (Module 36 §50-51)** — `garment.hr.employee.status` had
  `resigned`/`terminated` options but no actual workflow, no clearance tracking, and
  no final settlement. Added `garment.hr.exit`: Notice → Clearance (HR/Finance/
  Inventory/IT/Administration, matching SRS §51 exactly) → Settlement (gratuity +
  outstanding dues − loan deduction) → Archive (which flips the employee's status and
  archives the record).
- **Employee Transfer (Module 36 §18)** — `garment.hr.promotion` already had a
  `transfer` promotion_type that did nothing on approval. Added
  previous/new Department and Line Assignment fields; `action_approve()` now actually
  moves the employee.
- **Performance Evaluation areas (SRS §40/§46)** — both SRS documents list
  Productivity/Quality/Attendance/Discipline/**Skill**/**Teamwork** as the six
  evaluation areas; the model only scored four. Added `skill_score`/`teamwork_score`.
  Also fixed the Rating Scale to match SRS §43 exactly (Excellent 90-100 / Very Good
  80-89 / Good 70-79 / Average 60-69 / Need Improvement below 60) — the old thresholds
  and labels didn't match the spec. Existing selection *keys* (`outstanding`, `good`,
  `average`, `below_average`, `poor`) were deliberately left unchanged and only
  relabeled/re-thresholded, so previously stored ratings keep resolving correctly.
- **Employee Master fields** — added Gender, Date of Birth, Blood Group and Work
  Location (all explicitly listed in both SRS documents' Employee Profile sections
  but absent from the model), plus a `shift_id` convenience field.
- **Employee Category** — both SRS documents list Worker/Supervisor/Staff/Manager/
  Executive/Contract Employee; the designation model only had 4 of the 6. Added
  Supervisor, Executive and Contract Employee as additional (not replacement)
  options, so no stored data changes meaning.
- **Department** — added `employee_count`/`employee_ids` and a proper form view with
  an Employees stat button (Department previously had no form view at all, only a
  tree — a `garment_hr_department` model has none itself, House Style §7.3 requires
  at least tree+form for every real business-object model). Also added the missing
  Washing/Packing/Warehouse/Commercial departments to the seed data — both SRS
  documents list them but the seed data only had a subset.
- **Designation** — added a proper form view (same tree-only gap as Department),
  plus `salary_structure_id` and `responsibilities` (SRS §10 explicitly lists
  Responsibilities as a Designation field).
- **AI Workforce Analytics** — retention-risk scoring now also weighs outstanding
  loan balances (via the new Loan model) and unresolved complaints, in addition to
  the attendance/discipline/performance/advance signals it already had.

## Deliberately simplified / deferred (and why)

- **Full weekly roster grid (SRS §26 "Roster Management": per-day-of-week shift grid,
  e.g. "Monday: Morning, Tuesday: Night")** — `garment.hr.shift.assignment` covers
  Worker Shift Assignment (Module 36 §25) as one row per employee per effective date
  range, which is what both SRS examples actually show, but does not model a
  day-of-week rotation grid. A real weekly rotation would need its own calendar-style
  model; deferred as lower-value than the payroll/exit/loan gaps for this pass.
- **Role-specific KPI Management (SRS §42: distinct Worker/Supervisor/Manager KPI
  sets — Line Efficiency, Cost Control, Delivery Performance, etc.)** — not modelled
  as extra dynamic fields on `garment.hr.performance`, which would need a different
  field set per employee category and doesn't fit Odoo's static schema well. The
  Worker-level KPIs (Productivity/Quality/Attendance/Discipline/Skill/Teamwork) are
  now fully covered; supervisor/manager-level line-efficiency and cost-control KPIs
  are already tracked in more authoritative detail by `garment_ie_management`
  (`garment.ie.line.balance`, `garment.ie.productivity.record`) and
  `garment_production` (OEE, line balancing) — garment_hr is not given a redundant,
  weaker copy of those.
- **Employee Welfare Management (SRS §50: Medical Support, Welfare Fund,
  Accommodation, Emergency Support)** — Medical/Transport/Food allowances already
  exist as payroll earnings; a dedicated Welfare Fund ledger was judged out of scope
  for this pass since it's Finance-ledger shaped (contributions, fund balance) rather
  than an HR record, and `garment_finance` already owns `garment.budget`/
  `garment.expense` for that kind of tracking. Not modelled to avoid an
  under-powered duplicate.
- **Production incentive is self-contained, no cross-module FK** — `garment.hr.
  incentive.production_reference` is a plain Char, not a Many2one into
  `garment_production`/`garment_ie_management`. Per the house style's cross-module
  rule, a Many2one is only added when the module is structurally dependent on the
  target; MODEL_MAP.md documents `garment_ie_management`/`garment_production` as
  linking *to* `garment.hr.employee`, not the reverse, so `garment_hr` was not given
  a new `depends` entry on either.

## Cross-module links (unchanged from before, per MODEL_MAP.md)

No new `depends` entries were added. `garment_hr` still only depends on
`base`, `mail`, `portal`, `garment_buyer_crm` (used for the shared `garment.ai.engine`
abstract model that `models/garment_ai_engine.py` extends). All new models
(`garment.hr.salary.structure`, `garment.hr.shift`, `garment.hr.shift.assignment`,
`garment.hr.bonus`, `garment.hr.incentive`, `garment.hr.loan`, `garment.hr.complaint`,
`garment.hr.exit`) live entirely inside `garment_hr` and relate only to
`garment.hr.employee`/`garment.hr.department`/`garment.hr.designation`/
`garment.hr.payroll`, matching the note in MODEL_MAP.md that other modules
(`garment_production`, `garment_ie_management`, `garment_maintenance`,
`garment_mobile_platform`, `garment_compliance`) link *to* `garment.hr.employee` — its
key fields (`employee_id`, `name`, `department_id`, `designation_id`, `status`, etc.)
were all kept in place, only added to.

## Validation

- `python3 -m py_compile` — all `.py` files in the module compile cleanly.
- `xmllint --noout` — all `.xml` files in the module parse cleanly.
- `security/ir.model.access.csv` — every model in `models/` has at least one access
  row and vice versa (cross-checked programmatically); no duplicate access ids; every
  referenced group id resolves to a `res.groups` record defined in
  `security/garment_hr_security.xml`.
- No duplicate XML record/menu ids across the module.
- Manifest `data` load order was adjusted so `garment_hr_department_views.xml` (whose
  new stat button references `action_garment_hr_employee`) loads *after*
  `garment_hr_employee_views.xml` — a forward-reference that would otherwise fail on
  a clean install.
