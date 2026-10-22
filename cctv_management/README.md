# Smart CCTV Management — Odoo 17 Community

**Developed by [Nelsis Tech](https://www.nelsistech.com) — Nur Uddin Ahammed**

Part of the Smart CCTV Suite (4 packages, built to work together):
- **`cctv_management`** (this package) — the Odoo module: all data, workflows, dashboards, UI
- **`cctv_ai_service`** — the Python/FastAPI detection service this module's webhook receives events from
- **`cctv_model_training`** — the pipeline that trains the PPE/fire-smoke models `cctv_ai_service` uses
- **`cctv_mobile_app`** — the Expo/React Native app that talks to this module over Odoo's JSON-RPC API

See `RELEASE_NOTES.md` (in the suite's top-level delivery) for how all four fit together and a first-install checklist.

## What this module actually does (read this first)

Odoo (Python + XML) can manage data, workflows, dashboards, and a live-video
**grid UI**. It **cannot itself** run computer vision (YOLO/DeepSORT/face
recognition/ANPR) — that needs a real video-processing service with GPU/CPU
inference. This module is split accordingly:

**Built and working right now (pure Odoo):**
- Company → Office/Factory/Warehouse/Branch → Floor → Department → Camera hierarchy (unlimited depth)
- Camera registry for ONVIF/RTSP/Hikvision/Dahua/Uniview/Axis/CP Plus/NVR/DVR/USB
- Live Monitor (v4.1): auto-fits ANY number of cameras on one screen (no scrolling), click a camera for
  full screen with zoom / pan, green (normal) / red (flagged) tracking boxes and a tracking info panel
  in the top-left corner of every monitor - see "Live Monitor" below
- AI Event log, Smart Alerts (auto-generated from severe events), Security
  Incident workflow (Open → Investigation → Action → Closed)
- Face database (employee/visitor/vendor/blacklist/VIP), visit/route tracking,
  vehicle (ANPR) log, face-match log
- Role-based access (10 groups matching the SRS)
- Camera-offline heartbeat monitor (cron, every 5 min)
- QWeb PDF reports (Incident Summary, Camera Health) + all list views export to Excel/CSV natively
- A REST webhook (`/cctv/api/event`, `/cctv/api/heartbeat`) so an external AI service can push detections in

**Needs an external service (not included, but the module is built to receive it):**
- Actual object/human/face/plate detection (YOLO, DeepSORT, InsightFace/FaceNet, OCR-ANPR, pose estimation, PPE detection)
- Turning raw RTSP into something a browser can display (see below)
- SMS/WhatsApp/Telegram delivery (Odoo's `mail` module handles email/in-app out of the box; the others need a connector you already have or a 3rd-party API)

This is the honest, correct architecture — no serious CCTV+AI platform (Genetec, Milestone, Hikvision iVMS included) does the AI *inside* the ERP either; they all use a separate media/inference server and push events into the business system.

## Why browsers can't just play your RTSP URL

Chrome/Firefox have no built-in RTSP decoder. You need a bridge that converts
RTSP → HLS or RTSP → MJPEG. Two good free options:
- **MediaMTX** (https://github.com/bluenviron/mediamtx) — point it at your camera's RTSP URL, it re-serves HLS and also LL-HLS/WebRTC.
- **go2rtc** (https://github.com/AlexxIT/go2rtc) — similar, also gives you MJPEG snapshots which the Live Monitor grid displays natively with zero extra JS.

Once you have a bridge running, put its output URL into the camera's
**"Browser Stream URL (HLS/MJPEG)"** field and it will appear in Live Monitor.

## Installing

1. Copy the `cctv_management` folder into your Odoo 17 `addons` path.
2. Restart Odoo, then Apps → Update Apps List → search "Smart CCTV Management" → Install.
3. Go to Settings → Users & Companies → Groups and assign your team the right
   CCTV role (Security Director, CCTV Operator, Receptionist, etc.).
4. CCTV → Configuration → Sites/Floors/Departments/Cameras: build your hierarchy and register cameras.
5. CCTV → Configuration → Live Monitor Grids: create a grid (e.g. "Factory Floor - 9 Cam") and assign cameras.
6. CCTV → Live Monitor: watch it.

## Wiring up the AI service (Phase 2)

1. Set a shared secret: Settings → Technical → System Parameters → create
   `cctv_management.api_key` = some random string.
2. Run a small Python service (FastAPI is fine) alongside your RTSP bridge that:
   - pulls frames from each camera (OpenCV `cv2.VideoCapture`)
   - runs YOLOv8 for human/vehicle/fire/smoke, DeepSORT for tracking across
     cameras, InsightFace for face embeddings, an ANPR model for plates, and
     a PPE-detection model for helmet/vest/mask
   - POSTs a JSON payload to `https://<your-odoo>/cctv/api/event` with header
     `X-CCTV-API-KEY: <the secret>` (see `controllers/main.py` for the exact
     schema and field meanings)
3. Odoo will auto-create `cctv.event` rows, and for the severe behaviors
   (fighting, trespassing, restricted-area entry, fire, smoke) it will
   auto-create a `cctv.alert` and a `cctv.incident` for you.

## Employee activity & compliance monitoring

Beyond the general AI events, there's now a dedicated employee-monitoring layer:

- **CCTV → Employee Monitoring → Monitoring Assignments**: link an employee
  to their face-database entry (`cctv.person`), assigned zone, and shift
  hours. This is what powers everything below - without a linked
  `cctv.person` matched by your face-recognition service, none of these
  checks can run.
- **Late arrival / early departure**: checked every 15 minutes against the
  employee's configured shift start/end + grace period
- **Left workstation**: flags an employee with no detected presence in
  their assigned zone for longer than `idle_alert_minutes` during shift hours
- **Task delay**: set "Expected Work Zone" on a `project.task`; if it goes
  overdue with zero camera-detected presence of the assignee in that zone in
  the last 3 days, a `task_delay` event/alert is raised
- **Daily Activity Summary**: one row per employee per day - idle count,
  phone-usage count, unauthorized-break count, left-station count, late/early
  flags, and an "unprofessional conduct" bucket for arguments, unofficial
  visitors at a workstation, and excessive non-work group gatherings
- All of this rides on the same `behavior_type` values already defined on
  `cctv.event` (see the model) - the AI service just needs to push events
  with `person_id` set (via face matching) for these to populate

**Before turning this on:** this is meaningfully more intrusive than
perimeter/safety monitoring, and in most places has real legal requirements
around employee notice/consent, data retention limits, and proportionality
(this is general awareness, not legal advice - check what applies in your
jurisdiction and any client's, e.g. local labor law and any relevant data
protection law). In practice that usually means: tell employees what's
monitored and why (a written policy, not just a camera sign), keep the data
access restricted to the HR Manager / Security Director groups (already the
default here), and set a retention/deletion policy on `cctv.event` and
`cctv.employee.daily.summary` rather than keeping it forever. Covert
monitoring specifically framed as catching people rather than a disclosed
performance/safety policy is where this gets legally and ethically risky
fastest.

## Employee monitoring - gap detection upgrade (v4.3)

**Fixes**
- *Time zone:* shift times are now in the employee's **local time** (`hr.employee.tz`, falling back to the
  user's tz, then UTC). Before, the crons compared UTC hours to local shift hours, so a 09:00 shift in Dhaka
  (UTC+6) was checked at 09:00 UTC. Set the time zone on each employee; the assignment form shows the one used.
- *Self-masking alerts:* alerts raised by the crons carry the employee's `person_id`, and used to be counted as
  "sightings", so a left-workstation alert immediately reset the gap it reported. They are now tagged with
  `source_service = cctv_employee_monitor_cron` and ignored everywhere (also in task-delay presence).
- *Alert spam:* late arrival and early departure are raised **once per shift**; left-workstation **once per gap**,
  repeating only after `alert_cooldown_minutes` while the employee is still away.
- The alert text was never stored. It is now saved in the event's `raw_payload` (message, minutes late/away, last seen).
- One failing employee no longer aborts the whole cron run (per-employee savepoint + logging).

**New**
- Scheduled **break window** (`break_start`/`break_end`): never counted as absence, and no left-workstation alert
  fires during it. Leave both at 0 for no break.
- **Working days** (Mon-Sun), **public holidays** (global resource calendar leaves) and **approved time off**
  (`hr.leave`, if the Time Off app is installed) are skipped.
- **Gap scope:** count a detection by *any camera* as present (default) or only by the assigned zone / relevant cameras.
- **Late arrival** is now also raised when the employee *did* show up, but after the grace period (with minutes late).
- **Overnight shifts** (end earlier than start) are supported.
- **Daily summary** gains: scheduled / present minutes, **presence %**, minutes late, minutes left early,
  gap count, total and longest gap, and a **gap detail** list in local time. It is rebuilt hourly for the shift in
  progress and for 6 hours after it ends, so final numbers are always written; a *Rebuild Today's Summary* button
  is on the assignment form. New filters: Late, Left Early, Has Gaps, Presence under 80%.

**Upgrade notes**
- New working-day flags default to all seven days on and the break to none, so existing assignments behave as before
  apart from the time-zone fix. Make sure employees have a time zone set.
- The gap maths lives in `utils/presence.py` (pure Python, easy to unit test).
- `_create_compliance_alert(behavior, message, extra=None)`; the old `severity` argument is accepted but ignored
  (severity is derived from the behaviour in `cctv.event.create`).

## Employee violations, fines & progressive discipline

This is the piece that actually affects pay and discipline, so it's built
around a human-in-the-loop workflow rather than automatic wage deductions -
**AI Detection → Manager Review → HR Approval → (manual) Processing**, matching
the safer pattern most jurisdictions expect. Nothing in this module deducts
anyone's salary automatically.

- **CCTV → Employee Monitoring → Violation Rules**: define a fine/discipline
  matrix per violation type (late arrival, phone use, no helmet, restricted
  entry, etc.), scoped optionally by branch/department/designation, with
  configurable 1st/2nd/3rd/4th+ offense tiers (warning → written warning →
  fine → HR meeting → suspension review → termination review) and a
  points deduction against one of four scores (discipline/safety/attendance/compliance)
- When a matching AI event comes in with an identified employee, a
  `cctv.violation` record is created automatically in **"New (AI Detected)"**
  state and immediately routed to the employee's manager for review - it is
  *never* auto-approved or auto-fined
- **Manager Review → HR Review → Approved → Processed**: each step is a
  separate group-gated action (`action_manager_approve`, `action_hr_approve`,
  `action_mark_processed`); HR can adjust the fine amount at approval time
- **Deduction method** is tracked (warning only / direct salary / installment
  / separate receivable) but this module does **not** integrate with a
  payroll module directly - mark violations "Processed" once you've actually
  applied the deduction in whatever payroll system you use, and use the
  tree view's built-in Export to Excel on `cctv.violation` (filtered to
  `approved`) to hand your payroll process a list
- **Appeals**: `cctv.violation.appeal` gives the employee a place to submit
  an explanation and documents, routed Supervisor Review → HR Decision →
  Closed, with the outcome (upheld/overturned/reduced) flowing back to
  reopen or close the original violation
- **Monthly Leaderboard**: `cctv.employee.monthly.score` starts every
  employee at 100 across all four scores each month and deducts the rule's
  configured points per approved violation - use it for the "best disciplined
  employee" recognition angle, not just the compliance-risk angle
- **Dashboards**: HR (violations by employee), Factory (safety + production
  only), Management (branch comparison) - all pivot/graph views on the same
  `cctv.violation` model, so you can add your own groupings without new code

### Legal context - read before turning on real fines

This is general awareness, not legal advice, and I'm not a lawyer - verify
with local counsel for your actual situation. That said, since you're in
Bangladesh: the **Bangladesh Labour Act 2006, Section 25**, specifically
regulates workplace fines - they must be for acts on a list approved in
advance (and, per the Act, displayed/notified to workers), capped at a small
percentage of wages, and any money collected has to go to a worker welfare
fund rather than general company revenue; wage
deductions generally are also capped under Section 125. Automatic,
undisclosed, or uncapped fines deducted straight from salary are exactly the
scenario that section exists to prevent - which is also why this module
defaults to warning-only/manual-processing rather than doing it for you.
If you operate in multiple countries or serve clients elsewhere, the
equivalent local law will differ and needs its own check.

## Notes on credential security

Camera passwords are stored on the `cctv.camera` record and restricted to the
`group_cctv_admin` field group. For real production deployments, store
credentials in a secrets manager (Vault, AWS Secrets Manager, etc.) and have
your RTSP bridge fetch them at boot, rather than keeping plaintext camera
passwords in any database, including this one.

## Tracking menu upgrade (v4.4)

**New menu layout (CCTV > Tracking):** On Site Now - Visits / Routes - Face Database (People) - Watchlist
(Blacklist & VIP) - Unknown Faces (To Review) - Face Recognition Log - Vehicle Logs (ANPR) - Registered Vehicles.

**Fixes**
- Face recognition never opened a visit (only vehicles or manual entry did), so *Visits / Routes* stayed empty for
  people. A recognised visitor/vendor/VIP/blacklisted person now opens a visit at the camera's site, every later
  sighting refreshes it, and each face event is attached to the visit - this is the camera-to-camera route.
  Employees are skipped (they have attendance); set system parameter `cctv_management.track_employee_visits = 1` to include them.
- Only *unknown* faces raised an alert. A blacklisted person now raises a **critical** alert (at most every 10 min per
  person) and a VIP a low-severity "VIP arrived" alert (every 4 h).
- Vehicle gate events join the linked visit's route, and vehicle visits are marked `source = Vehicle (ANPR)`.

**New features**
- **On Site Now:** everyone with an open visit, grouped by site; bulk *Check Out Selected* action.
- **Visits:** form with status bar, *Check Out* button, route tab (camera to camera), vehicles tab and a one-line
  route summary (e.g. *Lobby → Rack A → Billing*). Filters: On Site Now, Overstayed, Auto-closed, Last 24 h, person type.
  Group by person / site / department / person type / source / day. Pivot and bar-chart views.
- **Auto check-out:** face visits not seen for 120 min are closed at their last sighting (`cctv_management.visit_timeout_minutes`);
  a visit closed < 10 min ago is reopened instead of duplicated (`cctv_management.visit_reopen_minutes`).
- **Overstay alerts:** set *Max Stay (min)* on a person; one alert is raised per visit that runs longer.
- **People:** kanban view with photo, *On site* badge and last-seen; search filters (type, on site, no biometric consent,
  archived); *Last seen* / *Last camera* / *Sightings* stat button on the form.
- **Watchlist:** dedicated list of blacklisted and VIP people.
- **Unknown Faces review queue:** *Enroll as Person* creates a Face Database entry from the stored snapshot (with a 30-day
  biometric retention default); *Mark Reviewed* dismisses it (bulk action available). Add the photo to the AI service
  face gallery so the person is recognised next time.
- **Face log:** filters (To Review, Unknown, Matched, Low Confidence, Last 24 h), grouping, form with snapshot, per-day chart.
- **Vehicle logs:** filters (Parked Now, Unauthorized, Unknown Owner, Last 24 h), grouping, form, *Check Out* button
  and bulk action; plate search ignores spaces/dashes.
- **Registered Vehicles** now has its own menu (search by plate, group by owner).

**Upgrade notes**
- Two new cron jobs: *Auto-close Stale Face Visits* (15 min) and *Visitor Overstay Alerts* (10 min).
- Existing visits keep working: they default to `source = Manual` and are never auto-closed.
- Integer parameters live in Settings > Technical > System Parameters.
- 4.4.1: the Incident and Violation kanban views used the Odoo 18 template name (`card`); on Odoo 17 they crashed with
  "Missing 'kanban-box' template". All kanban views now use `kanban-box`.

## Roadmap for Phase 3 (not built yet)

- Interactive facility map with camera pins + live alarm overlay (section 18) — the `map_x`/`map_y` fields on `cctv.camera` are already there to support this; needs a small OWL SVG/canvas component
- Heat-map analytics view (aggregate `cctv.event` by department/hour — the data model already supports the query, needs a heatmap widget)
- Mobile app screens (Live View, Alerts, Playback, PTZ, incident approval) — separate mobile client project
- Attendance auto check-in/out from `cctv.face.log` matches (a hook into `hr.attendance` is straightforward to add once face matching is live)

## v4.0 additions (gap closing)

**AI Insights & Forecasting** (menu *AI Insights*)
- `cctv.forecast`: hourly visitor forecast per site for the next 7 days, built from the same weekday+hour of the
  last 8 weeks (recency-weighted) x a short-term trend factor. Each row has an 80% range, a confidence score and a
  plain-language *evidence* text; real vs predicted is filled in automatically so accuracy is visible.
- `cctv.insight`: peak hours, branch comparison, unusual traffic day, recurring security events, forecast peak,
  forecast accuracy - each with confidence and evidence. Old runs are archived, not deleted.
- It is a transparent statistical baseline, not machine learning. It needs a few weeks of `cctv.footfall.count`
  data; with fewer than 3 comparable weeks the forecast is labelled low confidence.
- Reporting timezone: System Parameter `cctv_management.report_timezone` (e.g. `Asia/Dhaka`); falls back to the user's.

**Multi-channel alerts, siren, escalation** (Configuration -> Alert Channels)
- Channel types: Telegram bot, WhatsApp Cloud API, HTTP SMS gateway (any provider, URL/body templates),
  generic webhook, siren/relay HTTP endpoint. Each channel has minimum severity, scope (all / security / fire-smoke
  only), site filter, cooldown (anti-flood) and an *escalation level*: level 1+ only fires if the alert is still
  unacknowledged after N minutes. Use **Send Test Message** after configuring.
- Messages carry branch, camera, event time, severity, acknowledgement status and a link; Telegram also sends the snapshot.
- Delivery runs in a cron (triggered immediately on alert creation, retried 3 times) so a slow gateway never blocks the AI
  webhook. Every attempt is in *Notification Log*.
- WhatsApp: Meta only allows business-initiated messages through approved templates outside the 24h window - set the
  template name (5 body variables: alert, branch, camera, time, severity).
- Fire/smoke alerts now use alert type Fire/Smoke, so a channel with scope "Fire / smoke only" can drive a siren relay.
  Camera analytics supplement, and never replace, a certified fire-alarm system.

**Warehouse / ERP link** (Security -> Goods Movement / ERP Links)
- Mark a camera as *Loading Bay* and pick its ERP warehouse. Validated incoming/outgoing transfers are linked to the bay
  camera with a snapshot (smart button on the transfer). Goods/forklift/package movements seen by the camera wait for a
  matching transfer (+/- `cctv_management.goods_match_minutes`, default 60); none => flagged + alert.
- CCTV cannot count stock - this is evidence of movement, not an inventory quantity.

**Vehicles / parking / visitors**: register plates on a person (*Vehicles* tab). ANPR now keeps one open record per plate
(no per-frame duplicates), closes it on an exit gate (camera *Gate Direction*), computes parking time, links the owner
and their visit (auto-created for visitors/vendors/VIPs) and alerts when a blacklisted person's vehicle arrives.

**Recording playback**: set *Playback URL Template* on a camera (MediaMTX example in the field help); events get an
**Open Recording Clip** button and the mobile Playback screen a **Play clip** link.

**Biometric controls**: consent, "keep biometrics until" date, *Erase Biometric Data* button, and a daily purge of face
logs/snapshots older than `cctv_management.face_log_retention_days` (default 30). Delete the person's folder from the AI
service `face_gallery` too - Odoo cannot reach that disk.

New cron jobs: send notifications (1 min), escalate alerts (5 min), forecast (daily), forecast accuracy (hourly),
insights (daily), goods-movement matching (15 min), biometric retention (daily). New dependency: `stock`.


## Live Monitor (v4.1)

- **Auto-fit**: the grid picks the best columns x rows for the number of cameras in the selected
  Live Monitor Grid and the window size (10 cameras -> 4 x 3, short last row centred). The old
  "layout" selection of the grid is no longer needed. Resize the window / enter **Wall** mode and it re-fits.
- **Click a camera** -> full screen. Zoom: mouse wheel, `+` / `-`, buttons, double-click (2.5x), pinch on touch.
  Drag to move when zoomed. `0` = fit, `<-` / `->` = previous / next camera, `Esc` = close.
- **Tracking colours**: GREEN box = tracked and behaving normally, RED box = flagged behaviour
  (loitering, restricted entry, theft suspected, fire/smoke, tamper ... anything other than "none").
  A tile gets a green border while people are tracked and a pulsing red border when something is flagged.
- **Top-left info panel** per monitor: green / red counts, latest flagged events (last 5 min, with age),
  queue length / wait (queue cameras) and today's IN / OUT (people-counting cameras).
  The `Tracking` button hides/shows boxes + panels (remembered per browser).
- Data comes from `cctv.camera.get_live_tracking()` (polled every 3 s, counters every 15 s).

**Upgrade steps**: replace the module, then `odoo -u cctv_management` (adds `track_ref`,
`frame_width`, `frame_height` to `cctv.event`) and hard-refresh the browser (Ctrl+F5).
Restart `cctv_ai_service` so it sends `track_id` + `frame_size` with each detection - without them
the panel and green/red tile colours still work, but boxes are only drawn for events that carry a
frame size, and one tracked person may count more than once.
Boxes line up with the picture when the AI frame and the browser stream have the same aspect ratio
(e.g. both main-stream or both sub-stream of the same camera).

## Dashboard access, filters & map auto-refresh (v4.2)

**Who sees which dashboard** - *CCTV > Configuration > Dashboard Access* (Super Administrators only)
has one row per dashboard under *CCTV > Dashboards*. Pick the allowed groups; saving hides the menu
entry for everyone else. Super Administrators always see all of them, and an empty list means
"admins only". The defaults are role based (e.g. HR Dashboard: HR Manager, Security Manager, Auditor)
and are loaded once, so your changes survive upgrades.

- This controls who can *open* a dashboard, not what they can read inside it - that is still decided by
  the model access rights. The "Reads data from" column shows what each dashboard needs; only add groups
  that can read it. Facility Map / Heat Map tell the user on the page if a group was added without that access.
- Plain *Read Only User* is not in any default list (the Operator and Auditor roles imply it and are). Add it
  per dashboard if you want it.
- Branch Manager and Factory Manager now get read access to Floors and Departments, which the Heat Map needs.

**Filters** - Smart Alerts and Cameras now have search views (status, severity, today, health, site,
group-by...). *Executive* opens on "Today"; *Camera Health* opens grouped by health. The *New* default on
*Smart Alerts* now works too.

**Auto-refresh** - Facility Map (default 30 s) and Heat Map (default 60 s): set the seconds per map on the
same settings page (0 = off, minimum 10). Refresh pauses while the browser tab is hidden, keeps the selected
site, and the page shows "updated hh:mm:ss" with a *Refresh now* button.



## v4.5 - camera sync, AI auto-config, Google Drive
See `../CHANGELOG_v4_5.md` and `../GOOGLE_DRIVE_SETUP.md`. Settings live under **CCTV > Configuration > Settings**.
