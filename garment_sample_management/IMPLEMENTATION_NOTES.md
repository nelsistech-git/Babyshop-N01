# Implementation Notes — Sample Development Management (Gap-Upgrade Pass)

Date: 2026-08-24
Scope: Gap-upgrade of an already-working module against
`specs_txt/Sample Development Management System.txt` (SRS Module 7, Parts 1-3),
plus the mandatory `attrs=`/`states=` → Odoo 17 direct-attribute conversion.

## SRS sections covered by this pass

| Section | Status | Notes |
|---|---|---|
| 6. Sample Master fields | Extended | Added real `bom_id` (Many2one `garment.bom`), kept legacy `bom_reference` (Char) for old data; kept `order_reference` free-text (see below). |
| 7. Sample Types | Extended | Added Woven/Sweater-specific categories (section 45). |
| 8-12. Request/Planning/Material/Room mgmt | Extended | Added `packing` to the activity/operation list (was missing from section 12's operation list). |
| 13. Pattern Development Integration | **Added** (was fully absent) | `pattern_id` (Many2one `garment.pattern`, already in the installed `garment_style_library` dependency), `pattern_created_date`, `pattern_version`, `pattern_maker_id`, `pattern_approval_status` on `garment.sample`. |
| 14. Sample Production Tracking | **Added** | `garment.sample.activity` gained cutting fields (`cutter_id`, `fabric_used`, `panel_status`), sewing fields (`sewing_start`, `sewing_complete`), finishing fields (`ironing_done`, `trimming_done`, `packing_done`). |
| 15. Sample QC Checklist | Already complete | No change needed. |
| 16. Approval Workflow | Already complete | No change needed. |
| 17. Buyer Comment Management | Already complete | Added chatter audit-trail post on completion (section 47). |
| 18/40. Sample Revision Management | Extended | Added `responsible_department` (Selection) and `comment_id` (link to the triggering buyer comment = "Previous Sample Reference"). |
| 19/33. AI Sample Assistant | Extended | Added `find_similar_samples()` (AI Sample Similarity Search) to the shared `garment.ai.engine` extension + `action_find_similar_samples` button/field on the sample form. Image comparison and measurement verification were already implemented. |
| 20-21. Sample Cost + Cost Approval | Already complete | No change needed. |
| 22-23. Courier + Submission | Already complete (merged into one model) | Added audit-trail chatter post on Delivered/Buyer Received transitions. |
| 24. Approval Types | **Added** | `approval_type` Selection (Design/Fit/Color/Measurement/PP/Final) + `attachment`/`attachment_filename` on `garment.sample.approval`, plus a dedicated form view. |
| 25. Sample Calendar | **Added** | Calendar view on `garment.sample` (`required_date`), wired into the main Samples action. |
| 26. Sample Dashboard | Already present | Existing graph/pivot dashboard kept as-is. |
| 27. Sample Room Dashboard | **Added** | New pivot/search view on `garment.sample.activity` grouped by operator/machine/room with Today/Pending/Delayed filters, its own menu item. |
| 28. Sample Room Capacity Planning | **Added** (new model) | `garment.sample.room.capacity` — resource type/count/available hours/efficiency, computed Daily Capacity = hours × count × efficiency%. Full security + tree/form/pivot views + menu. |
| 29. Sample Priority Management | Fixed | Priority labels realigned to the SRS wording (Low/Medium/High/Critical) on both `garment.sample` and `garment.sample.request`; stored values (`0`-`3`) unchanged so no data migration is needed. |
| 30. Sample Notification System | **Added** (partial — see Deferred) | `_cron_sample_notifications()` on `garment.sample` + a daily `ir.cron`, covering the four example alerts (fit deadline tomorrow, PP pending, QC required, buyer approval >14 days) via native Odoo activities (Notification + Email channels). |
| 31. Buyer Portal Sample Management | Untouched (by design) | `garment_buyer_portal` already applies `portal.mixin` to `garment.sample` in its own extension file (`garment_sample_portal.py`) — confirmed intact, not duplicated here. |
| 32. Mobile Sample Application | Untouched (by design) | Delivered by `garment_mobile_platform`, which already writes to `garment.quality.inspection`; no direct code needed in this module. |
| 34-37. DB design / relationships / integration | Confirmed | Model set matches the SRS table exactly (with the section-13/24/28 additions above layered on). |
| 38-39. Security & Record Rules | Extended | Added `group_sample_designer` and `group_sample_pattern_master` (previously missing from the access matrix). Split the "full access" rule so Production Manager now sees **approved/bulk_production samples only** (was previously unrestricted — a real gap against section 39). Added `is_locked` + a `write()` guard so **approved samples become locked** for everyone except the Sample Manager group. Overrode `unlink()` to soft-delete (archive) instead of a hard delete — "deleted samples move to archive". Verified buyer/portal users already have zero CSV access to `garment.sample.cost` (no row exists for `base.group_portal` on that model) — "buyer cannot view internal costing" was already true, just undocumented. |
| 40. Revision fields/workflow | Extended | See section 18 above. |
| 41-42. Analytics & Reports | Extended | Added `delay_days` (computed vs. `required_date`/`submission_date`) and `delay_reason`, and `approval_duration_days` (computed from submission to final approval) to `garment.sample`, plus search filters/group-bys for delay and buyer-approval-state. |
| 43. Print Documents | Extended | Kept the existing "Sample Tracking Sheet" as the Sample Development Sheet. Added two new QWeb reports: **Sample Submission Form** (bound to `garment.sample.courier`) and **Sample Approval Certificate** (bound to `garment.sample`). |
| 44. Sample API Design | **Deferred** | No `controllers/` directory exists in this module and none of the SRS's 10 named models call for one; the buyer-facing and mobile-facing read/write surfaces are already served by `garment_buyer_portal` and `garment_mobile_platform`'s own controllers. Adding a parallel REST layer here would duplicate those and was judged out of scope for a model-layer gap-upgrade. |
| 45. Bangladesh Garment Sample Standards | **Added** | `garment_process` (Knit/Woven/Sweater) on `garment.sample`, `shade_approval_status`, `wash_approval_status`, `sealed_sample`/`sealed_sample_reference`, and 7 new `garment.sample.type` categories (Development, Sealed, Yarn Approval, Color Approval, Knitting, Linking, Wash) with seed data. |
| 46. Compliance & Quality Integration | Extended (lightweight) | Added `chemical_requirement`, `wash_standard`, `testing_requirement`, `buyer_compliance_notes` as tracked fields directly on `garment.sample`, rather than adding a hard dependency on `garment_quality`/`garment_compliance` (those modules' dependency chains — `garment_production`, `garment_warehouse`, `garment_hr`, etc. — are heavy for a data-tracking-only need, and neither module depends back on this one, so a future pass could still add real FK links safely). |
| 47. Audit Trail | Extended | `garment.sample.approval`, `garment.sample.comment`, `garment.sample.qc` and `garment.sample.courier` action methods now `message_post` onto the parent sample's chatter so Approval/Rejection/Comment/QC/Courier events show up in the sample's own audit trail (they previously only updated their own record silently, several of which don't even have a chatter of their own). |
| 48. Performance | Extended | Added `index=True` on the hot filter fields (`buyer_id`, `style_id`, `sample_type_id`, `status` on `garment.sample`; `buyer_id`, `style_id` on `garment.sample.request`) for the 500k+ record scale target. |
| 51. Future Smart Factory | Not implemented (explicitly "Future") | No action taken, as specified in the SRS itself. |

## Known-bug fix: `attrs=` / `states=` → Odoo 17 direct attributes

Found and converted **7** occurrences across 4 view files:

- `views/garment_sample_views.xml` — 3 button `attrs` (Submit to Buyer, Mark Approved, Transfer to Bulk Production)
- `views/garment_sample_cost_views.xml` — 1 button `attrs` (Move to Next Stage)
- `views/garment_sample_courier_views.xml` — 1 button `attrs` (Move to Next Status)
- `views/garment_sample_request_views.xml` — 2 button `attrs` (Approve, Create Sample)

All converted to direct boolean expressions (e.g. `invisible="status != 'approved'"`). All new buttons/fields added in this pass were written directly in the new syntax from the start. `grep -rn "attrs=\|states="` across `views/` and `report/` now returns nothing.

## Cross-module integration points (per MODEL_MAP.md)

- `garment_buyer_portal` applies `portal.mixin` to `garment.sample` and reads `garment.sample.approval` in its own model files — left untouched and confirmed intact.
- `garment_mobile_platform` writes to `garment.quality.inspection` (a different module's model) for QC scans — no interaction with this module's models, confirmed no conflict.
- New dependency added: `garment_bom_management` (for the real `bom_id` link). Verified no circular dependency: `garment_bom_management` does **not** depend on `garment_sample_management`, while `garment_order_management` and `garment_buyer_portal` already depend on this module — so this module must never depend on either of those (confirmed `order_reference` stays free-text for that reason).

## Manifest changes

- `depends`: added `garment_bom_management`.
- `data`: added `data/ir_cron_data.xml` and `views/garment_sample_room_capacity_views.xml`.

## Validation

- `python3 -m py_compile` — every `.py` file in the module: **all pass**.
- `xmllint --noout` — every `.xml` file in the module: **all pass**.
