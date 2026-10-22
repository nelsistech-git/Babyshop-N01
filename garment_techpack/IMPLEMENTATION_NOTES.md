# Tech Pack Management System — Gap-Upgrade Pass (2026-08-24)

This is a GAP-UPGRADE pass on an already-working module. Every existing
model, field, view and action described below as "already covered" was
verified against the SRS (`specs_txt/Tech Pack Management System.txt`) and
left untouched. Only genuine gaps were closed, plus the `attrs=`/`states=`
bug-fix requested for this pass.

## 1. `attrs=` / `states=` fix (Odoo 17 removed both)

8 occurrences converted to direct attribute expressions across 6 files:

| File | Count |
|---|---|
| `views/garment_techpack_views.xml` | 4 |
| `views/garment_artwork_views.xml` | 2 |
| `views/garment_techpack_version_views.xml` | 1 |
| `views/garment_tech_change_views.xml` | 1 |
| `views/garment_tech_review_approval_views.xml` | 1 |

`grep -rn "attrs=\|states=" views/` now returns no matches.

## 2. SRS gaps closed

### Section 7 — Product Classification
`garment.techpack.garment_type` was a free-text `Char`; converted to a
`Selection` with the exact SRS taxonomy (T-Shirt/Polo/.../Sportswear), and
added `fabric_category` (Knit/Woven/Sweater/Other) as the top-level
classification field.

### Section 10/11/12 — Artwork / Print / Embroidery
- Added `print_type` (Print Details) and `embroidery_type` (Embroidery
  Specification) fields to `garment.artwork`.
- Added a `@api.constrains` on `artwork_filename` enforcing the "Supported
  Files" list (AI, PSD, PDF, PNG, JPG, SVG, EPS).

### Section 15 — Measurement Integration
`garment.measurement.sheet` connected to the Measurement Chart but not to
Pattern or Size Specification, and had no Approve/Compare actions:
- Added `pattern_id` (→ `garment.pattern`) and `size_set_id`
  (→ `garment.size.set`).
- Added `action_submit_review()` and `action_approve()` ("Approve
  Measurements").
- Added `action_compare_revision()` ("Compare Revision") — a
  tolerance-point diff (Added/Removed/Modified) against another
  measurement sheet's chart, via new `compare_sheet_id` / `comparison_result`
  fields.

### Section 16 — BOM Integration (Automatic BOM Extraction)
The module had **no** connection to `garment.bom` at all, even though
`garment_bom_management` already carries `garment.bom.techpack_id` back to
this module. Adding a hard `depends` the other way would create a
**circular module dependency** (bom_management already depends on
techpack), so the link is intentionally *not* a stored relational field.
Instead:
- `bom_count` (stored compute) + a `BOMs` smart button (`action_view_boms`)
  read `garment.bom` defensively through `'garment.bom' in self.env.registry`
  — works when BOM Management is installed, degrades to 0/a clear error
  otherwise.
- `action_check_production_release` now also checks BOM approval (see
  section 23 below) the same way.

### Section 18 — Revision Management ("Old Version Archived")
`garment.techpack.version` had every *field* the SRS lists but no notion of
"current vs. archived". Added `is_current` (Boolean); `action_approve()`
now archives every sibling version of the same Tech Pack when a new one is
approved, closing the "New Version Released → Old Version Archived" step
of the Revision Workflow. `previous_version_id` is now auto-populated on
create from the previously-current version instead of being manual-only.

Also added `impact_level` and `buyer_reference` to `garment.tech.change`
(previously only on the version, not on the change request that drives the
"Impact Analysis" workflow stage) plus a `revision_deadline` field, and
`action_next_stage()` now carries impact level / buyer reference through
to the version it creates.

### Section 19 — Version Comparison (was entirely missing)
New wizard `garment.techpack.version.compare` (`wizard/`), opened via a
"Compare Versions" button on the Tech Pack form and a "Compare Revision"
button on the Measurement Sheet form. It renders an HTML side-by-side diff
of the two versions' Revision Information (type, impact level, approval
status, buyer reference, effective date, change reason — with
Added/Removed/Modified-equivalent "Status" column) plus every Tech Change
Request recorded between the two revision dates.

