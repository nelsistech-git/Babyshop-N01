# -*- coding: utf-8 -*-
{
    'name': 'CRM Omni-Channel: Connect Center (WhatsApp QR + Facebook OAuth + VoIP)',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'One-click WhatsApp QR pairing (multi-number), Facebook Page OAuth connect, and Asterisk '
               'VoIP line setup, with a live status dashboard and real connection diagnostics.',
    'description': """
CRM Omni-Channel - Connect Center
==================================
Adds the "easy connect" layer on top of crm_omnichannel_whatsapp_baileys,
crm_omnichannel_meta_connector and crm_omnichannel_voip_asterisk:

* Settings > Omnichannel > Connections - one screen, live status badges for
  every WhatsApp number, Facebook Page and VoIP calling line, with a
  "Test Connection" button that calls the real bridge / Graph API / AMI and
  shows the actual error instead of failing silently.
* WhatsApp: "Add Number" wizard - auto-generates the session, starts
  pairing, and shows a QR code that AUTO-REFRESHES every ~2.5s (no manual
  form reload) until the phone scans it and it flips to Connected. Repeat
  for as many numbers as you want.
* Facebook: "Connect Facebook Pages" - Facebook Login popup, lists every
  Page the logged-in user manages, and a single click per Page fetches its
  Page Access Token, auto-subscribes the app to that Page's messaging
  webhook via the Graph API, and creates the crm.channel record. No manual
  token copy/paste.
* VoIP: "Add Calling Line" wizard - enter your Asterisk AMI host/port/
  username/secret once (or reuse the defaults set in Settings), click
  Test & Connect, and it verifies BOTH the AMI login itself AND the
  ami_bridge.py event bridge's health endpoint in one step, then creates
  the crm.channel record - instead of saving blind and only discovering a
  typo the next time a call rings.

REQUIREMENTS (cannot be automated away - these are Meta/WhatsApp/Asterisk
platform rules, not limitations of this module):
* A Meta App (App ID + App Secret) with the Facebook Login and Webhooks
  products added - enter these once in Settings > Omnichannel > Connections.
* The App's Webhook callback URL + Verify Token must be pasted into the
  Meta App Dashboard ONE TIME (Meta does not expose an API to do this
  step for you) - Settings shows you the exact values to paste.
* The Baileys bridge (bridge/server.js) and the AMI bridge (ami_bridge.py)
  must each be running as their own long-lived process, reachable by Odoo
  - see BRIDGE_SETUP.md included in this module for copy-paste Docker/
  PM2/systemd setups for both.
""",
    'author': 'Nelsis Tech',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['crm_omnichannel_hub', 'crm_omnichannel_meta_connector', 'crm_omnichannel_whatsapp_baileys',
                'crm_omnichannel_voip_asterisk'],
    'data': [
        'security/ir.model.access.csv',
        'views/whatsapp_connect_wizard_views.xml',
        'views/voip_connect_wizard_views.xml',
        'views/connect_dashboard_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_omnichannel_connect_center/static/src/js/wa_qr_live.js',
            'crm_omnichannel_connect_center/static/src/js/facebook_connect.js',
            'crm_omnichannel_connect_center/static/src/xml/templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
