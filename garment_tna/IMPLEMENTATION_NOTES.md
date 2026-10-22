# garment_tna — Implementation Notes (Gap-Upgrade Pass)

This pass upgraded the already-working `garment_tna` module against the full
`TNA (Time & Action Calendar) Management System` SRS (Parts 1-3), and fixed
the `attrs=`/`states=` Odoo-17 bug pattern. Nothing existing was renamed or
removed — every field/model relied on by `garment_production`
(`tna_id` on `garment.production.plan`/`garment.production.order`) and by
`garment_mobile_platform` (`garment.tna.activity` fields queried directly by
the `/api/mobile/tna/tasks/today` controller) is untouched.

## SRS sections closed in this pass

- **Section 7 (TNA Status Workflow)** — the full Draft → Generated →
  Department Review → Active → Monitoring → Completed → Closed lifecycle
  now has real transition buttons/guards on `garment.tna`
  (`action_submit_for_review` / `action_activate` / `action_start_monitoring`
  / `action_complete` / `action_close`). Activation is blocked while any
  Department Approval is still Pending (SRS section 37 "Critical changes
  require approval").
- **Section 8/13/42 (Template + Dependency + Buyer-Specific Settings)** —
  `garment.tna.template.line` gained `dependency_type` /
  `predecessor_line_id`, copied onto the generated Activities on Apply.
  `garment.tna.template` gained `approval_steps` / `required_documents` /
  `escalation_rules` free-text fields for buyer-specific settings.
- **Section 17/18/27 (Auto Escalation, Notification Channels, Reminders)** —
  these previously existed only as static Selection fields with no
  automation behind them. Added three daily `ir.cron` jobs on
  `garment.tna.activity` (`data/ir_cron_data.xml`):
  `_cron_send_pre_due_reminders` (7/3/1 days before), 
  `_cron_send_overdue_reminders` (daily after due date), and
  `_cron_auto_escalate` (4-level escalation by days overdue: L1 immediate,
  L2 at 3+ days to the Department Manager equivalent, L3 at 7+ days, L4 at
  15+ days) — all logging real `garment.tna.notification` records and
  posting to the TNA chatter.
- **Section 20 (Gantt Planning)** — Odoo **Community** 17 ships no Gantt
  view type (same conclusion already reached by `garment_techpack` and
  `garment_merchandising` in this suite — see their own
  `IMPLEMENTATION_NOTES.md`). Added the underlying `delay_status` compute
  (Normal/Warning/Delayed/Critical, stored) on `garment.tna.activity` so
  the Gantt Color Indicators are real, tested data — driving tree/kanban
  decorations now and ready to feed an OCA/Enterprise Gantt view later
  without a model change. The Calendar view remains the working substitute.
- **Section 21/22 (Calendar Filters / Department-wise Dashboards)** — added
  a proper search view for `garment.tna.activity` (Buyer, Style, Department,
  Responsible Person, Status, Priority filters/group-bys — Buyer/Style are
  new stored related fields for this) and five Department Dashboard actions
  (Merchandising, Purchase, Production, Quality, Commercial) under a new
  "Department Dashboards" menu.
- **Section 25 (TNA Automation Engine)** — `garment.merch.order.confirmation`
  (an existing dependency, `garment_merchandising`) is extended in
  `models/garment_merch_order_confirmation.py` to auto-create the TNA
  Master on `action_confirm()`, matching a Template by Buyer/Product
  Category when one exists and applying it (Automatic Date Calculation
  from Shipment Date).
- **Section 26 (Activity Dependency Automation)** — `garment.tna.activity.
  write()` now blocks a status/actual-date change that violates its
  configured Finish-to-Start / Start-to-Start / Finish-to-Finish
  dependency ("System blocks incorrect workflow").
- **Section 28 (TNA Risk Management)** — added a rule-based, stored
  `risk_score` (0-100%) and `main_risk_issue` on `garment.tna`, distinct
  from the AI prediction (section 29), computed from open Risk lines
  (probability × impact) and logged Delays (severity-weighted).
- **Section 29 (AI Shipment Prediction)** — `garment.ai.engine` gained
  `predict_shipment_probability()` (Shipment Probability %, Expected Delay
  days) sharing the same transparent scoring as the existing
  `predict_shipment_risk()`; both are now stored on `garment.tna`
  (`ai_shipment_probability_pct`, `ai_expected_delay_days`) and shown on
  the AI Assistant tab.
- **Section 30 (TNA Reports)** — added "Order Progress Report" (Buyer,
  Order, Style, Completion %, Delay Status) and "Shipment Risk Report"
  (High Risk Orders, Main Issue, Recovery Plan) as printable QWeb reports
  bound to `garment.tna`, alongside the existing single-TNA detail report.
- **Section 35 (Integration Architecture)** — `garment.tna` gained real
  `techpack_id` / `bom_id` / `costing_id` links to `garment.techpack` /
  `garment.bom` / `garment.costing` — these were already listed in
  `depends` but never actually used from this module's models.
- **Section 36/37 (Security & Record Rules)** — added four execution-
  department groups (`group_tna_purchase`, `group_tna_production`,
  `group_tna_quality`, `group_tna_commercial`) with `ir.rule`s scoping
  each to its own `category`/`department` on `garment.tna.activity` /
  `garment.tna.approval` — "Production cannot modify merchandising
  activities. Purchase cannot modify production activities." An explicit
  always-true rule keeps `group_tna_manager` (which implies all four)
  unrestricted, since Odoo OR's a user's matched group-rule domains
  together. "Completed TNA cannot be edited without revision" is enforced
  on `garment.tna.write()` (raises unless the Shipment Date change comes
  through a Revision).
- **Section 38 (TNA Revision Management)** — new model
  `garment.tna.revision` (Revision Number via a new `ir.sequence`,
  Previous/New Timeline, Change Reason, Requested/Approved By, Date,
  Draft/Approved/Rejected state). Approving a revision applies the new
  Shipment Date to the TNA and reopens a Completed/Closed TNA to
  Monitoring.
- **Section 39 (Audit Trail)** — `garment.tna.activity` and
  `garment.tna.milestone` now inherit `mail.thread` with `tracking=True`
  on the fields the SRS example names (dates, status, responsible person),
  each with a proper form view + chatter so the tracked changes are
  actually visible, not just recorded silently.
- **Section 44 (Multi Currency & Export Support)** — `garment.tna` gained
  `currency_id`, `port`, `vessel`, `forwarder`, `buyer_country_id`,
  `destination`.
- **House style bug fix** — the one `attrs="{...}"` instance
  (`views/garment_tna_views.xml`, the "Generate From Template" button) was
  converted to a direct `invisible="status != 'draft'"` expression; all
  other views in this module were already attrs/states-free. Grepping
  `views/*.xml` post-fix confirms zero remaining `attrs=`/`states=`.

## Deliberately simplified or deferred

- **Section 23 (Buyer Portal TNA Access)** — `garment.tna` now inherits
  `portal.mixin` (matching House Style §2, "buyer/partner-facing" models),
  and the `rule_garment_tna_portal_own_buyer` record rule already scopes
  portal buyers to their own TNAs. The actual `/my/...` controller routes
  and templates are **not** added here: `garment_buyer_portal` is the
  suite's single dedicated buyer-portal module (its own
  `controllers/portal.py` already implements `/my/orders`, `/my/samples`,
  `/my/shipments`, `/my/quality`, `/my/techpacks`, `/my/approvals`,
  `/my/messages` by extending each target model with `portal.mixin` from
  *outside* that model's own module — see e.g.
  `garment_buyer_portal/models/garment_shipment_portal.py`). Building a
  second, parallel `/my/tna` surface inside `garment_tna` itself would
  fragment that established one-portal architecture. `garment_buyer_portal`
  does not currently depend on `garment_tna` or reference it — wiring the
  `/my/tna` route belongs in a `garment_buyer_portal` task, following its
  own per-model-extension pattern, now that `garment.tna` is portal-ready.