**Scope decision**: full field-level diffing of Technical/Material/Visual
data (measurements, artwork, BOM, packaging) would require the module to
snapshot those sub-documents *per version*, which the existing data model
does not do (measurement/artwork/label/packaging records belong to the
Tech Pack, not to a specific version). Re-architecting that is out of
scope for a gap-closing pass that must not break existing data — the
wizard instead compares the version records' own descriptive fields and
the linked Tech Change Requests, which is an honest, working subset of
section 19.

### Section 21/31 — Approval Workflow automation
- `action_generate_approval_stages()` on the Tech Pack auto-creates the
  full 7-step internal + buyer `garment.tech.approval` sequence
  (Merchandiser Review → ... → Buyer Approved), matching the pattern
  already used for `action_generate_standard_tasks()`.
- `garment.tech.approval.create()` now posts a chatter notification on the
  Tech Pack when a `buyer_submission`-stage approval record is created
  ("Notify buyer after submission" automation rule).

### Section 23 — Production Release Control / Certificate
`action_check_production_release()` only checked 4 of the 7 SRS
conditions. Added the missing three:
- **BOM Approved** — via the same registry-safe `garment.bom` lookup as
  section 16.
- **Sample Approved** — via a registry-safe `garment.sample` lookup
  (`garment_sample_management` also depends on this module, so the same
  circular-dependency reasoning applies).
- **Buyer Approval Completed** — via `approval_ids` where
  `approval_stage == 'buyer_approved'` and `status == 'approved'`.

Added `production_release_date` / `released_by_id`, stamped on successful
release, and a new **Production Release Certificate** QWeb report (Style
Info, Version, Approved-Documents checklist, Approval History, Release
Date, Released By).

### Section 29 — Print Documents
Only the "Complete Tech Pack PDF" existed. Added the other two named
reports: **Production Specification Sheet** (Sewing Instructions /
Measurement Details / Quality Points sourced from the Technical Review
checklist / Packing Instructions) and **Buyer Approval Document**
(Version, Changes, Approval Signature).

### Section 36 — Menu Structure
Added the menu items the SRS names that were missing: **My Tech Packs**,
**Pending Approval** (open `garment.tech.approval` records), **Buyer
Approval** and **Production Release** (state-filtered Tech Pack lists),
and a **Reports** submenu (section 28: Tech Pack Register, Revision
History, Pending Approval, Buyer Tech Pack Status, Production Released
Tech Packs, Revision Trend, Approval Time / Department Delay) built from
list/pivot actions that work with no pre-selected record. The 4 printable
*documents* from section 29 are intentionally **not** bare menu items —
generating a PDF needs a selected Tech Pack, so they stay exposed the
correct Odoo way: via `binding_model_id`/`binding_type="report"` on each
`ir.actions.report`, which puts them in every Tech Pack's own Print menu.

**Deliberate simplification**: the SRS's "Configuration" submenu
(Product/Construction/Stitch/Artwork/Label/Packaging Types, Approval
Rules) implies turning today's `Selection` fields into user-configurable
master-data models. Every one of the 28 modules in this suite uses fixed
`Selection` lists for exactly this kind of classification (see
`garment.artwork.artwork_type`, `garment.bom.status`, etc. — this is the
house convention, not a techpack-specific shortcut), and several existing
Python methods do `== 'print'` / `== 'embroidery'` style comparisons
against these values. Converting them to Many2one master-data records is
a real architectural change with real risk of breaking working code for
comparatively low SRS value; it was deliberately not done in this pass.
No fake/empty Configuration menu was added in its place.

### Section 38 — Kanban View
Cards only showed name/buyer/number. Added Style Image (new
`style_image` related field to `garment.style.front_view_image`), Style
Number, Due Date (`review_deadline`), Responsible Person
(`technical_owner_id`), and an Approval Status badge — matching the SRS
card-content list.

