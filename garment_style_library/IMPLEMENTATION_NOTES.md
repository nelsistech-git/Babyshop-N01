# Implementation Notes — Style Library & Product Development (garment_style_library)

GAP-UPGRADE pass against `specs_txt/Style Library & Product Development.txt` (SRS Module 3).
The module already covered the great majority of the SRS (all 14 core models in section 33's
"Odoo Database Design" table already existed). This pass closes the remaining field-, workflow-
and UX-level gaps found by a section-by-section read of the SRS against the existing
models/views, and fixes the known `attrs=`/`states=` view-syntax bug.

## 1. Bug fix: Odoo 17 `attrs=`/`states=` removal

Odoo 17 dropped both attributes. Converted every occurrence found in the module to direct
attribute expressions — **7 instances across 3 files**:

- `views/garment_style_views.xml` — 4 instances (New Revision / Lock / Unlock buttons,
  the "Locked" `web_ribbon` widget), e.g.
  `attrs="{'invisible': [('is_locked', '=', False)]}"` → `invisible="not is_locked"`
- `views/garment_style_revision_ecr_views.xml` — 2 instances (Revision "Approve" button,
  ECR "Move to Next Stage" button)
- `views/garment_style_development_request_views.xml` — 1 instance ("Convert to Style" button)

Verified with `grep -rn "attrs=\|states="` over the whole module: zero remaining matches.

## 2. SRS gaps found and closed

### Section 7 — Style Number Generation (bug + gap)
`garment.style.create()` fetched the style's `garment.style.category` into a `category`
variable and then **never used it** — the style number was always the bare sequence, not the
SRS's configurable "Company/Year + Product-Category code + running sequence" format
(`ST-2026-KN-000001`). Added `garment.style.category.code` (short code, e.g. `KN` for Knit,
seeded on all 10 default categories) and rewrote `_generate_style_number()` to build
`ST-<year>-<category code>-<sequence>`. Adjusted `data/ir_sequence_data.xml` so the sequence
itself no longer double-applies a prefix.

### Section 10 — Design Information
Added the 8 "Design Elements" fields the SRS lists separately from Product Attributes
(`collar_design`, `sleeve_design`, `pocket_design`, `hood_design`, `waist_design`,
`bottom_design`, `hem_design`, `cuff_design`) and a Decoration checklist (9 booleans —
Printing/Embroidery/Appliqué/Heat Transfer/Sublimation/Silicone Patch/Leather Patch/Rubber
Patch/Reflective Print) alongside the existing single "Primary Decoration" selection, since a
real style commonly combines more than one decoration method.

### Section 14 — Digital Asset Management
- `garment.style.document.tag_ids` referenced Odoo's standard **`crm.tag`** model, which is
  **not** an install dependency of this suite (`depends` is `base, mail, portal,
  garment_buyer_crm` — no `crm`). That is a latent install-time bug (unknown co-model). Replaced
  it with a new self-contained `garment.style.document.tag` master model.
