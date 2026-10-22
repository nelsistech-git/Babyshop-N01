# garment_plm — Implementation Notes

## Scope of this module

`garment_plm` is the OVERARCHING stage-gate governance layer of the PLM
journey. It deliberately does **not** re-model style, tech pack, BOM,
sample or costing data — those already have complete, dedicated modules in
this suite. Instead it adds a light-weight tracking layer on top of them,
linking out via `Many2one` fields so it functions as a cross-module status
dashboard and gate-approval workflow.

## Models created

| Model | Purpose |
|---|---|
| `garment.plm.project` | One record per style's end-to-end PLM journey. Links to `garment.style`, `garment.techpack`, `garment.bom`, `garment.sample`, `garment.costing`. Tracks current stage, progress %, delay flags, AI risk insight. |
| `garment.plm.stage.gate` | One line per stage of Concept -> Design -> Sourcing -> Sampling -> Costing -> Approval -> Production Handover (SRS section 4). Planned vs. actual dates, SLA (days), automatic delay detection. |
| `garment.plm.gate.approval` | Gate sign-off per role (Designer / Merchandising / Technical / Quality / Buyer / Production — SRS sections 18 & 46) required to pass a stage gate. |
| `garment.plm.team.member` | Cross-functional team assignment per project (Merchandiser, Designer, Pattern Maker, Sample Coordinator, IE Engineer, Quality Team, Production Team — SRS section 11). |
| `garment.plm.task` | PLM task management (SRS section 47) — Create Tech Pack / Prepare Sample / Update BOM / Submit Approval / Complete Revision, etc. |
| `garment.plm.notification` | PLM notification log (SRS section 48) — approval-pending, sample delay, stage delay, ECN required, buyer feedback, production handover alerts. |

Additionally, `models/garment_ai_engine.py` **extends** the existing
`garment.ai.engine` abstract model (defined in `garment_buyer_crm`, already
extended once by `garment_style_library` for style similarity) with
`analyze_plm_project_risk()` — a deterministic, provider-pluggable
development-risk / production-readiness insight (SRS sections 39-41,
52-54: AI Product Development Assistant, AI Tech Pack Validation, AI
Production Risk Detection). It does not introduce a new persisted "AI"
model, matching the pattern already established by
`garment_style_library/models/garment_ai_engine.py`.

## SRS sections deliberately NOT rebuilt here (and where they live)

| SRS section | Already covered by | Why not duplicated |
|---|---|---|
| 6-8 Style Library / Digital Style Library, 12 Style Status | `garment.style` (`garment_style_library`) | Style master, status and lifecycle_stage fields already exist there. `garment.plm.project.style_id` links to it; style/lifecycle status are surfaced read-only via related fields, not re-stored. |
| 13-17 Design Management, Color, Artwork, Product Documents | `garment.style.color`, `garment.style.image`, `garment.style.document`, `garment.cad.file` (`garment_style_library`) | Full color/artwork/document management already modeled with approval status. |
| 21-29 Tech Pack, Tech Spec, Measurement, Pattern, CAD Integration | `garment.techpack`, `garment.measurement.sheet`, `garment.construction.detail`, `garment.tech.spec`, `garment.pattern`, `garment.cad.file` (`garment_techpack`, `garment_style_library`) | `garment.plm.project.techpack_id` links to the existing tech pack record and surfaces its status; no tech pack fields are duplicated. |
| 30-36 Sample Development, Sample Request/Tracking/Calendar/Cost, Buyer Approval Portal, Digital Comments | `garment.sample`, `garment.sample.request`, `garment.sample.cost`, `garment.sample.approval`, `garment.sample.comment` (`garment_sample_management`) | Complete sample lifecycle module already exists with buyer-portal approval workflow. `garment.plm.project.sample_id` links to the primary sample; sample status is surfaced read-only. |
| 37 BOM Integration | `garment.bom` / `garment.bom.line` (`garment_bom_management`) | `garment.plm.project.bom_id` links to the BOM; material/cost lines live only in BOM Management. |
| Costing Integration | `garment.costing` (`garment_costing`) | `garment.plm.project.costing_id` links to the costing sheet; cost breakdown lives only in Costing. |
| 43-45 Engineering Change Management (ECN) | `garment.ecr` (`garment_style_library`) — already includes `change_category`, full `technical_review -> merchandising_review -> qa_review -> approval -> implemented -> closed` workflow, and an `impact_analysis` text field | A second ECN/ECR model would directly duplicate `garment.ecr`. `garment.plm.project` instead exposes an `ecr_count` computed field and an `action_view_ecrs()` smart-button so ECRs for the style are visible from the PLM journey without re-modeling them. |
| 38 PLM Document Control (version control, access permission, document history) | `garment.style.document`, `garment.tech.attachment`, chatter (`mail.thread`) on every document model across the suite | Odoo's built-in attachment/chatter versioning plus the existing per-module document models already satisfy this; no separate document-control model was added. |

