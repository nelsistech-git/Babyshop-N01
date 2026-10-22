# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 24: Mobile Application Platform
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Mobile Application Platform',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Server-side enablement layer (device registry, push notification log, session audit, '
               'offline sync log and a JSON REST API) for the Android/iOS/PWA mobile clients',
    'description': """
Smart Complete Garment Software — Mobile Application Platform
================================================================
Module 24 of the Smart Complete Garment Software suite.

IMPORTANT SCOPING NOTE
-----------------------
A native Android/iOS application cannot be built as part of an Odoo server
addon. This module realistically scopes "Module 24" as the **server-side
enablement layer** a real mobile/PWA client would call into: device
registration, a pragmatic API-key auth scheme, a push-notification log/queue,
a login/session audit trail, an offline-sync audit log, and a small set of
real, working JSON REST endpoints against the ERP's actual production/quality/
TNA data. See ``IMPLEMENTATION_NOTES.md`` for exactly what is a working
endpoint vs. a documented stub/integration point.

Key Features
------------
* Mobile Device Registry (``garment.mobile.device``) — one record per
  registered device per user: platform (Android/iOS/Web PWA), app area
  (Executive / Employee ESS / Merchandising / Production / QC / Warehouse /
  HR / Finance), push token, app version, a generated API key, block/
  activate control and last-seen tracking (SRS s.36, s.52 — Mobile Device
  Management)
* Push Notification Log (``garment.mobile.push.notification``) — typed
  notification queue (Management/Production/Quality/Maintenance/Approval/
  Attendance/TNA/General alerts) with a send-state machine. The actual push
  delivery call to FCM (Android) / APNs (iOS) is a clearly marked TODO stub
  — it requires external provider credentials this environment does not
  have (SRS s.26, s.51)
* Mobile Session Audit (``garment.mobile.session``) — login/logout audit
  trail per device: login method (password/OTP-mobile/OTP-email/biometric),
  IP address, session duration (SRS s.20, s.23, s.39, s.52)
* Offline Sync Log (``garment.mobile.offline.sync.log``) — audit trail of
  records captured offline on the device (production entries, QC
  inspections, attendance, warehouse scans, checklists) and synced back to
  the ERP once connectivity returns, including the raw payload for replay/
  audit (SRS s.24-25, s.48, MOB-003 test case)
* JSON REST API (``/api/mobile/...``) — simple API-key auth (no JWT/OAuth
  server available in this environment), 5 real working endpoints:
  login + device registration, today's TNA tasks, shop-floor production
  count entry, QC barcode scan + inspection log, and the notification inbox
  — wired against the real ``garment.production.entry``, ``garment.tna``/
  ``garment.tna.activity``, ``garment.quality.inspection`` and
  ``garment.barcode`` models (SRS s.13, s.15-17, s.21-22, s.28, s.51)

Cross-Module Integration
-------------------------
* Production Entry — ``garment.production.entry`` (Production Management &
  MES, ``garment_production``)
* TNA / TNA Activity — ``garment.tna`` / ``garment.tna.activity``
  (``garment_tna``)
* Quality Inspection / Defect / Barcode — ``garment.quality.inspection``,
  ``garment.quality.defect`` (``garment_quality``) and ``garment.barcode``
  (``garment_warehouse``)
* Employee — ``garment.hr.employee`` (``garment_hr``)
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'garment_production',
        'garment_quality',
        'garment_tna',
        'garment_hr',
    ],
    'data': [
        'security/garment_mobile_platform_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/garment_mobile_device_views.xml',
        'views/garment_mobile_push_notification_views.xml',
        'views/garment_mobile_session_views.xml',
        'views/garment_mobile_offline_sync_log_views.xml',
        'views/garment_mobile_platform_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
