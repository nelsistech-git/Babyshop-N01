# garment_production — Implementation Notes

Module 15 of the Smart Complete Garment Software suite: **Production Management,
Planning, MES & Shop Floor System**. This is the flagged MAIN CORE module of the
suite, merging four source SRS documents into one coherent Odoo 17 design:

1. `Production Management System.txt` (Module 14, Parts 1-3)
2. `Garment Production Planning & MES System.txt` (Module 35, Parts 1-3)
3. `Advanced Manufacturing Execution System (MES).txt` (Module 29, Parts 1-3)
4. `Garment Production MES & Shop Floor Management System.txt` (Module 42, Parts 1-3)

## SRS coverage map

| Feature area (all 4 SRS docs, deduplicated) | Model(s) |
|---|---|
| Work centers / production master setup | `garment.work.center` |
| Machines, IoT counters, breakdown status | `garment.production.machine` |
| Production lines (sewing & general) | `garment.production.line` |
| Operation routing + Operation Bulletin + SMV | `garment.operation.routing` / `.routing.line` |
| Production planning (long/med/short term) | `garment.production.plan` |
| Capacity planning (2 SRS formulas supported) | `garment.capacity.plan` |
| Line allocation | `garment.line.allocation` |
| Production calendar (working days/shift/holiday) | `garment.production.calendar` |
| Production approval workflow | `garment.production.approval` |
| Production order (manufacturing order) + dept. progress | `garment.production.order` |
| Work orders (operation-level jobs) | `garment.work.order` |
| Shop-floor Production Entry (manual/tablet/barcode/IoT), hourly monitoring, line efficiency | `garment.production.entry` |
| Operator assignment | `garment.operator.assignment` |
| Operator performance / scorecard / incentive | `garment.operator.performance` |
| Production targets (hourly/shift/daily/monthly) | `garment.production.target` |
| Material issue to floor (request→store approval→issue) | `garment.production.material.issue` |
| Planned vs actual material consumption / variance / wastage | `garment.production.consumption` |
| Cutting order, fabric issue verification | `garment.cutting.order` |
| Fabric relaxation | `garment.fabric.relaxation` |
| Marker planning & efficiency % | `garment.cutting.marker` |
| Cutting bundle (barcode/RFID tracked) | `garment.cutting.bundle` |
| Cutting QC (panel measurement/notch/shade/qty) | `garment.cutting.qc` |
| Washing order, recipe, chemical consumption | `garment.washing.order` / `.recipe` / `.chemical.line` |
| Finishing order & operations (trim/iron/fold/tag) | `garment.finishing.order` / `.operation.line` |
| Final measurement checking | `garment.measurement.check` |
| Packing order & carton tracking | `garment.packing.order` / `.carton` |
| Line balancing & bottleneck detection | `garment.line.balancing` / `.balancing.line` |
| Machine/line downtime with reason codes | `garment.machine.downtime` |
| Production issue / delay / Andon alerts (unified) | `garment.production.issue` |
| Production rework | `garment.production.rework` |
| WIP tracking by department stage | `garment.wip.tracking` |
| OEE (Availability x Performance x Quality) | `garment.production.oee` |
| Production cost roll-up | `garment.production.cost` |
| AI production/completion forecast, bottleneck insight, predictive maintenance | `garment_ai_engine.py` extension (+ AI fields on order/machine) |
| Dashboards / Control Room / MES live output | Graph/pivot/kanban actions on `garment.production.order` and `garment.production.entry` (no separate dashboard model — matches the pattern already used in `garment_style_library`) |

**39 models** in total (see full list in the top-level response).

## Deliberate simplifications / merges (and why)

- **Production Issue / Delay / Andon Alert** are three separate concepts across
  the four SRS docs (Production Delay Management, Production Alert/Andon
  System, Production Issue Management) but describe the same real workflow:
  a floor-reported problem with a type, severity/andon color, impact and
  resolution. Merged into one `garment.production.issue` model with an
  `issue_type` selection covering all reasons named across the four docs
  (material shortage, machine breakdown, worker shortage, quality issue,
  planning issue, power problem, low output/efficiency, deadline risk).
- **SMV Management / Operation Bulletin / Operation Routing** are one process
  in practice (a routing IS a sequence of operations, and each operation
  carries its SMV and skill requirement) — modeled as
  `garment.operation.routing` with an embedded `garment.operation.routing.line`
  rather than three separate models.
