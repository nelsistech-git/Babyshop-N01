# garment_logistics — GAP-UPGRADE Implementation Notes

Upgrade pass against `specs_txt/_Logistics & Shipment Management System.txt`
(Module 19 SRS, Parts 1–3). The module already implemented most of the SRS;
this pass closed the remaining gaps and fixed the `attrs=` bug pattern.

## SRS sections covered by this upgrade

- **Section 19 — Logistics Alert System.** New `garment.shipment.
  _cron_check_logistics_alerts()` (daily `ir.cron`, `data/ir_cron_data.xml`)
  raises a Shipment Delay Alert activity when the AI delay score is HIGH, and
  a Document Missing Alert activity when a required document type (B/L,
  freight invoice, or AWB depending on mode) is still absent — both as
  `mail.activity` records on the shipment (dedup'd by summary so re-runs
  don't spam).
- **Section 22 — Transport Request Management (Vehicle Requirement).**
  Added `vehicle_requirement` (Selection) on `garment.transport.trip` — the
  requested vehicle type, distinct from `vehicle_id` (the vehicle actually
  assigned after Vehicle Selection).
- **Section 28 — Port Management (new model).** Added `garment.port`
  (Port Name, Type, Location, Country, Contact, Operating Hours) with
  tree/form/search views, menu, and access rows. Seeded the three ports the
  SRS names explicitly (Chittagong Port, Mongla Port, Dhaka ICD) in
  `data/garment_logistics_data.xml`. Linked from `garment.container`
  (`port_id`, additive alongside the existing `port` Char so nothing
  breaks) and `garment.transport.trip` (`delivery_port_id`).
- **Section 29 — Port Delivery Tracking.** Added `port_delivery_status`
  (Factory Loaded → In Transit → Port Gate Entry → Port Accepted → Vessel
  Loading) and `action_next_port_delivery_status()` on
  `garment.transport.trip` — this 5-stage flow is distinct from the
  trip's own request/assignment `status` field and from the container's
  8-stage tracking status, so it gets its own field per the SRS wording.
- **Section 35 / 52 — Buyer Notification System + Automation Workflows.**
  - Container Booking Automation: `garment.shipment.
    action_generate_container_requirement()` — a button (visible in
    Allocation/Booking) that auto-creates draft Booked containers sized
    from total allocated carton quantity (~700 cartons per 40HC), posting
    a "Container Requirement Generated" message.
  - `action_confirm_shipment_ready()` moves Allocation → Booking once every
    allocation line is Ready, posting a "Shipment Ready" message.
  - Delivery Completion Automation: `garment.container.action_next_status()`
    now posts milestone messages to the parent shipment ("Container
    Loaded", "Vessel Departed", "Delivery Completed") and, once every
    container on a shipment reaches Delivered, `garment.shipment.
    _check_delivery_completion()` auto-sets `status='delivered'`,
    `is_closed=True`, `closed_date`, and posts a closing message.
  - The buyer's `res.partner` is subscribed as a follower on shipment
    `create()`, so these `message_post` milestones reach them via the
    existing mail/portal channels (Email + Portal Notification, per the
    SRS's supported channels). **WhatsApp is not implemented** — no
    WhatsApp Business API credentials/integration exist in this suite;
    deferred as a genuine third-party integration, same as sections 36/53/54.
- **Sections 37 & 39 — AI Freight Cost Prediction / AI Route
  Optimization.** Added `predict_freight_cost()` and
  `suggest_route_optimization()` to the shared `garment.ai.engine`
  extension (rule-based: historical freight average on the same
  destination with a seasonal peak-export heuristic; shipping-line
  transit-time comparison). Wired into `garment.shipment.
  action_run_ai_analysis()` alongside the existing delay prediction, and
  displayed on a renamed "AI Logistics Optimization" notebook page.
- **Section 40 — AI Container Utilization** was implemented in the AI
  engine but never exposed. Added `ai_utilization_note` field and an
  "AI Utilization Analysis" button on the container form so it is
  actually reachable.
- **Section 45 — Carrier Performance Management.** Added `damage_rate`,
  `avg_response_time_hours`, and a computed `performance_grade`
  (Excellent/Good/Average/Poor, banded off `performance_rating`) on
  `garment.forwarder`, shown on its list/form with color decoration.
- **Sections 42–45 — dashboards.** Added a Shipment Status Dashboard
  (kanban grouped by status), a Container Monitoring Dashboard (kanban
  with current location/vessel/ETA), a Freight Cost Dashboard (graph/pivot
  grouped by Buyer / Destination / Forwarder / month, backed by new
  related+stored `buyer_id`/`destination`/`shipment_date` fields on
  `garment.freight`), and a Carrier Performance Dashboard (forwarder list),
  all reachable from Logistics ▸ Dashboard.
- **Section 11 — Container Loading (Dispatch step)** and **section 36 /
  43 (vessel/container position tracking)**: added `dispatch_date` and
  `current_location` on `garment.container`.

## Bug fix — `attrs=`/`states=` → Odoo 17 direct attributes

Converted all 5 instances found across the module's views:
- `garment_container_views.xml` — button `invisible` on status.
- `garment_transport_trip_views.xml` — button `invisible` on status.
- `garment_freight_views.xml` — button `invisible` on `is_selected`.
- `garment_shipment_views.xml` — 2 group `invisible` on `mode` (Air/Courier).

Confirmed with `grep -rn "attrs=\|states=" views/` → no matches after the fix.

## Deliberately simplified / deferred

- **Sections 36, 53, 54 (Real-Time API / GPS API / third-party
  integration).** No live Shipping Line / Freight Forwarder / GPS
  Tracking / Courier API credentials exist in this environment. The data
  fields the APIs would populate (`current_location`, `last_gps_update`,
  `estimated_arrival`, container `current_location`) are modeled and
  editable/updatable manually or by a future integration job; the actual
  HTTP integration is out of scope for this pass.
- **Section 46 — dedicated Container/Freight/Delay-Analysis PDF
  reports.** Only the Shipment Summary PDF report existed and still
  exists; the other three "reports" in the SRS are served via the new
  tree/graph/pivot dashboard views instead of separate QWeb templates,
  consistent with how Odoo Community typically serves list-style reports
  without a print layout. Can be added as QWeb reports later if a buyer-
  facing printed version is specifically required.
- **Section 47 — document version control.** `garment.shipment.document`
  already has approval/sharing/expiry; full version-chain tracking (like
  `garment.document.version` in `garment_document_management`) was not
  duplicated here to avoid re-inventing that module's model — flagged as a
  candidate to link to `garment_document_management` in a future pass.
- **Section 20/56 — mobile app screens.** These are front-end app
  features; the backing data (documents, GPS fields, status transitions)
  is all present and reachable; the mobile client itself lives in
  `garment_mobile_platform`.

## Cross-module links respected (not touched)

- `garment_commercial_export.garment_shipment_export` (`_inherit
  'garment.shipment'`) adds EXP/customs/incentive fields and
  `_compute_commercial_readiness` — untouched, still depends on
  `container_ids`/`bl_ids`/etc. exactly as before.
- `garment_buyer_portal.garment_shipment_portal` adds `portal.mixin` to
  `garment.shipment` — not duplicated here.
- New `garment.port` model does not collide with any model in
  `MODEL_MAP.md`.

## Validation

- `python3 -m py_compile` — all `.py` files in the module: **pass**.
- `xmllint --noout` — all `.xml` files in the module: **pass**.
- `grep -rn "attrs=\|states="` in `views/`: **no matches**.