## SRS sections implemented net-new in this module

- Section 4 (overall lifecycle flow) -> `garment.plm.stage.gate` (7 standard stages, auto-generated per project via `action_generate_stage_gates` / on `create`).
- Section 9-11 (Product Development Request, Team) -> `garment.plm.project` header fields (`request_source`, `development_request_id`, `target_launch_date`) + `garment.plm.team.member`.
- Section 18 & 46 (PLM / Product Approval Workflow, approval levels) -> `garment.plm.gate.approval`.
- Section 19 & 50-51 (PLM Dashboard, Analytics, KPIs) -> `views/garment_plm_dashboard_views.xml` (kanban grouped by stage, graph, pivot by buyer x stage) built directly on `garment.plm.project`'s own computed fields (`progress`, `is_delayed`, `delayed_stage_count`, `pending_gate_approval_count`) — no separate dashboard model, following the same pattern as `garment_style_library`'s dashboard.
- Section 47 (PLM Task Management) -> `garment.plm.task`.
- Section 48 (PLM Notification System) -> `garment.plm.notification` (log model, same shape as `garment_tna`'s notification model already in the suite).
- Section 39-41, 52-54 (AI Assistant / Tech Pack Validation / Production Risk) -> `garment.ai.engine` extension (`analyze_plm_project_risk`), surfaced via `action_run_ai_insight()` and the `ai_last_insight` / `ai_risk_level` fields on the project.

## Sections simplified / deferred

- Section 49 PLM Collaboration Portal (buyer/supplier document sharing UI) and Section 55 PLM Mobile Application, Section 57 REST API endpoints — these are front-end/integration surfaces rather than data models; the underlying data (documents, comments, approvals, samples) is already modeled in the linked modules, and Odoo's existing `portal.mixin` / REST-JSON-RPC layers are the natural place to expose them. No new model was added for these; flagged here as a deferred follow-up (would live in a thin portal-controller extension, not a new business object).
- Section 56 PLM Security Management ("audit trail") is satisfied by `mail.thread` chatter + `tracking=True` on all key fields, and by `ir.rule` record rules restricting team members to their assigned projects — no separate audit-log model was added, matching the rest of the suite's convention.

## Cross-module models linked to (see MODEL_MAP.md)

- `garment.style`, `garment.style.category`, `garment.style.development.request`, `garment.ecr` — `garment_style_library`
- `garment.techpack` — `garment_techpack`
- `garment.bom` — `garment_bom_management`
- `garment.sample` — `garment_sample_management`
- `garment.costing` — `garment_costing`
- `garment.hr.employee` — `garment_hr`
- `garment.buyer` (via `style_id.buyer_id` related field) and `garment.ai.engine` (extended) — `garment_buyer_crm`

## Validation performed

- `python3 -m py_compile` on every `.py` file — clean, no errors.
- `xmllint --noout` on every `.xml` file — clean, no errors.
- No deprecated `attrs=` / `states=` view syntax used anywhere in this module.
- Every model has `ir.model.access.csv` rows (base read-only + role-specific + manager full access).
