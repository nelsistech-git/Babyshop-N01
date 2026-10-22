# garment_ie_management — Implementation Notes

Module 16 of the Smart Complete Garment Software suite: **Industrial
Engineering (IE) Management System**, built against
`specs_txt/Industrial Engineering (IE) Management System .txt` (all three
parts).

## SRS sections covered

| SRS section(s) | Feature | Model(s) |
|---|---|---|
| 6, 41-43 | IE / Executive / Line Efficiency dashboards | Dashboard actions (graph/pivot) over `garment.ie.smv`, `garment.ie.line.balance`, `garment.ie.productivity.record`, `garment.ie.capacity.study` — see `views/garment_ie_dashboard_views.xml` |
| 7-9, 39-40, 50 | SMV Management, SMV Master Database, SMV Calculation, SMV Approval workflow | `garment.ie.smv`, `garment.ie.smv.allowance.line` |
| 10-11 | Operation Breakdown / Operation Database | `garment.ie.operation` |
| 12-16, 53 (Stopwatch/SMV Update) | Time Study, Stopwatch Time Study, Performance Rating, Allowance Management | `garment.ie.time.study`, `garment.ie.time.study.line`, `garment.ie.time.study.allowance.line`, `garment.ie.allowance.type` |
| 17-19, 54 | Skill Matrix, Operator Skill Profile, Skill-Based Operator Allocation | `garment.ie.skill.matrix`, `garment.ie.skill.matrix.line` (+ "Recommended Operators" smart button on `garment.ie.operation`) |
| 21-25 | Line Balancing, Operation Allocation, Bottleneck Detection, Bottleneck Recommendation | `garment.ie.line.balance`, `garment.ie.line.balance.line` |
| 26-28, 37, 44 | Capacity Planning, Factory Capacity Dashboard, Production Simulation, AI Capacity Forecast, Capacity Planning Reports | `garment.ie.capacity.study` |
| 29 | Method Study | `garment.ie.method.study` |
| 30-31, 54 | Motion Study, Workstation Management | `garment.ie.motion.study`, `garment.ie.workstation` |
| 32-33, 45-46 | Productivity Measurement, Operator Efficiency Report, SMV Variance Report, Line Productivity Report | `garment.ie.productivity.record` (dashboards reuse the same model for the report views) |
| 34, 47-48 | IE Improvement Tracking, Improvement Workflow, Cost Saving Analysis | `garment.ie.improvement` |
| 35-38, 51 | AI Line Balancing Recommendation, AI SMV Prediction, AI Capacity Forecast, AI Productivity Coach, API Integration | `garment.ie.ai.insight` |
| 52 | Work Study / Work Sampling (Bangladesh IE standards) | `garment.ie.work.sampling`, `garment.ie.work.sampling.line` |
| 49 | IE Security Rules | `security/garment_ie_management_security.xml` (4 groups) |
| 20, 53 | IE Mobile Application | No dedicated mobile UI is built (out of scope for an Odoo Community backend addon) — the module exposes standard list/form/kanban-ready models and a manual/API-style entry point (`garment.ie.ai.insight`, s.51 `GET /api/ie/...`) that a mobile client or future integration can read/write against, same pattern as `garment.quality.ai.analysis` in `garment_quality`. |

## Deliberate simplifications / deferrals

- **API controllers (SRS s.51)**: the SRS lists three `GET /api/ie/...`
  endpoints. No Odoo `http.Controller` routes were added — the models the
  endpoints would read (`garment.ie.smv`, `garment.ie.capacity.study`,
  `garment.ie.productivity.record`) already exist and are addressable via
  Odoo's standard JSON-RPC/external API, and building bespoke REST
  controllers was judged out of scope for this pass, consistent with how
  `garment_quality`'s AI section was implemented (data model + manual/API
  entry point, no controller).
- **AI features (s.35-38)**: modelled as a single typed log,
  `garment.ie.ai.insight` (`insight_type` = line_balancing / smv_prediction
  / capacity_forecast / productivity_coach), not four separate models — no
  real ML runs in Community; this mirrors `garment.quality.ai.analysis`
  (garment_quality) and `garment.ai.engine` (garment_buyer_crm).
- **Skill Matrix vs. `garment_hr`**: `garment_hr` already ships
  `garment.hr.skill.matrix` — a general HR competency record with generic
  department-level operation categories and a 1-5 proficiency scale. This
  module's `garment.ie.skill.matrix` is deliberately a *different*,
  finer-grained record: it is scoped to the actual `garment.ie.operation`
  master, carries an efficiency % used directly in Line Balancing capacity
  math, and drives the SRS s.19 operator recommendation — it is not a
  duplicate, it is the IE-specific companion to the HR record.
- **Line Balancing / Capacity Plan vs. `garment_production`**:
  `garment_production` already has execution-time
  `garment.line.balancing` (shop-floor bottleneck snapshot from actual
  output) and `garment.capacity.plan` (per-line/date booked-vs-remaining
  capacity for day-to-day planning). This module's `garment.ie.line.balance`
  and `garment.ie.capacity.study` are the upstream IE *engineering studies*
  — they work from SMV and operator skill before a line is even set up, and
  simulate order-level "how many lines / how many days" questions. Neither
  production model is redefined or modified.
- **Productivity vs. `garment.operator.performance`**:
  `garment_production`'s `garment.operator.performance` is a
  quality/attendance/incentive scorecard using a simple Actual/Target
  ratio. This module's `garment.ie.productivity.record` implements the
  standard garment-industry formula
  `Efficiency % = (Standard SMV x Actual Output) / Minutes Worked x 100`
  and an SMV-variance figure (Standard SMV vs. Actual Time/PC) — the IE
  engineering view of the same shop floor, not a duplicate record.
- **Method Study vs. Motion Study vs. Workstation** were kept as three
  separate, small models (rather than folded into one) because the SRS
  gives each a genuinely different field set (steps/description vs.
  walking-distance/hand-movement vs. machine/table/tools) and each is
  useful searchable/reportable on its own.

## Cross-module models linked to (none redefined)

- `garment.style` — Style Library
- `garment.production.line`, `garment.production.order`,
  `garment.work.order`, `garment.operation.routing`,
  `garment.operation.routing.line` — Production Management & MES
  (`garment_production`); this module studies/improves these, it does not
  redefine routing, lines or work centers
- `garment.hr.employee` — HR & Payroll (`garment_hr`), used throughout as
  the operator/employee reference (Time Study operator, Skill Matrix
  employee, Line Balancing assigned operator, Workstation operator, IE
  Engineer "responsible" fields)

## Validation performed

- `python3 -m py_compile` on every `.py` file — no errors.
- `xmllint --noout` on every `.xml` file — no errors.
- Cross-checked: every model has at least one `ir.model.access.csv` row (20
  models, 60 access rows); every `action="..."` used in the menu file
  resolves to an `ir.actions.act_window` defined in a `views/*.xml` file
  loaded before the menu file; every `groups="..."` reference resolves to a
  group defined in `security/garment_ie_management_security.xml`; no
  deprecated `attrs=`/`states=` view syntax was used.
