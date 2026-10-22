# garment_mobile_platform — Implementation Notes

Module 24 of the Smart Complete Garment Software suite: **Mobile
Application Platform**, built against
`specs_txt/Mobile Application Platform.txt` (all three parts).

## Scoping decision (read this first)

A native Android/iOS application cannot be built as part of an Odoo server
addon. This module is deliberately scoped, per the build instruction, as the
**server-side enablement layer** a real mobile/PWA client would call into:
a device registry, a pragmatic API-key auth scheme, a push-notification
log/queue, a login/session audit trail, an offline-sync audit log, and a
small set of real JSON REST endpoints wired to existing ERP models. It does
not attempt to model the eight separate "mobile applications" (Executive,
ESS, Merchandising, Production, QC, Warehouse, HR, Finance) as eight
different Odoo apps — one `app_type` field on `garment.mobile.device`
records which app area a device belongs to, and the API endpoints are the
actual integration surface any of those eight client apps would call.

## What is a WORKING endpoint vs. a STUBBED integration point

### Working (real logic, real read/write against real models)

| Endpoint | Method | What it does |
|---|---|---|
| `/api/mobile/auth/login` | POST | Authenticates the ERP user (`res.users`), registers/updates the calling `garment.mobile.device` (platform, push token, app version, API key), opens a `garment.mobile.session` audit row, returns the device's API key. |
| `/api/mobile/tna/tasks/today` | GET | Queries `garment.tna.activity` for today's `planned_end_date`, scoped to the calling user as `responsible_person_id` or as the TNA's `merchandiser_id` (pass `?all=1` to lift the scoping) — SRS s.12 "TNA Calendar". |
| `/api/mobile/production/entry` | POST | Creates a real `garment.production.entry` (shop-floor output/target/reject/rework count) and a `garment.mobile.offline.sync.log` audit row — SRS s.13-14 "Output Entry" / s.24-25 offline production sync. |
| `/api/mobile/qc/scan` | POST | Looks up the scanned code against `garment.barcode`, creates a real `garment.quality.inspection` (+ a `garment.quality.defect` line when a defect quantity is passed) and a `garment.mobile.offline.sync.log` audit row — SRS s.15/s.28 "Barcode & QR Integration" / QC inspection. |
| `/api/mobile/notifications` | GET | Lists (and can mark-read via `?mark_read_id=`) the calling user's `garment.mobile.push.notification` inbox — SRS s.51 Notification API. |

All five run under `auth='public'` and do their own authorization: the
`X-Mobile-Api-Key` header (or an `api_key` field) is resolved to an active
`garment.mobile.device`, and the ERP call executes as that device's linked
`res.users` (`request.env(user=...)`) — never as the public user. A
missing/invalid/blocked-device key returns HTTP 401. See the module
docstring in `controllers/main.py` for the full auth-scheme writeup.

### Stubbed integration point (documented TODO, not working)

* **Outbound push delivery** (`garment.mobile.push.notification._send_via_fcm`
  / `_send_via_apns`): the notification **log/queue itself is fully
  working** — rows are created, listed via the API, and state-tracked
  (queued/sent/failed/read). The actual outbound call to Firebase Cloud
  Messaging (Android) or Apple Push Notification Service (iOS) is **not**
  implemented — both methods raise a documented `NotImplementedError` with
  a TODO explaining exactly what credentials (FCM service-account JSON /
  APNs auth key) and API call need to be added. `action_send()` catches
  that and records the notification as `failed` with the explanatory
  message, rather than pretending to have delivered it.

### Not built at all (out of scope for this pass, and why)

* **OAuth 2.0 / JWT / WebSocket** (SRS s.22): no external identity-provider
  or token-signing infrastructure is available in this environment. The
  API-key scheme above is the pragmatic, working substitute — documented in
  `controllers/main.py`.
* **OTP login, biometric login, face-verification GPS attendance** (SRS
  s.23, s.41.1, s.46): `garment.mobile.session.login_method` models these
  as data (otp_mobile/otp_email/biometric are valid values a client can
  report), but no SMS/OTP gateway or biometric SDK integration exists here
  — only password login is actually implemented server-side.
  `garment_hr.garment_hr_attendance` already has the attendance model this
  would eventually write into; no new attendance model was added here.
* **WhatsApp Business API / SMS Gateway** (SRS s.27): would be a delivery
  channel for `garment.mobile.push.notification`, same "needs external
  credentials" situation as FCM/APNs — not built, not stubbed separately
  (the push stub covers the pattern).
* **Executive / Production / QC / Warehouse / HR / Finance mobile
  dashboards** (SRS s.6, s.13.3, s.32, s.41.2-41.3, s.50): this module is
  the server-side API/data layer, not the client-side dashboard UI. No new
  "dashboard" model was added — an executive dashboard screen would read
  directly from `garment.production.entry`, `garment.quality.inspection`,
  `garment.finance` models etc. via additional read-only endpoints in a
  later pass, once a concrete dashboard client exists to consume them.
* **AI Executive/Voice Assistant, AI Photo Analysis** (SRS s.8, s.31,
  s.42-44): this suite's established pattern for "AI" is a manual/API log
  model per module (e.g. `garment.quality.ai.analysis` in `garment_quality`,
  `garment.ie.ai.insight` in `garment_ie_management`) — no such log was
  added here since no mobile-specific AI feature was in the explicit build
  scope; a future pass could add `garment.mobile.ai.insight` following that
  same pattern.
