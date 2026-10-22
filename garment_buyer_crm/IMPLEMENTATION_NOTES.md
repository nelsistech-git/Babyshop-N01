# Buyer CRM & Relationship Management — GAP-UPGRADE Notes

This pass compared the existing `garment_buyer_crm` module against
`specs_txt/Buyer CRM & Relationship Management.txt` section by section and
closed the gaps found. Nothing that already worked was removed.

## Bug fix: `attrs=` / `states=` (Odoo 17 removed both)

Found **9** instances of the deprecated `attrs="{...}"` syntax across 4 view
files (no `states=` usage was found). All converted to direct attribute
expressions:

- `views/garment_buyer_views.xml` — 1 (`action_create_related_partner` stat
  button visibility)
- `views/garment_opportunity_views.xml` — 2 (`action_mark_won` button,
  "Lost Reason" group)
- `views/garment_rfq_views.xml` — 3 (submit/approve/reject buttons)
- `views/res_config_settings_views.xml` — 3 (AI provider-dependent fields)

## Bug fix: hidden dependency on Odoo's `crm` module

`garment.opportunity.tag_ids` pointed at `crm.tag`, a model that only exists
when the standard Odoo `crm` app is installed — which is **not** one of this
suite's dependencies (`depends` only lists `base, mail, portal, contacts`).
This would break tag rendering on any install that only has the Nelsis
Smart Garment modules. Added a local `garment.crm.tag` model
(`models/garment_crm_tag.py`, seeded via `data/garment_crm_tag_data.xml`)
and repointed `garment.opportunity.tag_ids` (and added `garment.buyer.tag_ids`)
at it instead.

## Bug fix: orphaned cron method

`garment.buyer.document._cron_notify_expiring_documents()` existed in code
but was never registered as an `ir.cron`, so expiry reminders never actually
fired. Registered it in the new `data/ir_cron_data.xml`.

## SRS gaps closed

### New models
| Model | SRS section | Notes |
|---|---|---|
| `garment.crm.meeting` | 16 Meeting Management | number sequence MTG/, calendar view, MoM, buyer/internal participants |
| `garment.buyer.visit` | 18 Buyer Visit Management | number sequence VIS/, full visit + 9-item checklist with completion % |
| `garment.buyer.complaint` | 22 Buyer Complaint Management | number sequence CMP/, Logged→Investigation→CAPA→QA→Mgmt Approval→Closed workflow (section 39) |
| `garment.crm.activity` | 15 Activity Scheduler | number sequence ACT/, garment-specific activity types, reminder options, overdue cron |
| `garment.crm.tag` | 31 Search & Filter (Tags) | replaces the broken `crm.tag` dependency, used by Buyer and Opportunity |
| `garment.whatsapp.template` | 25 WhatsApp Integration / 29 Configuration menu | template master keyed to the same automation-event list as section 25 |

### New fields on existing models
- **`garment.buyer`**: `portal.mixin` inherited (buyer is explicitly
  partner/portal-facing per house style and is the model the new
  `garment_buyer_portal` module hangs off of); `branch`, `bgmea_reference`,
  `bkmea_reference` (section 44); `tag_ids`, `internal_notes` (section 35
  field standards); `nda_expiry_date`; buyer segmentation fields
  `business_segment` / `volume_segment` / `profitability_segment` (section
  21 — geography segmentation reuses the existing `country_id` rather than
  duplicating a second region field); full **Buyer Registration Approval
  Workflow** (section 39: `approval_status` Draft→Sales Executive→Marketing
  Manager→General Manager→Managing Director→Approved, with
  `action_submit_for_approval` / `action_approval_advance` /
  `action_reject_approval`); `ai_score_classification` computed
  Platinum/Gold/Silver/Bronze/Low Potential (section 19 score
  classification table); `last_activity_date` / `is_dormant` computed
  (feeds the "Inactive Buyer" notification, section 32/40); One2many + stat
  buttons to the 4 new child models.
- **`garment.opportunity`**: full **AI Opportunity Prediction** field set
  (section 20 — probability of winning, expected margin, buyer response
  time, expected PO date, suggested follow-up date/next action, recommended
  sales executive, similar historical orders) plus
  `action_run_ai_prediction()`; `branch`, `internal_notes`; `meeting_ids`
  reverse relation.
- **`garment.rfq`**: `branch`, `internal_notes`; RFQ Automation crons
  (`_cron_remind_due_dates`, `_cron_escalate_overdue` — section 14).
