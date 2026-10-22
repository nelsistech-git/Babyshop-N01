# -*- coding: utf-8 -*-
{
    'name': 'Smart CCTV Management',
    'version': '17.0.4.6.0',
    'category': 'Operations/Security',
    'summary': 'Multi-site/multi-showroom CCTV monitoring, AI event intake, people counting, heatmaps, '
               'queue & theft detection, POS sync, incidents, employee monitoring, violations/fines',
    'description': """
Smart CCTV Management for Odoo 17 Community
=============================================
- Company / Office / Floor / Department / Camera hierarchy (unlimited depth)
- Camera registry for ONVIF/RTSP/NVR/DVR/IP cameras of any brand
- Live monitoring grid (1/4/9/16/25/36+ layouts) driven by an HLS/MJPEG bridge URL,
  plus a Facility Map (camera pins with live status) and department x hour Heat Map
  (raw RTSP cannot play in a browser - see README for the MediaMTX/go2rtc bridge)
- AI Event intake via REST webhook (/cctv/api/event) so an external computer-vision
  service (YOLO/DeepSORT/InsightFace/ANPR) can push detections in real time
- Human behaviour, PPE compliance, warehouse behaviour, vehicle (ANPR), face
  recognition and visitor-tracking event categories
- Security incident workflow (Open -> Investigation -> Action -> Closed)
- Smart alerts routed through Odoo mail (extendable to SMS/WhatsApp/Telegram)
- Employee monitoring: zone/shift assignments, late-arrival/early-departure/
  left-workstation detection, daily activity summaries, task-delay detection
  tied to project.task
- Employee violation & fine engine: configurable offense-tier rule matrix,
  human-in-the-loop Manager Review -> HR Review -> Approved -> Processed
  workflow (no automatic wage deduction), appeals, and a monthly discipline/
  safety/attendance/compliance score leaderboard
- Role based access: Super Admin, Security Director, Security Manager,
  CCTV Operator, HR Manager, Factory Manager, Branch Manager, Receptionist,
  Auditor, Read Only
- Executive / Operations / HR / Factory / Management / Analytics dashboards, with per-dashboard
  access groups (Configuration > Dashboard Access) and auto-refreshing Facility / Heat Maps
- PDF/Excel-ready reports (QWeb)

Retail / Multi-Showroom AI Suite (v3.0)
----------------------------------------
- People Counting: entry/exit footfall per camera, per interval, with daily
  totals and a running "customers inside now" figure
- Heatmap Analytics: rendered zone/rack popularity overlays + per-zone dwell
  and traffic-share stats, pushed by the AI service on a rolling schedule
- Queue Monitoring: live billing-counter crowding + estimated wait time,
  auto-alerts when a counter is overcrowded past a configurable threshold
- Theft / Suspicious Activity Detection: rule-based flags for loitering +
  concealment gestures + after-hours presence in retail zones, escalating
  straight to a Theft incident
- Tamper Detection: alerts when a camera is blocked, physically moved, or
  goes out of focus
- POS Integration: every POS sale is auto-linked to the camera watching that
  till, with a timestamped snapshot and any correlated suspicious event
- Universal camera onboarding: any ONVIF/RTSP camera (any brand, including
  existing/legacy CCTV already installed) can be added to the AI pipeline -
  the AI runs in the external cctv_ai_service, not on the camera itself

v4.6 "Aurora" UI
----------------
- Command Center landing dashboard (KPI cards, 24h activity, camera health donut, alerts)
- Modern colourful theme: 3D icon tiles, 3D buttons, glossy cards on every CCTV screen

v4.0 additions
--------------
- AI Insights & Forecasting: hourly visitor forecast per site with confidence,
  80% range and evidence; peak hours, branch comparison, traffic anomalies,
  recurring security events; forecast accuracy tracking
- Multi-channel alerts: Telegram, WhatsApp Cloud API, HTTP SMS gateway, webhook,
  siren/relay; delivery log, cooldown, escalation of unacknowledged alerts
- Warehouse ERP link: goods movements at loading bays matched to stock transfers
- Vehicle (ANPR) entry/exit bookkeeping linked to people, visits and parking time
- Recording playback links from any AI event (MediaMTX or other playback server)
- Biometric controls: consent, retention limits, automatic and on-demand erasure
""",
    'author': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nur Uddin Ahammed',
    'depends': ['base', 'mail', 'hr', 'project', 'point_of_sale', 'stock'],
    'external_dependencies': {'python': ['requests', 'pytz']},
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cctv_data.xml',
        'data/cctv_v4_data.xml',
        'data/cctv_tracking_data.xml',
        'data/cctv_update_data.xml',
        'views/cctv_office_views.xml',
        'views/cctv_camera_views.xml',
        'views/cctv_live_monitor_views.xml',
        'views/cctv_event_views.xml',
        'views/cctv_alert_views.xml',
        'views/cctv_incident_views.xml',
        'views/cctv_person_views.xml',
        'views/cctv_vehicle_views.xml',
        'views/cctv_face_views.xml',
        'views/cctv_tracking_views.xml',
        'views/cctv_employee_monitor_views.xml',
        'views/cctv_violation_rule_views.xml',
        'views/cctv_violation_views.xml',
        'views/cctv_violation_appeal_score_views.xml',
        'views/cctv_footfall_views.xml',
        'views/cctv_heatmap_views.xml',
        'views/cctv_queue_views.xml',
        'views/cctv_pos_link_views.xml',
        'views/cctv_dashboard_views.xml',
        'views/cctv_menus.xml',
        'views/cctv_command_center_views.xml',
        'views/cctv_v4_views.xml',
        'views/cctv_dashboard_access_views.xml',
        'views/cctv_update_views.xml',
        'data/cctv_dashboard_access_data.xml',
        'report/cctv_reports.xml',
        'report/cctv_report_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cctv_management/static/src/js/live_monitor_utils.js',
            'cctv_management/static/src/js/live_monitor.js',
            'cctv_management/static/src/js/dashboard_utils.js',
            'cctv_management/static/src/js/facility_map.js',
            'cctv_management/static/src/js/heat_map.js',
            'cctv_management/static/src/js/command_center.js',
            'cctv_management/static/src/xml/live_monitor_templates.xml',
            'cctv_management/static/src/xml/facility_map_templates.xml',
            'cctv_management/static/src/xml/heat_map_templates.xml',
            'cctv_management/static/src/xml/command_center_templates.xml',
            'cctv_management/static/src/scss/cctv.scss',
            'cctv_management/static/src/scss/cctv_theme.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
