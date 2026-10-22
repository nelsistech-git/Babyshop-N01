# garment_compliance — Implementation Notes

Merges two overlapping SRS documents into one factory-level compliance
module:

- **SRS1**: "Compliance & Sustainability Management System" (Module 21)
- **SRS2**: "Bangladesh Garment Compliance & Regulatory Management System" (Module 28)

Both documents describe almost the same system from different angles
(SRS1 is buyer/ESG-leaning, SRS2 is Bangladesh-regulatory-leaning); this
module deduplicates their overlapping model tables (both proposed their
own `garment.compliance.audit` / `garment.compliance.finding` /
`garment.compliance.capa` / `garment.compliance.certificate`, and
separate `garment.waste.record` vs `garment.environment.waste`, etc.)
into ONE coherent schema.

## Avoiding duplication with garment_supplier and garment_hr

This was the central design constraint and is called out in every
relevant model's docstring:

- **garment_supplier** already owns SUPPLIER-side compliance:
  `garment.supplier.audit`, `garment.supplier.capa`, `garment.supplier.risk`
  (audits *of* suppliers/vendors). This module's `garment.compliance.audit`
  / `garment.compliance.capa` audit the **factory itself** (buyer, social,
  safety, fire, environmental, internal, government, certification audits
  of Nelsis's own factory) — a different subject entirely. No Many2one
  from this module points at `garment.supplier`; the two audit/CAPA
  families are intentionally parallel, not merged, exactly like
  `garment_quality.garment.quality.audit`/`.capa` already sit alongside
  `garment.supplier.audit`/`.capa` as a third, separate family (production/
  quality-process audits). Each docstring in `garment_compliance_audit.py`
  and `garment_compliance_capa.py` states this explicitly.
- **garment_hr** already owns `garment.hr.compliance` — day-to-day HR
  labor-compliance record-keeping tied directly to `garment.hr.employee`/
  `garment.hr.department` (working hours, minimum wage, overtime, child
  labor, safety — one record per spot-check). This module does **not**
  re-implement that; instead:
  - `garment.compliance.requirement` / `garment.compliance.audit` /
    `garment.compliance.finding` operate one level up — the department-wide
    checklist and formal audit trail (BSCI/WRAP/SEDEX/Accord-Alliance-style)
    that `garment.hr.compliance`'s daily entries feed into.
  - Both `garment.compliance.finding.responsible_department_id` and
    `garment.compliance.audit.department_id` are Many2one to
    `garment.hr.department` (reused, not re-created), and
    `garment.compliance.incident.employee_id` is Many2one to
    `garment.hr.employee` (reused, not re-created) — so a compliance audit
    finding or safety incident naturally cross-links to the exact
    employee/department the HR module already tracks, instead of a second
    freestanding worker/department master.
  - Grievance Management (SRS1 sec. 25) is deliberately **not**
    implemented as a new model here — it is HR case-management scoped to
    an individual worker complaint, closer in nature to
    `garment.hr.discipline`, and is left as a natural future extension of
    garment_hr rather than duplicated in this factory-level module.

## Models created (19)

| File | Model(s) |
|---|---|
| `garment_compliance_standard.py` | `garment.compliance.standard` |
| `garment_compliance_requirement.py` | `garment.compliance.requirement` |
| `garment_compliance_document.py` | `garment.compliance.document` |
| `garment_compliance_certificate.py` | `garment.compliance.certificate` |
| `garment_compliance_audit.py` | `garment.compliance.audit`, `garment.compliance.audit.line`, `garment.compliance.finding` |
| `garment_compliance_capa.py` | `garment.compliance.capa` |
| `garment_compliance_incident.py` | `garment.compliance.incident` |
| `garment_compliance_fire.py` | `garment.compliance.fire.equipment`, `garment.compliance.fire.drill` |
| `garment_compliance_building.py` | `garment.compliance.building`, `garment.compliance.building.inspection` |
| `garment_compliance_chemical.py` | `garment.compliance.chemical` |
| `garment_compliance_waste.py` | `garment.compliance.waste` |
| `garment_compliance_water.py` | `garment.compliance.water` |
| `garment_compliance_energy.py` | `garment.compliance.energy` |
| `garment_compliance_esg_score.py` | `garment.compliance.esg.score` |
| `garment_compliance_calendar.py` | `garment.compliance.calendar` |
| `garment_ai_engine.py` | extends the shared `garment.ai.engine` (abstract, no new model) |

## SRS sections covered

- Compliance Master / Standards (SRS1 §7, SRS2 §6) → `garment.compliance.standard`, seeded with BSCI/WRAP/SEDEX/Accord-Alliance-RSC/ISO 9001-14001-45001/Higg/GOTS/OEKO-TEX/BGMEA/BKMEA/Bangladesh Labor Act/Fire License/Environmental Clearance in `data/garment_compliance_standard_data.xml`.
- Checklist / Requirement Management (SRS1 §8, SRS2 §§6-7,12) → `garment.compliance.requirement`, also reused as the source of audit checklist lines.
- Compliance Document Management (SRS1 §15, SRS2 §8) → `garment.compliance.document` (version control + digital approval workflow).
- Certification Management incl. government licenses/memberships (SRS1 §§16,52, SRS2 §§9-10,68) → one unified `garment.compliance.certificate` register with computed Active/Expiring Soon/Expired status.
- Audit Management, Planning, Execution, Finding Management (SRS1 §§9-12, SRS2 §§13-17,65-67) → `garment.compliance.audit` + `.audit.line` (checklist) + `garment.compliance.finding`, with a Planning→Checklist Review→Execution→Finding Identification→Corrective Action→Closure statusbar and a checklist-completion score matching the SRS2 §17 formula (Completed/Total × 100).
- CAPA / Root Cause Analysis (SRS1 §§13-14, SRS2 §§45-46) → `garment.compliance.capa` (5-Why/Fishbone/Risk Assessment root-cause method, verification + effectiveness check).
- Social Compliance / Labor Law / Working-Hour / Wage Compliance (SRS1 §§21-24, SRS2 §§21-30) → covered via `garment.compliance.requirement`/`.finding` (category='hr') cross-linked to `garment.hr.department`/`garment.hr.employee`; day-to-day record-keeping stays in `garment.hr.compliance` (see dedup note above) rather than being duplicated here.
- Health & Safety, Accident & Incident Management (SRS1 §§26,33) → `garment.compliance.incident`.
- Fire Safety Management (SRS1 §§29-32, SRS2 §§31-37) → `garment.compliance.fire.equipment` (extinguisher/alarm/pump/hose/sprinkler/emergency lighting/exit) and `garment.compliance.fire.drill`.
- Building Safety Management (SRS2 §§38-42) → `garment.compliance.building` + `.building.inspection` (structural/electrical/generator).
- Environmental Compliance / Chemical Management (SRS1 §§34,37-38, SRS2 §§50-51,59-62) → `garment.compliance.chemical` (SDS, ZDHC MRSL status, New Chemical Request→Compliance Review→Safety Approval→Purchase Permission→Usage Allowed workflow), linked optionally to `garment.material` (category='chemical') rather than re-tracking stock quantity/valuation.
- Waste Management (SRS1 §39, SRS2 §§53-54) → `garment.compliance.waste`.
- Water Management / ETP (SRS1 §§36,47-48, SRS2 §§55-56) → `garment.compliance.water` (pH/COD/BOD/TDS parameters).
- Energy Management / Carbon Footprint (SRS1 §§35,43-46, SRS2 §§57-58) → `garment.compliance.energy` (Carbon Emission = Energy × Emission Factor, per SRS1 §44).
- ESG Score Management (SRS1 §§41-42,51) → `garment.compliance.esg.score` (Environmental 40% + Social 40% + Governance 20%, per SRS1 §42 formula), also carries the Buyer Sustainability Portal's per-buyer score.
- Compliance Alert System / Compliance Calendar / Notification System (SRS1 §18, SRS2 §§10,19) → `garment.compliance.calendar`, populated daily by `ir.cron` `cron_garment_compliance_reminders`, scanning certificate expiry (90/60/30-day), audit due dates, and fire-equipment/building-inspection due dates, and flagging anything past due as `overdue`.
- Compliance Dashboard (SRS1 §6, SRS2 §§18,70) → `views/garment_compliance_dashboard_views.xml` (kanban/graph/pivot on Findings, matching the pattern already used by `garment_supplier`'s dashboard — no separate "dashboard" data model, consistent with house style).
- AI Compliance Risk Prediction / AI Sustainability Forecast (SRS1 §§20,53-55, SRS2 §69) → `garment_ai_engine.py` extends the shared `garment.ai.engine` abstract model with `predict_compliance_risk(department)` and `recommend_carbon_reduction()`.

## Deliberately simplified / deferred

- **Grievance Management** (SRS1 §25) — not modeled here; it is
  individual-worker HR case management, a natural extension of
  `garment_hr` (alongside `garment.hr.discipline`), not a factory-level
  compliance register. Deferred rather than duplicated.
- **PPE Distribution tracking** (SRS1 §27) — not modeled as its own
  register; it is asset issuance to individual workers, closer to an HR/
  stores function than factory-level compliance. Deferred.
- **Company-level weighted "Compliance Score"** dashboard number (SRS1 §6,
  SRS2 §18) is not persisted as its own field — it is presented via the
  Compliance Dashboard's graph/pivot aggregation over open/closed
  Findings and Certificate status, matching how `garment_supplier`
  already builds its dashboard (graph/pivot reusing an existing model,
  no separate "dashboard" model). A stored, configurable weighting
  formula can be added later as a `garment.compliance.dashboard` config
  model if the business wants a single persisted number.
- **Buyer/Sustainability Portal templates** (SRS1 §§17,51) — the data
  side is fully modeled (`buyer_id` on Certificate/Audit/ESG Score,
  `portal.mixin` on Certificate/Audit, and portal `ir.rule`s scoping a
  buyer's portal user to their own buyer's certificates/audits), but the
  website/portal controller and QWeb templates that would render these
  under `/my/...` are not built in this pass — same scope boundary used
  elsewhere in this suite where portal.mixin is added without a full
  controller (e.g. `garment_quality.garment.quality.complaint`).
- **Notification channels** (SRS2 §19: Email/SMS/WhatsApp/Mobile App) —
  the calendar/reminder *data* and daily cron are implemented; wiring to
  SMS/WhatsApp gateways is out of scope for a Community-only backend
  module and deferred to whatever messaging integration the suite adds
  later (mail activities/chatter already fire for tracked field changes).
- **Air Quality Management** (SRS2 §57) — folded into
  `garment.compliance.water`'s environmental scope conceptually but not
  given its own model since the SRS gives it only three descriptive
  fields; can be split out later if a dedicated air-quality register is
  needed.

## Cross-module links (real Many2one/Many2many, no re-invented masters)

- `garment.hr.department` (garment_hr) — Requirement/Finding/Audit/Incident/Waste/Water department fields.
- `garment.hr.employee` (garment_hr) — Incident.employee_id.
- `garment.buyer` (garment_buyer_crm) — Audit.buyer_id, Certificate.buyer_id, ESG Score.buyer_id.
- `garment.location` (garment_warehouse) — Fire Equipment/Chemical/Incident storage/location fields.
- `garment.material` (garment_warehouse, category='chemical') — Chemical.material_id (optional link, no stock duplication).
- `garment.warehouse` (garment_warehouse) — Building.warehouse_ids (which warehouses/floors a building houses).
- `garment.ai.engine` (garment_buyer_crm, abstract) — extended, not re-created.

## Validation performed

- `python3 -m py_compile` on every `.py` file — all pass.
- `xmllint --noout` on every `.xml` file — all pass.
- Cross-checked: every model referenced in `security/ir.model.access.csv`
  and `security/garment_compliance_security.xml` (`model_<name>` ids)
  resolves to a model actually defined in `models/*.py` (19/19); every
  `action_*` id referenced from a menu or button resolves to an action
  actually defined in `views/*.xml`, with no orphaned actions or
  dangling references; every file listed in `__manifest__.py`'s `data`
  key exists on disk and vice versa.