- **Operator Skill Matrix**: `garment.hr.employee` (garment_hr module) already
  has `skill_level` and a `garment.hr.skill.matrix` one2many — reused via a
  `related` field on `garment.operator.performance` instead of duplicating a
  skill-matrix model here.
- **Dashboards / Control Room / MES Dashboard / AI Control Tower**: implemented
  as graph/pivot/kanban `ir.actions.act_window` on the existing
  `garment.production.order` and `garment.production.entry` models (grouped/
  filtered by line, status, date) rather than a separate non-transactional
  "dashboard" model — this mirrors the existing `garment_style_library`
  dashboard pattern (`action_garment_style_dashboard`) already used elsewhere
  in the suite.
- **AI features** (completion/delay forecast, bottleneck detection, predictive
  machine maintenance) are implemented as an extension of the shared
  `garment.ai.engine` abstract model (defined in `garment_buyer_crm`), with a
  deterministic rule-based fallback exactly like the AI extensions already
  shipped in `garment_style_library` / `garment_bom_management` / etc., so the
  feature always works without an external AI provider configured.
- **Washing/Finishing/Packing** are modeled as their own order-header +
  line/child models (not folded into the generic `garment.production.entry`)
  because each department's SRS calls out attributes the generic entry model
  doesn't carry (wash recipe/chemicals, ironing temperature, carton
  size/weight/destination) — matching how the SRS itself describes them as
  distinct documents, not just output counters.

## Cross-module integration (real Many2one links, no duplicated masters)

- `garment.style` (garment_style_library) — Style master, referenced from Plan,
  Order, Cutting, Marker, Washing, Finishing, Packing, Routing.
- `garment.bom` / `garment.bom.line` (garment_bom_management) — BOM reference
  on Plan/Order/Routing; `garment.production.consumption.bom_line_id` links
  planned-vs-actual variance back to the exact BOM line.
- `garment.buyer` (garment_buyer_crm) — Buyer on Plan/Order (also related
  through to Washing/Packing orders).
- `garment.merch.order.confirmation` / `garment.merch.handover`
  (garment_merchandising) — order/handover linkage on Plan and Order.
- `garment.order` (garment_order_management, built concurrently by a sibling
  agent) — `order_id` Many2one added on both `garment.production.plan` and
  `garment.production.order` per instructions; `garment_order_management` is
  declared in `depends` so Odoo resolves load order correctly regardless of
  build order.
- `garment.tna` (garment_tna) — TNA milestone sync on Plan and Order.
- `garment.hr.employee` (garment_hr) — every operator/supervisor/inspector
  field across Line, Work Center, Production Entry, Operator Assignment/
  Performance, Cutting QC, Finishing Operations, Rework, Fabric Relaxation.
- `garment.warehouse` / `garment.material` / `garment.stock.move` /
  `garment.fabric.roll` / `garment.rfid.tag` (garment_warehouse) — Material
  Issue, Consumption, Cutting Order fabric fields, Fabric Relaxation, Bundle
  RFID tag, Packing finished-goods warehouse.
- `garment.cad.file` (garment_style_library) — referenced from
  `garment.cutting.marker`.

## Security

Module category `Smart Garment ERP - Production & MES` with 5 role groups
matching the SRS role tables (Operator, Line/Floor Supervisor, Planning/IE
Manager, Production Manager, Production Director/Factory Head), each
`implied_ids`-chained bottom-up. An `ir.rule` restricts Operators to their own
`garment.production.entry` records (matched via `employee_id.user_id`); a
second rule grants Supervisor-and-up full entry visibility. All 39 models have
`ir.model.access.csv` rows (read for `base.group_user`, write/create for the
relevant role, unlink reserved to Manager/Director).

## Validation performed

- `python3 -m py_compile` on every `.py` file — clean.
- `xmllint --noout` on every `.xml` file — clean.
- Automated cross-checks (ad hoc scripts, not shipped in the module):
  manifest `data` file list resolves to existing files; every menu `action=`
  matches a defined `ir.actions.act_window` id (and vice versa); every
  `res.groups` reference in security rules/views/menus resolves to a defined
  group; every `ir.model.access.csv` row's model matches an actual model
  defined in `models/*.py` (39/39, no orphans, no gaps); every `<field
  name="...">` in every view resolves against the correct model (recursing
  into One2many/Many2many sub-trees against the child model, not the parent);
  every `type="object"` button resolves to a real `action_*` method on that
  model. A load-order bug was found and fixed this way: the Work Center form's
  stat button used `%(action_garment_production_machine)d`, which must be
  loaded before `garment_work_center_views.xml` in the manifest — reordered.
