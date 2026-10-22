# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 26: Smart Factory & IoT Integration Platform
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Smart Factory & IoT Integration Platform',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Factory-wide IoT gateway/device registry, generic sensor reading log, '
               'threshold alert rules and a real JSON ingestion API for connected shop-floor devices',
    'description': """
Smart Complete Garment Software — Smart Factory & IoT Integration Platform
=============================================================================
Module 26 of the Smart Complete Garment Software suite.

IMPORTANT SCOPING NOTE
-----------------------
The source SRS describes a full Industry 4.0 stack — PLC integration, MQTT
brokers, a Digital Twin simulation engine, an AI machine-learning analytics
platform and a live control-center dashboard. Those pieces need external
infrastructure (an MQTT broker, PLC drivers, a simulation/3D engine, a model
training pipeline) that does not exist inside an Odoo Community addon. This
module realistically scopes Module 26 as the **factory-wide IoT device/
gateway management layer and data-ingestion backbone** a real Digital Twin /
MQTT bridge / AI engine would sit on top of:

* A Gateway and Device register modelling the SRS's own architecture diagram
  (Machine -> Sensor -> IoT Gateway -> API/MQTT -> Odoo ERP).
* A generic, lightweight reading log fed by a REAL, working JSON HTTP
  ingestion endpoint (``/api/iot/ingest``) that a gateway/MQTT-bridge script
  would call, using the same pragmatic device-API-key auth pattern already
  used by ``garment_mobile_platform``.
* A threshold-based Alert Rule engine evaluated synchronously against every
  incoming reading, with a fired-alert log — the working implementation of
  SRS s.28 (Smart Andon), s.48 (Real-Time Alert Management) and IOT-005.
* Deliberately NOT a duplicate of ``garment.maintenance.iot.reading``
  (garment_maintenance) — that model is the machine-condition reading
  HISTORY feeding CMMS breakdown work orders. This module's
  ``garment.iot.reading`` is the generic, cross-device (RFID / barcode /
  environment / energy / counter / machine sensor) ingestion log; a
  ``garment.iot.device`` of type Machine Sensor can be linked to a
  ``garment.production.machine`` and its readings can drive the creation of
  a ``garment.maintenance.iot.reading`` row for CMMS alerting instead of
  re-implementing that logic. See IMPLEMENTATION_NOTES.md.
* Explicitly NOT a time-series database: ``garment.iot.reading`` is a plain
  PostgreSQL table meant for periodic/aggregated readings and the data that
  fed an alert, not true high-frequency (sub-second) telemetry — a
  production deployment would ingest raw high-frequency data into a
  dedicated time-series store (InfluxDB / TimescaleDB) and only forward
  aggregates/exceptions into Odoo. See IMPLEMENTATION_NOTES.md.
* PLC-specific protocol drivers (Siemens/Mitsubishi/Omron/Allen-Bradley),
  the MQTT broker itself, the Digital Twin 3D/simulation layer and the
  Machine-Learning model training pipeline are out of scope for a backend
  addon and are documented as deferred, not silently dropped.

Key Features
------------
* IoT Gateway Register (``garment.iot.gateway``) — physical gateway/hub per
  factory location: protocol (MQTT / Modbus / HTTP / OPC-UA), IP/port,
  connection status and last-heartbeat, with the devices attached to it
  (SRS s.6-7, s.36 IoT Gateway model).
* IoT Device Register (``garment.iot.device``) — sensor/device master:
  RFID reader, barcode scanner, temperature/humidity/vibration/air-quality
  sensor, energy meter, machine sensor, counter, PLC node; linked to a
  Gateway and, optionally, to a ``garment.production.machine`` or a
  ``garment.location`` (SRS s.6, s.18, s.37 IoT Device model).
* Generic Reading Log (``garment.iot.reading``) — device, reading type,
  numeric value + unit, optional text/tag payload, timestamp; fed by the
  real ingestion API (SRS s.38 Sensor Data model, s.51 Data Storage).
* Threshold Alert Rules (``garment.iot.alert.rule``) — per device or per
  device-type + reading-type comparisons (>, >=, <, <=, ==, !=) with a
  configurable action: create an activity, post a chatter message on the
  device, or call a method on another model — plus the fired-alert log
  (``garment.iot.alert.log``) (SRS s.28 Smart Andon, s.48 Real-Time Alert
  Management, IOT-005).
* Real JSON ingestion controller (``controllers/main.py``) —
  ``POST /api/iot/ingest`` (device API-key auth) creates a reading and
  evaluates alert rules against it; ``POST /api/iot/gateway/heartbeat``
  updates a gateway's live connection status (SRS s.39 IoT API
  Architecture, IOT-001/IOT-002/IOT-005 test cases).

Cross-Module Integration
-------------------------
* Machine link — ``garment.production.machine`` (garment_production)
* Machine-condition alerting handoff — ``garment.maintenance.iot.reading`` /
  ``garment.maintenance.workorder`` (garment_maintenance) — NOT duplicated,
  see IMPLEMENTATION_NOTES.md
* Factory location — ``garment.location`` / ``garment.warehouse``
  (garment_warehouse)

See IMPLEMENTATION_NOTES.md for the full duplication-avoidance rationale and
the list of SRS sections deliberately simplified or deferred.
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'garment_maintenance',
        'garment_production',
        'garment_warehouse',
    ],
    'data': [
        'security/garment_iot_platform_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/garment_iot_platform_data.xml',
        'views/garment_iot_gateway_views.xml',
        'views/garment_iot_device_views.xml',
        'views/garment_iot_reading_views.xml',
        'views/garment_iot_alert_log_views.xml',
        'views/garment_iot_alert_rule_views.xml',
        'views/garment_iot_platform_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
