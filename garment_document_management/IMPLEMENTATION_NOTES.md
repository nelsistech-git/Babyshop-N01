# Implementation Notes — `garment_document_management`

Module 23: Document Management & Digital Workflow System.

## Design decision: a generic, low-dependency foundation layer

The SRS (sections 7-59) describes a very large enterprise DMS — repository,
OCR, AI classification, digital signatures/PKI, secure share links,
buyer/supplier portals, dashboards, backup/DR, mobile apps. Almost every
other module in this 27+ module suite already stores its own working
documents on its own model (`garment.style.document`,
`garment.supplier.document`, `garment.hr.document`, `garment.tech.attachment`,
`garment.compliance.document`, `garment.order.document`, `garment.lc.document`,
`garment.shipment.document`, ...). This module does **not** migrate or
replace any of that.

Per the build brief, this module is instead a thin, standalone **foundation
layer** — `depends: ['base', 'mail', 'portal']` only — that any other module
can *optionally* plug into later, built around one key design decision:
`garment.document` links to any other model's record through a generic
`res_model`/`res_id` reference (the same pattern Odoo's own
`ir.attachment`/Documents app uses), so this module never has to depend on
the module that owns the underlying business record, and any of the other
modules can depend on *this* one without a circular dependency.

## Models delivered

| Model | Purpose | SRS sections |
|---|---|---|
| `garment.document.category` | Hierarchical folder/category tree (`parent_id`, `parent_store`) mirroring the Company > Commercial/Production/HR/Compliance/Finance repository structure | 7, 10 |
| `garment.document` | Central document register: binary file + version, generic `res_model`/`res_id` link to any record of any module, tags, security level, check-in/out, expiry, running approval-workflow state | 8, 9, 11-13, 17, 29-31, 36-38, 57 |
| `garment.document.version` | Immutable version-history snapshot created automatically on every check-in / file update | 12-13 |
| `garment.document.approval.workflow` + `garment.document.approval.workflow.step` | Configurable, reusable multi-step approval **template** (sequential or parallel), with amount/category/model dynamic rules and a `get_matching_workflow()` lookup other modules can call | 14-16, 27-28, 41-45 |
| `garment.document.access.log` | Audit trail — who viewed/downloaded/edited/checked-in-out/approved/rejected, with timestamp; written only from Python, never user-editable | 31, 56 |
| `garment.document.tag` | Free many2many tagging for fast search | 11 |
| `garment.document.retention.policy` | Configurable retention/archival rule (N years or permanent, plus the action to take on expiry: notify/auto-archive/lock), matched to documents by category/department/type | 50-51 |
| `garment.document.mixin` (`AbstractModel`) | Reusable mixin any other module's model can add to its own `_inherit` list to get a "Documents" smart button wired to the shared register | 57 (integration) |

## Approval workflow — implementation choice

The SRS asks for a *configurable* engine, not one hard-coded chain per
document type (unlike the simpler single-model `*.approval` pattern used in
sibling modules such as `garment.style.approval` or `garment.bom.approval`).
Rather than adding a **separate** "approval request" execution model on top
of the template (`garment.document.approval.workflow` /
`.workflow.step`), the running state — `workflow_id`, `current_step_id`
(sequential mode), `completed_step_ids` / `pending_step_ids` (parallel
mode) — lives directly on `garment.document`, and every step decision is
written to `garment.document.access.log` (`action='approve'/'reject'`,
`note=<step name/comment>`) so the audit trail (SRS section 31) already
carries full approval history without a second ledger. This keeps the
delivered model count to exactly what was asked for while remaining a
genuinely working sequential/parallel, mandatory/optional, group-or-specific-
approver chain (`action_submit_for_approval` / `action_approve_step` /
`action_reject_step` in `models/garment_document.py`).

## Deliberately simplified / deferred (with reasoning)

* **OCR / AI document processing & classification (SRS sections 10, 20-26,
  45)** — no OCR/AI text-extraction engine ships in Community-only code.
  `document_type` and `garment.document.category.document_type` exist as
  the classification *fields* an external OCR/AI connector would populate;
  wiring an actual provider is a follow-up integration module.
