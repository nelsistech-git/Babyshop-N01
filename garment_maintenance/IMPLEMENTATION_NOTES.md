# garment_maintenance — Implementation Notes

Module 22 / 41 of the Smart Complete Garment Software suite: **Maintenance &
Asset Management System (CMMS)**. Merges two source SRS documents:

- `Maintenance & Asset Management System.txt` (Module 22, Parts 1-3)
- `Garment Maintenance Management System (CMMS).txt` (Module 41, Parts 1-3)

Both documents describe the same underlying factory maintenance operation
(asset register, PM scheduling, breakdown work orders, spare parts,
technician management, calibration, cost, MTTR/MTBF/OEE, IoT, AI predictive
maintenance) at different levels of detail and with slightly different
proposed model names (e.g. `garment.machine` vs `garment.production.machine`,
`garment.maintenance.workorder` vs `garment.maintenance.workorder` — the CMMS
doc's own DB design table). They were deduplicated into ONE coherent design
below rather than built twice.

## SRS coverage

| SRS Section (either doc) | Covered by |
|---|---|
| Asset Master / Registration (Mgmt sec. 6-10) | `garment.asset` (non-production only, see below) |
| Machine Master / Category (CMMS sec. 6-9) | Reused `garment.production.machine` (garment_production) |
| Preventive Maintenance Mgmt / Schedule / Workflow (Mgmt sec. 11-13, CMMS sec. 11, 13) | `garment.maintenance.plan` |
| Maintenance Checklist Mgmt (Mgmt sec. 14, CMMS sec. 12) | `garment.maintenance.checklist` / `.checklist.line` + seed data |
| Breakdown Maintenance / Priority (Mgmt sec. 15-17, CMMS sec. 15-16) | `garment.maintenance.workorder` (`wo_type='breakdown'`) |
| Downtime Tracking (Mgmt sec. 18, CMMS sec. 21-22) | Reused `garment.machine.downtime` (garment_production) — resolved by the Work Order |
| Maintenance Work Order (Mgmt sec. 19, CMMS sec. 14) | `garment.maintenance.workorder` |
| Technician Management (CMMS sec. 17) | `garment.hr.employee` extended in place |
| Spare Parts Master / Categories (Mgmt sec. 21-22, CMMS sec. 25) | Reused `garment.material` (category `spare_parts`, garment_warehouse) |
| Spare Parts Inventory Integration / Issue (Mgmt sec. 23-24, CMMS sec. 18) | `garment.maintenance.workorder.spare.line` posting real `garment.stock.move` |
| Spare Parts Purchase Request / Reorder (Mgmt sec. 25, CMMS sec. 26-27) | `garment.maintenance.spare.request` → raises `garment.purchase.requisition` |
| Maintenance Supplier Mgmt / External Service (Mgmt sec. 26-27, CMMS sec. 31) | Reused `garment.supplier` (garment_supplier) |
| Calibration Management (Mgmt sec. 28-30, CMMS sec. 28-29) | `garment.calibration` |
| AMC / Maintenance Contract (CMMS sec. 32) | `garment.maintenance.contract` |
| Maintenance Cost Management (Mgmt sec. 31, CMMS sec. 19, 36) | Cost fields + pivot/graph views on `garment.maintenance.workorder` (no separate cost model — avoids duplicating cost data already on the WO) |
| Machine Performance / OEE (Mgmt sec. 32-33, CMMS sec. 33) | OEE itself already exists as `garment.production.oee` (garment_production) — NOT recomputed here |
| MTTR / MTBF / Availability / Breakdown Rate / PM Compliance (CMMS sec. 40, 44) | `garment.maintenance.kpi` (new — these metrics do not exist elsewhere) |
| Machine History Mgmt (Mgmt sec. 34, CMMS sec. 23-24) | Derived from `garment.maintenance.workorder` chatter/history + Machine/Asset smart buttons (no separate "history" model — it is a query, not new data) |
| IoT Machine Monitoring (Mgmt sec. 35, 49-50, CMMS sec. 34) | `garment.maintenance.iot.reading` (time-series log + threshold alerting), separate from the latest-snapshot fields already on `garment.production.machine` |
| Real-Time Machine Dashboard (Mgmt sec. 36, CMMS sec. 37) | List/kanban/pivot/graph views + KPI dashboard action (Odoo Community has no dashboard app; delivered as act_window views, consistent with sibling modules) |
| AI Predictive Maintenance / Spare Forecasting (Mgmt sec. 37-40, CMMS sec. 35, 39) | `garment.maintenance.ai.prediction` with deterministic heuristic scorer (same pattern as `garment.quality.ai.analysis`) |
| Maintenance Executive Dashboard / Reports (Mgmt sec. 41, 43-44, CMMS sec. 37, 43) | Views (tree/pivot/graph) on Work Order, Asset, KPI, Contract, Calibration |
| Maintenance Approval Workflow (Mgmt sec. 45, CMMS sec. 27, 30) | `approval_status` / `action_approve` / `action_reject` on Work Order + Spare Request |
| Maintenance Notification System (Mgmt sec. 51, CMMS sec. 42) | `mail.thread` chatter/`tracking=True` on every document (native Odoo activity/notification, no bespoke SMS/WhatsApp gateway — out of scope for a Community addon) |
| Mobile Application (Mgmt sec. 20, 52, CMMS sec. 38) | Out of scope — this module only defines the underlying ERP data model/API surface a mobile client would call; no native mobile app is built |
| API Integration (Mgmt sec. 53, CMMS sec. 45) | Out of scope — standard Odoo external API (XML-RPC/JSON-RPC) already exposes every model; no bespoke REST layer added |
| Third-Party / PLC Integration (Mgmt sec. 54) | Out of scope — `garment.maintenance.iot.reading` is the data sink such an integration would write to |

## Duplication avoidance — cross-module linkage

This is the most important design decision in this module, per the task
instructions, so it is spelled out explicitly:

1. **Production machines are NOT re-modeled.** Both source SRS documents
   propose a `garment.machine` / asset table that includes production
   equipment (sewing, cutting, embroidery, washing...). That register
   already exists as `garment.production.machine` in `garment_production`
   (with `machine_number`, `machine_type`, `status`, IoT snapshot fields,
   etc.). Every model in this module that needs to reference a machine uses
   `machine_id = fields.Many2one('garment.production.machine', ...)`
   instead of a new machine table. `garment.asset` in this module is
   deliberately scoped to **non-production** equipment only: utility assets
   (generator, compressor, transformer, chiller, HVAC, boiler) and facility
   assets (building, vehicle, computer, furniture, quality/testing
   instruments). Most models that reference equipment (Plan, Work Order,
   Contract, Calibration, KPI, IoT Reading, AI Prediction) carry an
   `equipment_type` discriminator (`machine` / `asset`) with two Many2one
   fields, so the same document type can point at either register without
   needing a generic/polymorphic model.

2. **Machine downtime is NOT re-modeled.** `garment.machine.downtime`
   already exists in `garment_production` (start/end datetime, reason,
   status, `action_resolve()`). A breakdown Work Order links to that SAME
   record via `downtime_id` (domain-filtered to open downtime on the
   selected machine). `GarmentMaintenanceWorkorder.action_complete()` is
   what actually calls `downtime_id.action_resolve()` and writes the
   root-cause `action_taken` back onto it — i.e. this module's Work Orders
   are what RESOLVE those downtime events, exactly as instructed, rather
   than tracking a second parallel downtime table.

3. **Technicians are NOT a new person model.** Both SRS documents list a
   `garment.maintenance.technician` model. Instead,
   `models/garment_hr_employee.py` extends the existing
   `garment.hr.employee` (garment_hr) in place with
   `is_maintenance_technician`, `maintenance_specialization`,
   `maintenance_certification` and `maintenance_experience_years`, plus a
   reverse `maintenance_workorder_ids`/stat button on the employee form.
   Every `technician_id` / `engineer_id` field across this module points at
   `garment.hr.employee`, domain-filtered to
   `is_maintenance_technician = True`. This keeps the maintenance workforce
   as the same real employee record used by HR/Payroll/Attendance.

4. **Spare parts are NOT a new item master.** The SRS "Spare Parts Master"
   (Part Code, Name, Category, Brand, Supplier, Min/Max Stock, Unit,
   Location) maps 1:1 onto the existing `garment.material` model
   (garment_warehouse), which already carries `material_code`, `name`,
   `category` (with a `spare_parts` value already defined), `uom`,
   `supplier_id`, `minimum_stock`, `maximum_stock`, `standard_cost` and a
   computed `on_hand_qty`. `garment.maintenance.workorder.spare.line`
   consumes that same model and — critically — posts a real
   `garment.stock.move` (`move_type='issue'`) when a spare line is created,
   so the material's on-hand quantity genuinely decreases instead of just
   being logged as a cost number on the Work Order.

5. **Spare parts reorder raises a real Purchase Requisition.** Rather than
   modeling a second "PO created" workflow, `garment.maintenance.spare.request.
   action_create_purchase_requisition()` creates a `garment.purchase.
   requisition` (garment_purchase) with `source='maintenance'` — a value
   that module's own `source` Selection field already reserves for exactly
   this integration — and a `garment.purchase.request.line` carrying the
   spare part details. Procurement, RFQ, supplier selection and PO
   conversion then run entirely inside garment_purchase, unduplicated.

6. **Maintenance Supplier / Service Provider / Calibration Company is NOT a
   new supplier model.** All three SRS "supplier type" concepts (Machine
   Supplier, Spare Supplier, Service Provider, Calibration Company) map onto
   the existing `garment.supplier` (garment_supplier, which already has a
   `supplier_type` Selection including `'service'`). `garment.maintenance.
   contract.vendor_id`, `garment.calibration.service_provider_id` and
   `garment.maintenance.workorder.external_provider_id` all point at
   `garment.supplier`.

7. **OEE is NOT recomputed here.** `garment_production` already ships
   `garment.production.oee` (Availability × Performance × Quality per
   line/machine/shift). This module's `garment.maintenance.kpi` instead
   focuses on the maintenance-specific reliability metrics neither SRS's
   existing sibling module computes: **MTTR** (`total_repair_hours /
   breakdown_count`), **MTBF** (`planned_hours / breakdown_count`),
   maintenance-defined **Availability** (`(planned_hours −
   downtime_hours) / planned_hours`), **Breakdown Rate** and **PM
   Compliance %** (completed-on-time PM plans ÷ PM plans due in the
   period) — all derived from this module's own Work Orders and Plans.

8. **IoT reading log complements, not duplicates, the machine's IoT
   snapshot.** `garment.production.machine` already stores the
   *latest-known* IoT values (`last_speed`, `last_vibration`,
   `last_energy_consumption`, `last_data_sync`) for shop-floor MES display.
   `garment.maintenance.iot.reading` is the maintenance-side time-series
   *history* of readings (for both machines and other assets) with
   threshold-based condition scoring (`normal` / `warning` / `critical`)
   that auto-raises a high-priority breakdown Work Order on a critical
   reading — a maintenance alerting function the snapshot fields alone
   cannot provide.

## Deliberately simplified / deferred

- **Mobile application, bespoke REST API layer, SMS/WhatsApp gateway,
  PLC/vibration-sensor hardware integration** — all out of scope for an
  Odoo Community addon; the module defines the data model/API surface
  (standard Odoo XML-RPC/JSON-RPC, plus `garment.maintenance.iot.reading`
  as the IoT data sink) such integrations would use.
- **AI Predictive Maintenance** is a deterministic heuristic scorer
  (`GarmentMaintenanceAiPrediction.run_breakdown_risk_prediction` /
  `run_spare_forecast`), the same "always works without an external ML
  provider" pattern already used by `garment.quality.ai.analysis` in
  garment_quality and the AI extension in garment_production.
- **Depreciation** on `garment.asset` is a manually-updated `current_value`
  field rather than an automatic straight-line schedule — Odoo Community's
  `account_asset` accounting-depreciation engine is out of scope for this
  CMMS-focused module.
- **Machine History** is not a separate model — it is the natural result of
  `mail.thread` chatter plus the Work Order / Downtime / Spare-line records
  already linked to a machine or asset (reachable via the smart buttons on
  `garment.asset` and, for production machines, the existing downtime smart
  button on `garment.production.machine`).
- A spare-parts stock move is only posted when the material has a
  `default_warehouse_id` configured (an optional field on
  `garment.material`); if it is not set, the spare line is still recorded
  and costed on the Work Order, but no stock movement is posted — the same
  soft-fail approach the module takes rather than forcing a hard
  warehouse-assignment requirement onto every spare part.

## New models (13) + 1 in-place extension

`garment.asset`, `garment.maintenance.checklist` (+`.checklist.line`),
`garment.maintenance.plan`, `garment.maintenance.workorder`
(+`.checklist.line`, +`.spare.line`), `garment.maintenance.spare.request`,
`garment.maintenance.contract`, `garment.calibration`,
`garment.maintenance.kpi`, `garment.maintenance.ai.prediction`,
`garment.maintenance.iot.reading`; plus `garment.hr.employee` (garment_hr)
extended in place with maintenance-technician fields.

## Validation

- `python3 -m py_compile` — all `.py` files pass.
- `xmllint --noout` — all `.xml` files pass.
- Every model has `ir.model.access.csv` rows; every access-CSV row maps to
  a real model and a real group; every group referenced from a view exists
  in the security XML; every menu action resolves to a defined
  `ir.actions.act_window`; every defined action is reachable from the menu
  tree; and manifest `data` load order was checked so no view uses a
  `%(xmlid)d` action reference before that action is defined (verified with
  small ad-hoc Python scripts against the actual file set, not just by
  inspection).
