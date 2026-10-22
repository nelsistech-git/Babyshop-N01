# garment_demo_data — Implementation Notes

One interlinked demo dataset spanning all 28 business modules of the Nelsis Smart
Garment suite. See `/DEMO_STORY.md` (in the project root, not shipped in this module)
for the original planning doc; this file documents what actually got built.

## The story

- **2 buyers**: Northwind Apparel Sourcing Ltd (UK), BalticHaus Fashion GmbH (Germany)
- **3 styles/orders**, each carried end-to-end through the whole suite:
  - Men's Crew Neck T-Shirt (style_tee / order_tee) — Northwind, 24,000 pcs — the
    flagship example, given the deepest data (full production/quality/IE detail,
    a fabric-delay TNA story, a defect→rework→CAPA quality story, an LC, a shipment)
  - Classic Pique Polo (style_polo / order_polo) — Northwind, 18,000 pcs — medium depth
  - Fleece Zip Hoodie (style_hoodie / order_hoodie) — BalticHaus, 12,000 pcs — medium depth
- **2 suppliers**: Delta Knit Fabrics Ltd (fabric mill, Narayanganj), Bright Trims &
  Accessories (Gazipur)
- **~10 employees** spanning merchandising, pattern making, QC, sewing operators, line
  supervision, IE, maintenance, warehouse, accounts, HR
- Factory floor: 1 warehouse, 2 sewing lines, ~9 machines, 1 IoT gateway/device set

## Load order

28 data files, numbered `01_` (foundation masters) through `05_` (back office &
platform layer) — the number prefix is also the manifest's load order, since later
files' demo records reference earlier files' records by XML id.

## Known modeling notes worth knowing before you look at the data

- Several models' "supplier" fields are typed `Many2one('res.partner')`, not
  `Many2one('garment.supplier')` (e.g. `garment.material.supplier_id`,
  `garment.purchase.order.supplier_id`, `garment.label.spec.supplier_id`). Two
  `res.partner` records (`partner_deltaknit`, `partner_brighttrim`) are created in
  `01_supplier_demo.xml` and also set as `garment.supplier.partner_id`, so the
  `garment.supplier` record and every `res.partner`-typed reference point at the same
  underlying company contact.
- Many workflow/approval fields across the suite are typed `Many2one('res.users')`
  rather than `Many2one('garment.hr.employee')`. No `res.users` demo records were
  created for the HR employees (that's out of scope for a data-only module — creating
  login users is a security-sensitive operation better left to a real onboarding flow),
  so those fields point at `base.user_admin` throughout, and the actual HR person's name
  is carried in free-text fields (remarks/notes/description) instead. This is
  consistent across every file.
- `garment_quality`'s link back to the production floor is a plain `Char` field (a
  soft reference, e.g. `"prod_order_tee / PROD-TS-2601-01"`), not a Many2one — this
  mirrors a deliberate design decision made when `garment_quality` was originally built
  (to avoid a circular module dependency on `garment_production`), documented in that
  module's own `IMPLEMENTATION_NOTES.md`.
- `garment_maintenance`'s demo file creates one small fallback
  `garment.production.machine` record (`machine_fallback_sewing_sn14`) rather than
  referencing one of `garment_production`'s demo machines — a timing artifact of how
  the batches were built in parallel. It's valid, self-consistent data; it just isn't
  tied into the main Line 1/Line 2 narrative the way `garment_iot_platform`'s demo data
  is (which does reference a real production machine, `machine_l1_ol1`).
- A few generic-reference fields (`garment.document.res_model_id`, used by
  `garment_document_management`) point at Odoo's own auto-generated `ir.model` external
  ids (e.g. `garment_techpack.model_garment_techpack`) — these aren't defined in any XML
  file in this suite; the Odoo ORM creates one automatically for every model when its
  module installs. A static XML scan can't confirm they exist ahead of a real install,
  but this is the standard, correct way every Odoo addon does this.

## Validation performed

Static only (no live Odoo/PostgreSQL instance available in the build environment):
`xmllint --noout` on all 28 files (clean), a custom cross-reference checker confirming
every `ref="local_id"` resolves to a record actually defined somewhere in this module
(clean — 350 records, 0 unresolved local refs), and manual field-name verification
against each target module's actual model source for every record (each batch's
build agent read the real `.py` files rather than guessing field names).

**Install this module only on a demo/staging/training database.** It is not meant for
a production database, and uninstalling it removes all demo records it created.