- **Section 24 (Mobile TNA Application)** — already implemented in
  `garment_mobile_platform` (`/api/mobile/tna/tasks/today`), reading
  `garment.tna.activity` fields directly. Left untouched by design; none
  of the fields it depends on (`tna_id`, `planned_end_date`, `status`,
  `responsible_person_id`, `priority`, `progress_pct`,
  `is_critical_path`, `category`, `activity_name`, and
  `tna_id.tna_number/style_id.style_name/buyer_id.name/merchandiser_id`)
  were renamed.
- **Section 30/31 Department Reports vs Dashboard** — Odoo Community has
  no distinct "report" vs "dashboard" widget; both are implemented as
  filtered graph/pivot/tree actions on `garment.tna.activity`
  (Department Dashboards) plus two QWeb PDF reports on `garment.tna`
  (Order Progress / Shipment Risk), matching the pattern already used by
  `garment_merchandising`'s own dashboard views for the same reason.
- **Section 40 (REST API)** — no HTTP controller was added in this module;
  `garment_mobile_platform` already exposes a REST-style JSON API against
  these same models and is the suite's established location for that
  surface (see its own `IMPLEMENTATION_NOTES.md`).
- **Section 43 (Multi Factory)** — `factory` / `production_unit` remain
  plain `Char` fields (as before). A real `Many2one` to `garment.warehouse`
  would need a new cross-module dependency for a field that is descriptive
  at the TNA level (actual multi-factory routing already lives in
  `garment_production`'s `production_line_id`/work-center model); not
  changed to avoid an unjustified new dependency.
- **Section 49 (Future Smart Factory Enhancements)** — explicitly marked
  "Future" in the SRS; not implemented.

## Existing-module models this module links to (MODEL_MAP)

`garment.buyer` (garment_buyer_crm), `garment.style` /
`garment.style.category` (garment_style_library), `garment.techpack`
(garment_techpack), `garment.bom` (garment_bom_management), `garment.costing`
(garment_costing), `garment.merch.order.confirmation` (garment_merchandising,
also extended for auto-TNA-creation). No new module dependency was added —
every new relation reuses a model this module already depended on, or a core
Odoo model (`res.currency`, `res.country`).