- **`garment.buyer.communication`**: `comm_number` (section 36 numbering
  series listed a `COM-000001` series that wasn't implemented).
- **`garment.buyer.contact`**: `_cron_notify_birthdays()` (section 40:
  "Trigger birthday and anniversary greetings").

### AI engine
`garment.ai.engine` gained `predict_opportunity()` (+ a deterministic
fallback heuristic mirroring the existing `score_buyer()` pattern) so
`action_run_ai_prediction` on Opportunity has something real to call,
following the same "no provider configured → rule-based fallback" contract
already established for lead scoring.

### Automation Rules (section 40) — new `data/ir_cron_data.xml`
Nightly AI lead scoring, inactive-buyer flagging, NDA expiry notice, buyer
document expiry notice (now actually wired up), contact
birthday/anniversary greetings, RFQ due-date reminders, RFQ overdue
escalation, high-value opportunity notification, and activity overdue
escalation — 9 scheduled actions total.

### Email / WhatsApp templates (sections 24–25)
- `data/mail_template_data.xml`: 12 `mail.template` records on
  `garment.buyer` covering every template named in section 24
  (Introduction, RFQ Acknowledgement, Quotation Submission, Sample
  Dispatch, Production Update, Shipment Notice, Payment Reminder, Holiday
  Greetings, Birthday Wishes, Compliance Document Request, Complaint
  Response, Thank You).
- `data/garment_whatsapp_template_data.xml` + `garment.whatsapp.template`
  model: 10 templates matching the section 25 automation trigger list.
  Actually dispatching through the WhatsApp Business API is left to the
  infrastructure/integration layer (see Deferred below) — this module owns
  the template *content* and trigger mapping only.

### Security (section 37)
Added the missing **Auditor (Read-Only)** group (`group_garment_crm_auditor`)
with read-only access rows across every business model, plus record rules
implementing two SRS section 38 examples that weren't yet enforced:
"Merchandisers can access RFQs assigned to them" (`rule_garment_rfq_assigned_merchandiser`,
scoped via the buyer's/opportunity's assigned merchandiser) and a general
auditor read-only rule on `garment.buyer`. Access rows for all 6 new models
follow the existing `base.group_user` read / merchandiser or admin
read-write / admin unlink pattern.

### Views, search, menus
- Tree/form/search(+calendar/kanban where useful) views for all 6 new
  models, wired into a new **Engagement** app menu (Activities, Meetings,
  Visits, Complaints) and **Configuration** entries (Tags, Email Templates,
  WhatsApp Templates) — matches the section 29 menu tree
  (`Activities / Meetings / Visits` and
  `Configuration > Email Templates / WhatsApp Templates`).
- Buyer form: approval-workflow header/statusbar, 5 new stat buttons
  (Meetings/Visits/Complaints + existing Opportunities/RFQs), Segmentation
  + Bangladesh reference group, NDA expiry, AI classification/dormant
  fields, and new notebook pages for Meetings & Visits / Complaints /
  Activities / Internal Notes.
- Opportunity form: new "AI Prediction" and "Meetings" notebook pages,
  Branch/Internal Notes.
- RFQ form: new "Notes" page (Branch/Internal Notes).
- Search views: added Tags/Currency/Payment Terms/Country fields and
  Dormant/Pending-Approval/High-Priority filters plus extra group-bys
  (section 31 Search & Filter Features, section 27 dashboards).

## Deliberately deferred (with rationale)

- **REST API (section 41)** — a full OAuth2/API-key/JWT REST controller
  layer is an infrastructure-scale addition on its own (auth, rate
  limiting, versioning) and out of scope for a model/view gap-closure pass;
  Odoo's built-in external API (XML-RPC/JSON-RPC) already covers
  programmatic CRUD on every model added here in the meantime.
- **`garment.buyer.kpi` as a dedicated aggregation model (section 27/33)**
  — the existing graph/pivot dashboard views on Buyer and Opportunity
  already answer the section 27 KPI list directly against live data, and
  the suite has a purpose-built `garment_analytics_bi` module
  (`garment.kpi.definition` / `garment.kpi.snapshot` /
  `garment.dashboard.tile`) for cross-module KPI aggregation — duplicating
  that here would fight the MODEL_MAP's single-source-of-truth guidance.
- **`garment.rfq`/Opportunity → `garment.order`/Quotation Many2one** — the
  Quotation model (`garment.merch.quotation`) lives in
  `garment_merchandising` and the Sales/Production Order
  (`garment.order`) lives in `garment_order_management`; both of those
  modules already depend on `garment_buyer_crm` (per MODEL_MAP: "now all
  reference `garment.buyer`"), so adding a reverse dependency back into
  this module would create a dependency cycle. `garment.buyer.complaint`
  therefore keeps `order_reference` as free text rather than a Many2one.
- **Per-certificate expiry dates for the 11 compliance booleans on
  `garment.buyer`** (section 32 "Compliance Certificate Expiry") — the
  existing `garment.buyer.document` model already carries
  `document_type='compliance_certificate'` with its own `expiry_date` and
  reminder cron; adding 11 parallel date fields on the buyer itself would
  duplicate that without adding capability.
- **Full per-stage approver/date audit trail on the Buyer Approval
  Workflow** — implemented `approval_status` (tracked, so every transition
  is already visible in the chatter) plus a single final `approved_by_id`
  / `approval_date`, rather than 4 separate approver+date field pairs per
  stage, to keep the model from ballooning; the chatter tracking already
  satisfies the section 43 "status changes" audit trail requirement.
- **Calendar Integration sync with Google Calendar / Outlook (section
  26)** — `garment.crm.meeting` and `garment.buyer.visit` both expose
  native Odoo `<calendar>` views (so they're immediately usable and
  shareable inside Odoo itself), but external calendar sync is an
  OAuth-per-user integration that belongs in a dedicated connector rather
  than this data-model module.

## Cross-module references (per MODEL_MAP)

No new module dependency was added — every new field/model here uses
either a local model or a model already within `garment_buyer_crm`'s
existing `depends` (`base`, `mail`, `portal`, `contacts`). Other modules
that need to reference these buyers/opportunities/RFQs continue to do so
via `garment.buyer` / `garment.opportunity` / `garment.rfq`, as documented
in MODEL_MAP.md.

## Validation

- `python3 -m py_compile` — every `.py` file in the module: **clean**.
- `xmllint --noout` — every `.xml` file in the module: **clean**.
- `ir.model.access.csv` — parsed and column-count-checked: 52 rows, all
  8 columns, one row set per group per model, no model left without at
  least a `base.group_user` read row.
