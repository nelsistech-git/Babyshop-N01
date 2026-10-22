# garment_analytics_bi — Implementation Notes

Module 27 of the Nelsis Smart Garment suite: "Advanced Analytics & Business
Intelligence Platform". Built as a genuine read-side aggregation layer over
six other modules' own data — it owns no operational business data itself.

## SRS coverage map

| SRS section(s) | What was built | Status |
|---|---|---|
| 6-7 (Data Warehouse / ETL) | `garment.kpi.definition._compute_measure` runs a real `read_group` against the target model as the "Extract+Transform" step; `garment.kpi.snapshot` is the "Load" (stored fact) | **Live** |
| 8-19 (Executive/Factory/Quality/Finance/... dashboards) | `garment.dashboard.board` + `garment.dashboard.tile`, seeded with an Executive, Factory Production, Quality and Finance board wired to real KPIs (`data/garment_dashboard_board_data.xml`) | **Live** |
| 20, 54 (Report Scheduler / Scheduled Delivery) | `garment.report.schedule` — full field set (category, frequency, day/time, format, delivery channel, recipients) | **Config-only, deferred** — see below |
| 21-24 (KPI Management Framework / Categories / Scorecard / Targets) | `garment.kpi.definition` (category, department, frequency, target, thresholds); 11 seeded KPIs across Production/Quality/Sales/Finance/HR (`data/garment_kpi_definition_data.xml`) | **Live** |
| 25 (KPI Alert System) | `garment.kpi.snapshot.status` (on_target/warning/critical) computed from the KPI's warning/critical thresholds; a Critical snapshot posts a chatter message on the KPI Definition (`mail.thread`) | **Live** (chatter-based alert, not email/push — see below) |
| 26-30 (MIS Reporting — Daily/Weekly/Monthly/Board reports) | Covered by `garment.report.schedule` records + the KPI/Snapshot data they would draw from | **Config-only, deferred** |
| 31-32 (Power BI Integration) | Not built — no external connector/OData/API endpoint | **Deferred**, out of scope for a self-contained addon |
| 33 (Data Visualization Engine: Bar/Line/Pie/Gauge/Heat Map/Geo Map) | `garment.kpi.snapshot` graph view (`type="line"`) and pivot view give Bar/Line/Pie for free via the standard Odoo graph widget (user can switch chart type in the UI); Gauge/Heat Map/Geographic Map are not standard Odoo Community view types and were not built | **Partially live** (bar/line/pie via stock Odoo widget), gauge/heatmap/geomap **deferred** |
| 34 (Real-Time Analytics Engine) | Dashboard tiles bound to a "custom" measure compute their value live (on every view render) via `read_group`, not from a stale snapshot; IoT/RFID/Mobile "real-time push" sources are out of scope (no such data exists yet in this suite) | **Live** for ERP-transaction tiles; IoT/RFID feed **N/A** |
| 35 (Trend / Comparative / Root Cause / Performance Analysis) | The KPI Snapshot pivot/graph views give trend and comparative analysis natively (group by KPI/period/category). Root-cause analysis (auto-generated "why") is not attempted — that would require the AI Insight/Root Cause engine below | **Trend/comparative live**, root-cause **deferred** |
| 36-38, 50-51 (Predictive BI / AI Assistant / Automated Insight Generation) | Deliberately **not** implemented. This SRS explicitly asked NOT to fake ML — there is no `garment.ai.insight` model here. A KPI going Critical only produces a factual chatter alert ("KPI X is Critical: value V vs target T"), never a fabricated "cause" or "recommendation" | **Deliberately out of scope** |
| 39 (BI Data Security) | Role-based groups (BI Viewer, Executive, BI Analyst, BI Manager) via `ir.model.access.csv`; `garment.dashboard.board.visible_group_ids` lets a board additionally be scoped to specific `res.groups`. Encryption/audit-log are platform-level (Odoo's own `mail.thread`/ORM audit trail, not reinvented here) | **Live** (access rights + board visibility), field-level encryption **N/A** (platform concern) |
| 40-41 (BI Database Models / KPI Definition fields) | `garment.kpi.definition` implements the SRS's 5 named fields (KPI Name, Department, Target Value, Frequency, Responsible User) plus the source/measure/aggregation fields this task explicitly required for a real `read_group` engine | **Live** |
| 42 (BI API Architecture — REST endpoints) | Not built — no `/api/bi/...` controller. Odoo Community has no OpenAPI layer out of the box; adding bespoke JSON-RPC/REST controllers was judged out of scope for "fields + working aggregation", not core to the BI logic itself | **Deferred** |
| 43-44 (Mobile BI Dashboard) | The tile Kanban dashboard view works in the standard Odoo mobile web client (responsive by default); no separate native mobile app or push-notification channel was built | **Partially live** (mobile web works), native/push **deferred** |
| 45 (Executive Analytics Center) | The seeded Executive dashboard board covers Business/Factory/Financial performance tiles; a dedicated "Risk Management" section was not built (no aggregated production/financial/supply-chain risk score exists anywhere in the suite yet to read from) | **Partially live** |
| 46-49 (Data Warehouse Design / Fact & Dimension tables) | `garment.kpi.snapshot` is deliberately the single fact table (one row per KPI x period x optional group), not a full star schema with separate Date/Product/Buyer/Factory dimension tables — those dimensions already exist as the real models (`garment.style`, `garment.buyer`, `garment.production.line`, ...) and are reached via `group_by_field` / `group_res_id` rather than duplicated | **Live**, in a pragmatic single-fact-table form |
| 52-53 (BI Report Library / Export System PDF/Excel/CSV/PPTX) | `garment.report.schedule.format` selection captures the intended export format; no QWeb/xlsx/pptx report templates were generated per library entry | **Config-only, deferred** |
| 55-57 (Performance / Testing / Acceptance) | Addressed by keeping the read_group engine to real indexed fields and simple domains; no load testing performed (out of scope for this task) | N/A |

## What "Live" means here precisely

* **`garment.kpi.definition`** points at one of eleven explicitly allow-listed
  real models (`SOURCE_MODEL_SELECTION` in `models/garment_kpi_definition.py`)
  already provided by `garment_order_management`, `garment_production`,
  `garment_quality`, `garment_costing`, `garment_finance` and `garment_hr`.
* **`garment.kpi.definition._compute_measure`** (also reused directly by
  `garment.dashboard.tile` for "custom" tiles) builds a real Odoo domain
  (optional extra `domain_filter` + a date-range restriction) and calls
  `Model.read_group(domain, [f'{measure}:{agg}'], groupby, lazy=False)` —
  this is a genuine ORM aggregation query, not a stub.
* **`data/ir_cron_data.xml`** registers a real daily `ir.cron` calling
  `garment.kpi.definition._cron_generate_kpi_snapshots()`, which walks every
  active KPI Definition, checks whether it is due for its own
  daily/weekly/monthly/yearly frequency, computes the closed prior period's
  date window, and creates `garment.kpi.snapshot` record(s) (one per
  group-by value when `group_by_field` is set).
* **Dashboard tiles** bound to a KPI (`tile_type = 'kpi'`) show the latest
  stored snapshot (cheap, and consistent with what the scheduled job last
  computed). Tiles with `tile_type = 'custom'` compute their value live,
  every time the dashboard is opened, over a rolling Today/This Week/This
  Month/This Year/All Time window — again through the same `read_group`
  helper, not a cached or hard-coded number.

## What is deliberately NOT live (and why)

* **Report rendering/delivery** (`garment.report.schedule`): the SRS asks
  for daily/weekly/monthly PDF/Excel/CSV/PPTX reports delivered by
  Email/WhatsApp/Mobile Push. Building even one working QWeb report + one
  real outbound mail template would already be a second module's worth of
  work, and WhatsApp/push delivery needs a third-party gateway this addon
  has no credentials or connector for. The model captures every
  configuration field the SRS lists (category, dashboard/KPI source,
  frequency, day/time, format, channel booleans, recipients) and
  `next_run_date` is computed for display, but nothing in this module reads
  that field to actually trigger a send — see the docstring at the top of
  `models/garment_report_schedule.py`.
* **Predictive analytics / AI assistant / automated insight generation**
  (SRS 36-38, 50-51): the task brief explicitly said "not fake ML". No
  `garment.ai.insight` model, no natural-language "why did profit drop"
  assistant, no forecast fields were added. The only automated "insight"
  this module produces is a factual chatter message when a KPI snapshot is
  Critical (measured value vs. target, nothing inferred).
* **Power BI / external BI connector** (SRS 31-32) and **REST API layer**
  (SRS 42): no outbound OData/Power BI connector and no `/api/bi/...`,
  `/api/kpi/...`, `/api/report/...` HTTP controllers were added. Odoo
  Community has no built-in OpenAPI/REST generation; a bespoke JSON
  controller layer was judged separate work from "a working cross-module BI
  read layer" and was left out rather than stubbed with fake responses.
* **Gauge chart / heat map / geographic map** (SRS 33): the Odoo Community
  graph view only supports bar/line/pie natively (all three are wired via
  `garment.kpi.snapshot`'s graph view and switchable in the UI). Gauge/heat
  map/geo map would need a custom OWL widget, which the task explicitly
  asked to avoid.

## Cross-module links (real Many2one / model references, not re-invented data)

* `garment.kpi.definition.source_model` — restricted Selection naming real
  models from `garment_order_management` (`garment.order`,
  `garment.order.shipment`), `garment_production` (`garment.production.entry`,
  `garment.production.oee`, `garment.machine.downtime`), `garment_quality`
  (`garment.quality.inspection`, `garment.quality.defect`), `garment_costing`
  (`garment.costing`), `garment_finance` (`garment.expense`,
  `garment.receivable`), `garment_hr` (`garment.hr.attendance`).
* `garment.kpi.definition.department_id` → `garment.hr.department`
  (`garment_hr`).
* `garment.dashboard.tile.source_model` reuses the exact same allow-list for
  "custom" tiles.
* `garment.dashboard.board.visible_group_ids` → `res.groups` (standard Odoo
  role-based dashboard visibility, SRS section 39).

## Security model

* `group_bi_viewer` — read-only KPI/Snapshot/Board/Tile access (department
  manager level).
* `group_bi_executive` — read-only, same models, distinct group so an
  Executive-only board (`visible_group_ids`) can be scoped separately from
  department managers per SRS section 39.
* `group_bi_analyst` (implies Viewer) — create/edit KPI Definitions,
  Dashboards and Tiles; read-only on Report Schedules.
* `group_bi_manager` (implies Analyst + Executive) — full CRUD everywhere,
  including Report Schedules.

## Validation performed

* `python3 -m py_compile` on every `.py` file — clean.
* `xmllint --noout` on every `.xml` file — clean.
* Every field referenced in a view/data file was cross-checked by hand
  against its model definition (no live Odoo instance was available in this
  environment to install/boot the module).