- Added the missing **Preview Thumbnail** field (`thumbnail`, SRS-listed asset property).
- Added a configurable **Document Type** master (`garment.style.document.type`) — see section 35.
- Added explicit tree **and form** views for `garment.style.image` and `garment.style.document`
  (previously tree-only, relying on Odoo's auto-generated default form — a Definition-of-Done gap).

### Section 17 — Measurement Chart Management
`garment.measurement.line` was missing 2 of the SRS's explicit per-point fields:
**Measurement Method** and **Illustration Reference**. Added both, plus an optional
`measurement_point_id` link (with onchange) to a new **Measurement Point master**
(`garment.measurement.point`, section 35 Configuration item), seeded with the 17 standard
points the SRS lists (Chest Width, Waist Width, ... Collar Length).

### Section 18 — Grade Rule Management
"Provide preview before approval" existed only as a button whose method computed a Python
`dict` and **returned it to nowhere** — the user saw nothing. Added
`garment.grade.rule.preview.wizard` (+ line model) so "Preview Grading" now opens an actual
on-screen size × measurement-point grid. Also added `grade_rule_id` on
`garment.measurement.chart` to record which grade rule produced/verifies a chart, and wired
Style Templates to set it when auto-creating a chart.

### Section 19 — Pattern Management
Pattern Components was a single "Primary Component" selection; the SRS lists 12 components a
pattern set typically includes together. Added a 12-field boolean checklist
(`comp_front_panel` … `comp_belt_loop`) alongside the existing selection/notes fields.

### Section 22 / 25 / 28 — Lifecycle Controls, Approval Workflow, Automation Rules
- Added a configurable **Approval Rule** master (`garment.style.approval.rule`, section 35
  Configuration) and `garment.style._generate_default_approval_steps()`, called automatically
  on `create()` and exposed as a manual "Generate Approval Steps" button — implements the SRS's
  "Mandatory Approvals" lifecycle control and the section 28 automation rule.
- Added `missing_assets_warning` / `has_missing_assets` (computed, shown as a form alert banner)
  implementing "Alert users when required assets (CAD, pattern, artwork) are missing", plus a
  matching "Missing Required Assets" search filter and a Reports-menu report.
- Added lightweight status-change notifications in `write()` (activity for the Pattern Master
  when a style enters Sample Development; chatter note when technical review clears into
  Sampling) implementing "Notify Pattern team after design approval / notify Sampling after
  pattern approval" without inventing a dependency on the Sampling module.

### Section 32 — Print Formats (new `report/` folder)
Added 3 of the 4 listed QWeb PDF print formats, bound via `binding_model_id` so they appear
under each form's native Print menu:
- **Style Specification Sheet** (`garment.style`) — style header, technical description, fabric
  and trim tables, first measurement chart, colorways, packaging instructions.
- **Approval Sheet** (`garment.style`) — approval history with approver, dates, comments and
  signature image.
- **Pattern Report** (`garment.pattern`) — pattern info, components checklist, properties and
  linked CAD files.

Deliberately **not** duplicated: **Technical Pack Report**. Full technical-spec authoring is
owned by `garment_techpack` (per `MODEL_MAP.md`); a second, competing "tech pack" report here
would fork the source of truth. The Style Specification Sheet already covers the style-level
fabric/trim/measurement summary this module owns.

### Section 35 — Menu Structure
Added the menu items the SRS lists that had no corresponding menu yet: standalone **Approvals**
(the model already existed as an inline notebook tab only), a **Reports** menu (Style Register,
Missing Technical Data Report, Approval Pending Report, plus existing Revisions/ECR reused), and
under **Configuration**: Measurement Points, Document Types, Document Tags, Approval Rules (Size
Systems menu entry added too, reusing the existing Size Set action).

### Section 30 — Advanced Search & Filters
Style search view only had Buyer filters/groupbys. Added Basic Filters (per-status filters,
Brand/Product Type/Country/Gender group-bys) and Technical Filters (No CAD File, No Pattern,
Missing Required Assets) achievable from existing data without new cross-module fields. Added
dedicated search views to Development Request and ECR (previously none). Business Filters
(Order Quantity, FOB Price, Revenue) are **deferred** — that data lives in
`garment_order_management` / `garment_costing`, not in this module.

### Section 40 — Bangladesh Garment Industry Requirements (Export)
Added `export_documentation_ref` and `port_destination` on `garment.style` (cheap, explicitly
named SRS fields). Compliance certificate tracking (GOTS/GRS/BSCI/...) is **deliberately not
modeled here** — `garment_compliance` already owns `garment.compliance.certificate`; adding a
parallel field set here would duplicate that module, contrary to the house-style cross-module
rule.

### Section 15 / 29 — Dashboard
Existing dashboard was one graph + one pivot on `garment.style`. Added a "Development Pipeline"
graph (dev-request counts by state) and a "Colorway Distribution" pie graph, wired into the
Dashboard submenu, closing the two most-requested KPI charts that were feasible without new
custom OWL widgets.

## 3. Explicitly deferred (documented, not built)

- **PLM lifecycle governance** (stage responsible department / entry-exit criteria /
  cross-functional gate sign-off) is intentionally **not** modeled here — `garment_plm` (which
  depends on this module) already owns that as its stage-gate governance layer. This module
  keeps only the simple `lifecycle_stage` selection it already had.
- **BOM auto-creation from a Style Template** (SRS section 28) — `garment_bom_management`
  **depends on** `garment_style_library`, so adding the reverse dependency here to call
  `garment.bom.create()` would create a circular module dependency. The template's
  `default_bom_note` free-text field is kept as the reference note; real BOM generation belongs
  in `garment_bom_management`, which already links `garment.bom.style_id` back to this module.
- **Audit Trail of document downloads / buyer portal access / API activity** (section 41) —
  `garment_document_management` already owns `garment.document.access.log` for exactly this;
  duplicating it here was avoided. Field-level change tracking (User/Date/Previous/New Value)
  is already covered by `mail.thread` chatter on the tracked fields.
- **Smart Search** (Barcode / QR / AI image / voice search, section 30) and the **AI Future
  Enhancements** (section 44: AI Style Recognition, 3D Virtual Sampling, AR Preview, etc.) are
  explicitly listed by the SRS itself as forward-looking; left untouched beyond the existing
  AI-Assisted Style Similarity feature.

## 4. New files added

```
models/garment_style_document_tag.py       garment.style.document.tag
models/garment_style_document_type.py      garment.style.document.type
models/garment_measurement_point.py        garment.measurement.point
models/garment_style_approval_rule.py      garment.style.approval.rule
wizard/garment_grade_rule_preview_wizard.py garment.grade.rule.preview.wizard (+ .line)
wizard/garment_grade_rule_preview_wizard_views.xml
views/garment_style_config_views.xml       (Document Type/Tag, Measurement Point, Approval Rule)
views/garment_style_approval_views.xml     (standalone Approvals tree/form/search)
data/garment_measurement_point_data.xml    (17 standard measurement points)
report/garment_style_spec_sheet_report.xml
report/garment_style_approval_sheet_report.xml
report/garment_pattern_report.xml
```

All registered in `__manifest__.py`'s `data` list (security → data → views → wizard views →
report → menus, menus last) and imported from `models/__init__.py` / `wizard/__init__.py` /
the root `__init__.py`.

## 5. Cross-module links (no new `depends` added)

`depends` stays `base, mail, portal, garment_buyer_crm` (unchanged) — every new model/field is
self-contained inside this module; no new Many2one into another module's model was added, so no
new dependency was needed. `garment.plm.project` (in `garment_plm`, which already depends on
this module) is the correct home for any future cross-module PLM governance additions.

## 6. Validation

- `python3 -m py_compile` — every `.py` file in the module compiles cleanly.
- `xmllint --noout` — every `.xml` file in the module is well-formed.
- Cross-checked: every model referenced by a view/report/security row is defined; every model
  has at least one `ir.model.access.csv` row; every action id referenced by the menu file is
  defined exactly once; every file in `views/`, `security/`, `data/`, `wizard/`, `report/` is
  registered in the manifest `data` list.