* **Digital Signature / PKI (SRS sections 16, 41-43)** — no dedicated
  signature-capture model. `garment.document.approval.workflow.step.
  requires_signature` is kept as a flag: when set, `action_approve_step()`
  requires the approver to supply a comment (a lightweight electronic
  sign-off, logged to the access log) before the step can complete. A
  licensed digital-certificate/PKI signing integration is out of scope for
  Odoo Community and is a follow-up module.
* **Document Sharing / Buyer & Supplier Portal (SRS sections 32-34)** — no
  `garment.document.share` link model. `portal.mixin` is already inherited
  on `garment.document`, and the shipped `ir.rule` grants a portal user
  read access to a document once a Document Controller adds that user to
  `allowed_user_ids`. Expiring/password-protected public share links are a
  follow-up (add a `garment.document.share` model + controller route on
  top of this same field, no model change needed elsewhere).
* **Encryption / password-protected files (SRS section 30)** — `is_password_
  protected` / `access_password` fields exist as the data placeholders;
  actual file encryption at rest is an infrastructure/deployment concern,
  not a model-level feature, and out of scope here.
* **API endpoints (SRS section 40)** — Odoo's standard XML-RPC/JSON-RPC
  already exposes every model above; no bespoke REST controller was added.
* **Backup & Disaster Recovery, Cloud Storage (SRS sections 48-49)** — an
  infrastructure/ops concern, not an addon-level feature.

None of the above required inventing new fields outside the SRS — they are
already-present fields/hooks ready for a follow-up module to complete.

## Existing-module models referenced

None by design — `depends: ['base', 'mail', 'portal']` only, as instructed,
so this stays a foundation any of the 27+ other modules can add to their own
`depends` later without a dependency cycle. `garment.document.category` and
the retention-policy seed data deliberately use their own lightweight
`department` Selection (Commercial/Production/HR/Compliance/Finance/Quality/
Logistics/General) instead of linking to another module's department model,
for the same reason.

## Follow-up integration task: wiring the smart button into other modules

`garment.document.mixin` and the generic `garment.document` register are
ready to use today (any module can already create `garment.document`
records pointing at its own records via `res_model`/`res_id`, and search/
filter the shared list/kanban view by `res_model`). What is **not** done —
because the other 27 modules are already built and this module cannot
retroactively edit their `__manifest__.py`/views — is:

1. Add `garment_document_management` to the target module's `depends`.
2. Add `'garment.document.mixin'` to the target model's `_inherit` list.
3. Add a stat button to that model's form view:
   ```xml
   <button name="action_view_garment_documents" type="object"
           class="oe_stat_button" icon="fa-file-text-o">
       <field name="garment_document_count" widget="statinfo" string="Documents"/>
   </button>
   ```

The modules that would benefit most from this follow-up, in priority order:

1. **`garment_style_library`** (`garment.style`) — tech specs, approvals,
   buyer correspondence attached to a style, alongside the existing
   `garment.style.document`.
2. **`garment_techpack`** (`garment.techpack`) — construction details,
   label/packaging specs, revisions that benefit from the shared version
   control and approval-workflow engine, alongside `garment.tech.attachment`.
3. **`garment_supplier`** (`garment.supplier`) — audit reports, CAPA
   evidence, certificates that need the retention-policy and access-log
   features this module adds on top of `garment.supplier.document`.
4. **`garment_compliance`** (`garment.compliance.certificate`,
   `garment.compliance.audit`) — the single best fit: certificates
   expiring on a schedule is exactly what `garment.document.retention.
   policy` + the expiry cron were built for.
5. **`garment_finance`** (`garment.lc`) — LC documents, amendments, bank
   correspondence that need the configurable multi-level approval chain
   (Commercial Manager -> Finance -> Director, SRS section 14 example).
6. **`garment_hr`** (`garment.hr.employee`) — employee contracts, NID
   copies, training certificates; also the best real-world case for the
   `highly_confidential` security level and the 7-year HR retention policy
   seeded in `data/garment_document_retention_policy_data.xml`.

## Validation

* `python3 -m py_compile` — all `.py` files pass.
* `xmllint --noout` — all `.xml` files pass.
* Every `data`/`views`/`security` file referenced in `__manifest__.py`
  exists on disk (and vice versa); every action id used in
  `views/garment_document_management_menus.xml` is defined; every
  `model_id`/`group_id` reference in security resolves to a model/group
  defined in this module.