* **Mobile Approval Center** (SRS s.7, s.34, s.19): every approvable
  document already has its own approval model in its owning module
  (`garment.purchase.approval`, `garment.hr.leave`, `garment.finance`
  payment approvals, `garment.production.approval`, etc.) — a unified
  mobile "approval inbox" endpoint that reads across all of them was judged
  out of scope for this pass; `garment.mobile.push.notification` with
  `notification_type='approval'` is the hook a future endpoint would use to
  surface them.
* **Geolocation / RFID / document OCR scanner** (SRS s.29, s.45, s.47): no
  models or endpoints added — these need device-side SDKs (GPS, RFID
  reader, OCR) this server-side module has no way to exercise; the offline
  sync log's generic `payload` field can carry that data once a client
  sends it.

## Mobile Database Models (SRS s.37) — mapping to what was actually built

The SRS's suggested model list (`garment.mobile.user`, `garment.mobile.device`,
`garment.mobile.notification`, `garment.mobile.sync`, `garment.mobile.token`,
`garment.mobile.approval`) was consolidated to match the concrete build
instruction and avoid duplicate concepts already present in `res.users` /
existing approval models:

* `garment.mobile.device` — built as specified, plus carries `api_key`
  in place of a separate `garment.mobile.token` model (the key **is** the
  token, one per device, generated on that device's row — no separate
  token table needed).
* `garment.mobile.push.notification` — built (SRS's `garment.mobile.notification`).
* `garment.mobile.session` — built (new; SRS s.20/23/39/52 login/session
  audit was implied but not given its own model in s.37 — added because
  s.52 explicitly asks for "Active Sessions" and "Remote Logout").
* `garment.mobile.offline.sync.log` — built (SRS's `garment.mobile.sync`,
  renamed/expanded to match the explicit build instruction and carry a
  `sync_type`/`payload`/`sync_status` audit shape instead of a generic log).
* `garment.mobile.user` — **not** built as a separate model. Every device
  already carries `user_id` (`res.users`) and an optional `employee_id`
  (`garment.hr.employee`); a standalone "mobile user" record would just
  duplicate `res.users` with the four fields the SRS lists
  (`user_id`, `device_id`, `app_type`, `last_login`, `status`) — all four
  already live on `garment.mobile.device`.
* `garment.mobile.approval` — not built; see "Mobile Approval Center" above.

## Cross-module models linked to (none redefined)

* `garment.production.entry` — Production Management & MES (`garment_production`),
  written to by `/api/mobile/production/entry`.
* `garment.tna` / `garment.tna.activity` — TNA (`garment_tna`), read by
  `/api/mobile/tna/tasks/today`.
* `garment.quality.inspection` / `garment.quality.defect` /
  `garment.quality.defect.code` — Quality (`garment_quality`), written to by
  `/api/mobile/qc/scan`.
* `garment.barcode` — Warehouse (`garment_warehouse`, reachable transitively
  through `garment_production`/`garment_quality`'s own dependency chain;
  not re-declared as a direct `depends` entry since this module never
  installs standalone against `garment_warehouse` only — see note below),
  looked up (not modified structurally, only its scan-tracking fields are
  updated) by `/api/mobile/qc/scan`.
* `garment.hr.employee` — HR (`garment_hr`), optionally linked from
  `garment.mobile.device` and used as the default operator on mobile
  production entries.

**Note on `garment.barcode`**: it lives in `garment_warehouse`, which is not
in this module's `depends` list (the build instruction scoped depends to
`garment_production`, `garment_quality`, `garment_tna`, `garment_hr` only).
`garment.barcode` is looked up defensively (`env['garment.barcode'].sudo().search(...)`,
with a `barcode_found: false` fallback in the JSON response) so the QC-scan
endpoint degrades gracefully — still logging a real inspection off the
scanned code as free text — if `garment_warehouse` happens not to be
installed in a given deployment. If `garment_warehouse` is always installed
alongside this suite in practice, add it to `depends` for a hard guarantee.

## Security

Three groups (`security/garment_mobile_platform_security.xml`):
`group_mobile_user` (implicit via `base.group_user`, read-only), 
`group_mobile_admin` ("IT Administrator" — device/session/notification/sync
management), `group_mobile_manager` ("Mobile Platform Manager", full access
incl. unlink, implies admin). All four models have access rows for all
three tiers in `security/ir.model.access.csv`.

## Validation performed

* `python3 -m py_compile` on every `.py` file — no errors.
* `xmllint --noout` on every `.xml` file — no errors.
* Every model has `ir.model.access.csv` rows (4 models x 3 rows = 12 rows).
* Every `action="..."` used in the menu file resolves to an
  `ir.actions.act_window` defined in a `views/*.xml` file loaded before the
  menu file in `__manifest__.py`'s `data` list.
* Every `groups="..."` reference resolves to a group defined in
  `security/garment_mobile_platform_security.xml`.
* No deprecated `attrs=`/`states=` view syntax was used — all
  Odoo 17 direct-attribute expressions (`invisible="..."`, `readonly="..."`).
* Controller auth: `request.session.authenticate()`'s exact signature has
  varied slightly across Odoo 17.0 point releases; `_authenticate_credentials()`
  tries the modern credential-dict form and falls back to the classic
  positional form. This could not be exercised against a live Odoo 17
  database in this environment (no `odoo` package installed here — only
  syntax validation was possible) — verify this call against the actual
  target Odoo 17.0 build before relying on it in production.
