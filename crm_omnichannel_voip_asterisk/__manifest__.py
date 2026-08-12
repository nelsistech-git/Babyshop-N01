# -*- coding: utf-8 -*-
{
    'name': 'CRM Omni-Channel: IP Calling (Asterisk / OnSIP VoIP)',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Click-to-call and live call-event sync against an Asterisk PBX (AMI + SIP/WebRTC)',
    'description': """
IP Calling (Asterisk) Connector
==================================
Wires crm.call.log up to a real Asterisk PBX:

* Per-channel Asterisk AMI connection settings (host, port, username,
  secret) and SIP/WebRTC settings (SIP domain, WebSocket URL,
  environment) - the same fields shown on the reference VoIP settings
  screen (OnSIP Domain / WebSocket / VoIP Environment)
* Per-agent SIP extension, auth username and secret (res.users), so
  each agent's browser softphone registers as themselves
* action_click_to_call is overridden here to actually originate the
  call through Asterisk's Manager Interface (AMI) instead of only
  creating the CRM record
* Inbound webhook endpoint that an AMI-to-HTTP bridge script
  (bridge/ami_bridge.py, included) forwards Asterisk events to -
  Ringing / Answered / Hold / Hangup - which auto-create and update
  crm.call.log records in real time, exactly like the chat channels
  auto-sync messages
* Call recording files (if Asterisk is configured to record) are
  pulled in and attached as crm.call.recording once the bridge
  reports a recording is ready

REQUIRES: an Asterisk PBX reachable from Odoo with AMI enabled, and
the bridge/ami_bridge.py script (or equivalent) running as its own
long-lived process - AMI is a persistent-socket protocol and doesn't
fit inside a normal Odoo HTTP worker (see bridge/README.md).
""",
    'author': 'Nelsis Tech',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['crm_omnichannel_hub'],
    'data': [
        'views/crm_channel_views.xml',
        'views/res_users_views.xml',
        'views/crm_call_log_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