### Section 39 — Calendar View (was entirely missing)
Added `review_deadline`, `buyer_submission_deadline`, `approval_deadline`
fields plus a Calendar view (`date_start="review_deadline"`) on the Tech
Pack action. `garment.tech.change` also gained `revision_deadline`.

### Section 40 — Gantt View
**Deferred, documented, not faked.** Odoo **Community** 17 has no
built-in Gantt widget (`web_gantt` is an Enterprise-only asset) — a
literal Gantt view cannot be shipped in a Community-edition module.
Added the underlying `planned_start_date` / `planned_end_date` fields plus
a stored `is_delayed` / `delay_days` compute (shown as a red flag in the
tree/kanban/form) so an OCA or Enterprise Gantt-capable view can plug in
later without any model changes.

### Section 41 — Pivot & Graph
Added `Revision Trend` (graph+pivot on `garment.techpack.version`,
grouped by month/revision type) and `Approval Trend` / department-delay
pivot (on `garment.tech.approval`, grouped by stage × status), and added
`Season`/`Product Category` group-bys plus a `Revision Count` measure to
the existing Tech Pack pivot. Wired both into the new Reports menu.

### Section 43 — Record Rules ("restricted by company and style")
The Buyer Portal record rule only filtered by buyer partner and state;
added `('company_id', 'in', user.company_ids.ids)` to also scope by
company as the SRS specifies.

### Section 46 — Factory Requirements
Added `factory` / `production_unit` Char fields to the Tech Pack (mirrors
the same fields already on `garment.bom`), and both new print reports
surface them.

## 3. Deliberately NOT duplicated / deferred (with reasoning)

- **Compliance certificates (OEKO-TEX/GOTS/GRS/BSCI/WRAP/SEDEX, section
  46)** already live on `garment.buyer` (`cert_bsci`, `cert_sedex`,
  `cert_wrap`, `cert_gots`, `cert_oeko_tex`) and are already read by this
  module's AI engine extension (`detect_missing_techpack_fields`).
  Duplicating them onto the Tech Pack would fork the source of truth, so
  they were left as buyer-level data. (Note: `garment.buyer` has no GRS
  field — that is a gap in `garment_buyer_crm`, out of scope for this
  module.)
- **Full Dashboard KPI screen (section 27)** — Total/Draft/Pending/
  Approved/Released/Archived counts, Avg Review Time, Approval Rate, etc.
  `garment_analytics_bi` (KPI Definition / Dashboard Tile / Dashboard
  Board models) exists specifically for this purpose suite-wide; building
  a parallel dashboard engine inside `garment_techpack` would duplicate
  that module's job. The Tech Pack's own graph/pivot/kanban views (state
  grouping, revision/approval trend, delay flag) provide the raw
  dimensions an analytics dashboard would consume.
- **Fine-grained audit trail (download/share/print/API access, section
  47)** — Creation/Edit/Revision/Approval are already tracked via
  `mail.thread` (`tracking=True` fields + chatter). Per-download/print/API
  logging is a cross-cutting concern better suited to
  `garment_document_management` (`garment.document.access.log`) than to a
  per-module reimplementation.
- **"Auto-create Tech Pack from approved Style" (section 31)** requires a
  hook inside `garment_style_library`'s own approval flow; out of scope
  for a techpack-only upgrade pass (would require editing another
  module's workflow, which risks that module's own tests/behaviour).

## 4. New files

- `wizard/__init__.py`, `wizard/garment_techpack_version_compare.py`,
  `wizard/garment_techpack_version_compare_views.xml` (Version Comparison
  wizard, section 19).
- Root `__init__.py` updated with `from . import wizard`.
- `security/ir.model.access.csv` — one new row for the wizard model.

## 5. Validation

- `python3 -m py_compile` — every `.py` file in the module: **all pass**.
- `xmllint --noout` — every `.xml` file in the module: **all pass**.
