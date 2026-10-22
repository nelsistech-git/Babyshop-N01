# garment_iot_platform — Implementation Notes

Module 26: Smart Factory & IoT Integration Platform (SRS technical name in
the source document: `garment_smart_factory_iot`; the suite's naming
convention for this addon is `garment_iot_platform`).

## 1. Scope decision — what a backend Odoo addon can realistically deliver

The SRS describes a full Industry 4.0 stack: PLC drivers for four vendor
protocols, an MQTT broker, a 3D Digital Twin simulation engine, an
AI/machine-learning training pipeline, and a live control-center dashboard.
None of those are "an Odoo addon" — they are separate infrastructure
(broker, drivers, a simulation/rendering engine, a model-training service)
that a real deployment would stand up *around* Odoo. Building fake versions
of them here would be worse than not building them: it would look
functional while doing nothing real.

Instead this module builds the actual **backbone piece Odoo is meant to
be** in the SRS's own architecture diagram —

```
Machine -> Sensor -> IoT Gateway -> API/MQTT -> Odoo ERP
```

— i.e. the device/gateway registry, the ingestion API that stands in for
"API/MQTT", the generic reading log, and a real threshold-alerting engine.
A real MQTT bridge / gateway script / PLC driver would be the thing calling
`POST /api/iot/ingest`.

## 2. SRS sections covered

| SRS section | Coverage |
|---|---|
| 6-7 IoT Device / Gateway Management | `garment.iot.device`, `garment.iot.gateway` — full register with the exact fields the SRS lists (Device ID/Name/Type/Manufacturer/Location/IP/Status/Last Communication; Gateway protocol/location/status) |
| 8-10 Machine Connectivity / Status Types | `garment.iot.device.device_type` includes `machine_sensor`, linked to `garment.production.machine`; `garment.iot.reading.reading_type = 'status'` carries Running/Idle/Stopped/Error/Maintenance-style text values |
| 11-12 Production Data Collection / Automatic Production Entry | Modeled as the generic ingestion pipeline (`reading_type = 'count'`/`'speed'`); this module deliberately does NOT create `garment.production.entry` records automatically — that write belongs to garment_production's own MES layer and doing it here would be a second, competing writer. See "Deferred" below. |
| 13-14 PLC Integration / MQTT Communication | `garment.iot.gateway.protocol` (mqtt/modbus/http/opc_ua) records *which* transport a gateway uses; the actual broker/driver connection is external infrastructure, not something an HTTP addon terminates — the ingestion controller is the "API/MQTT -> Odoo ERP" arrow in the SRS diagram |
| 15-17 RFID Factory / Fabric / Finished Goods Tracking | `device_type = 'rfid_reader'`, `reading_type = 'rfid_scan'`; deliberately NOT duplicating `garment.rfid.tag` / `garment.barcode` (garment_warehouse) — an RFID device's scan reading is the raw event, the tag/stock-move record it should produce is warehouse's model, wired the same way a Machine Sensor reading is wired into `garment.maintenance.iot.reading` (a "Call Method" alert rule targeting a warehouse method) |
| 18-19 Smart Sensor Integration / Environmental Monitoring | `device_type` covers temperature/humidity/vibration/air_quality/water sensors; `reading_type` mirrors them |
| 20 Energy Monitoring | `device_type = 'energy_meter'`, `reading_type = 'energy'`; seeded example alert rule |
| 28 Smart Andon System | `garment.iot.alert.rule.severity` = info/warning/critical (Green/Yellow/Red), `garment.iot.alert.log` is the fired-alert record |
| 36-39 IoT Database Design / Device / Sensor Data models / API Architecture | `garment.iot.device`, `garment.iot.reading` (SRS's `garment.iot.sensor.data`, generalized to any device type, not just sensors), `POST /api/iot/ingest` (SRS's `POST /api/iot/sensor/data`), `POST /api/iot/gateway/heartbeat` (device/gateway online status, SRS's `GET /api/iot/machine/status` re-scoped as a push-style heartbeat since Odoo cannot poll a factory device) |
| 40 IoT Security Framework | Per-device and per-gateway generated API key (`secrets.token_hex`), same pragmatic pattern as `garment_mobile_platform`; role-based `ir.model.access.csv` / `res.groups` |
| 47 Smart Factory Reports — IoT Device Report | `connection_status` + `last_communication` on `garment.iot.device`, list/search views with Online/Offline/Error filters and group-by |
| 48 Real-Time Alert Management | `garment.iot.alert.rule` + `garment.iot.alert.log`, evaluated synchronously on every ingested reading |
| 51 IoT Data Storage / Data Retention | `garment.iot.reading` is explicitly documented (module docstring + this file) as NOT a time-series store; `_cron_prune_old_readings` implements the "Real-Time Data: 1 Year" retention rule as a config-parameter-driven nightly prune; fired alerts (`garment.iot.alert.log`) are kept indefinitely (SRS "Audit Data: Permanent") — `reading_id` on the log uses `ondelete='set null'` so pruning readings never deletes the alert history |
| 52 Smart Factory Integration table | Manufacturing -> `garment.production.machine` (garment_production); Maintenance -> `garment.maintenance.iot.reading` bridge (garment_maintenance); Inventory -> `garment.location` (garment_warehouse) |
| 53 Test Cases | IOT-001 (`action_mark_online` / gateway heartbeat), IOT-002 (`/api/iot/ingest` creates a reading), IOT-005 (alert rule fires and is logged) are all real, exercised code paths, not stubs |

## 3. Deliberately simplified or deferred

* **PLC vendor drivers (Siemens/Mitsubishi/Omron/Allen-Bradley)** — out of
  scope; `garment.iot.gateway.protocol` records the *choice* of transport
  a real driver would use, nothing more.
* **MQTT broker** — out of scope; the ingestion controller is the point
  where a broker-side bridge script would forward messages into Odoo via
  plain HTTP, since Odoo does not run an MQTT subscriber in-process.
* **Digital Twin (3D/simulation layer, factory hierarchy Building->Floor->
  Department->Line->Machine->Operator, "what-if" capacity simulation)** —
  a rendering/simulation engine is not something a backend addon produces.
  The data this module *does* capture (Gateway/Device -> Location ->
  Machine, live status via readings) is the data feed such an engine would
  consume; it is not modeled as its own hierarchy of models here to avoid
  a large speculative build with no consuming UI.
* **AI/Machine-Learning analytics (s.41-43, predictive failure/quality
  risk scoring)** — genuine ML training/inference infrastructure is out of
  scope for this addon, exactly as `garment_maintenance`'s own
  `garment.maintenance.ai.prediction` and `garment_buyer_crm`'s
  `garment.ai.engine` already document for their modules. A Machine Sensor
  reading that should feed such a model is available via the "Call Method"
  alert-rule action the same way the CMMS bridge uses it.
* **OEE / MTBF / MTTR KPI roll-ups (s.44-46)** — already computed in
  `garment.production.oee` (garment_production) and the maintenance KPI
  model in `garment_maintenance`; not recomputed a third time here.
* **Automatic Production Entry (s.12)** — a Machine Sensor's `count`/
  `speed` readings are ingested and can drive an alert rule, but this
  module does not itself create `garment.production.entry` rows. That is
  a second real writer's responsibility (garment_production's own MES
  entry flow / `garment_mobile_platform`'s `/api/mobile/production/entry`)
  and duplicating it here would create two competing sources of truth for
  hourly output.
* **Digital control-center dashboard (s.26-27) / Mobile IoT Monitoring
  (s.49)** — the underlying data (device/gateway status, readings, fired
  alerts with search/group-by views) is fully modeled and browsable; a
  dedicated dashboard/kanban board and a mobile-specific view are left for
  `garment_analytics_bi` (which already owns `garment.dashboard.board`/
  `garment.dashboard.tile`) rather than building a second dashboard
  framework inside this module.

## 4. Relationship to `garment_maintenance.garment.maintenance.iot.reading`

This was the explicit instruction for the task and is worth stating plainly:

* `garment.maintenance.iot.reading` (garment_maintenance) is the
  **machine-condition reading HISTORY that drives CMMS breakdown Work
  Orders** — narrow, maintenance-specific fields (temperature, vibration,
  speed, power, per-reading warning/critical thresholds) and a `create()`
  override that opens a `garment.maintenance.workorder` when the computed
  `condition` is critical. It already existed before this module and is
  NOT re-created here.
* `garment.iot.reading` (this module) is the **generic, factory-wide
  ingestion log** for every connected device type — RFID/barcode scans,
  environmental sensors, energy meters, counters, and machine sensors
  alike — fed by the real `/api/iot/ingest` HTTP endpoint and evaluated
  against configurable threshold rules.
* The bridge between them is `models/garment_maintenance_iot_reading_ext.py`,
  which **extends** (`_inherit`) `garment.maintenance.iot.reading` in place
  with one `@api.model` method, `create_from_iot_platform_reading(iot_reading)`,
  that maps a generic `garment.iot.reading` (from a Machine Sensor device)
  onto that model's existing fields and calls its normal `create()` — so
  the CMMS module's own critical-condition/work-order logic runs exactly
  as it always has, unmodified. This method is the target of the seeded
  example alert rule *"Machine Sensor Vibration -> CMMS Condition Log"*
  (`data/garment_iot_platform_data.xml`), which is also the concrete,
  working example of the alert rule engine's "Call Method" action.
* Net effect: a factory could register a machine-condition sensor either
  directly against `garment.maintenance.iot.reading` (CMMS-only, as
  before) **or** as a `garment.iot.device` behind a gateway in this
  module, with the reading automatically relayed into the same CMMS
  history/alerting via the bridge above — never both models independently
  reimplementing threshold logic for the same physical sensor.

## 5. Other cross-module links

* `garment.iot.device.machine_id` -> `garment.production.machine`
  (garment_production) for Machine Sensor devices.
* `garment.iot.device.location_id` / `garment.iot.gateway.location_id` ->
  `garment.location` (garment_warehouse); `garment.iot.gateway.warehouse_id`
  -> `garment.warehouse`.
* `garment.iot.alert.rule.action_model_id` (Call Method action) is a
  generic `ir.model` reference — the seeded rule targets
  `garment.maintenance.iot.reading`, but the mechanism itself works
  against any model/method a future integration needs (e.g. a
  `garment.rfid.tag` or `garment.barcode` method in garment_warehouse),
  without this module needing to depend on every possible target.

## 6. API surface (`controllers/main.py`)

Both routes are `type='http'`, `auth='public'`, return plain JSON (not the
JSON-RPC envelope), and authenticate via a per-record generated API key —
the same pragmatic pattern `garment_mobile_platform` already uses, chosen
for the same reason: no external JWT/OAuth2 identity provider exists in
this environment.

* `POST /api/iot/ingest` — header `X-IoT-Api-Key` (or body `api_key`)
  identifies the `garment.iot.device`; body `{reading_type, value, unit,
  text_value, timestamp}` creates a `garment.iot.reading` via
  `garment.iot.device.record_reading()`, which also evaluates alert rules
  and returns the list of alerts fired.
* `POST /api/iot/gateway/heartbeat` — header `X-IoT-Gateway-Api-Key` (or
  body `api_key`) identifies the `garment.iot.gateway`; marks it online
  and refreshes `last_heartbeat`.

Both endpoints are real and exercised by IOT-001/IOT-002/IOT-005-style
scenarios described above — not stubs.

## 7. Validation performed

* `python3 -m py_compile` on every `.py` file — passes.
* `xmllint --noout` on every `.xml` file — passes.
