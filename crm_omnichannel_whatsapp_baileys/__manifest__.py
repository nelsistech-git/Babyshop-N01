# -*- coding: utf-8 -*-
{
    'name': 'CRM Omni-Channel: WhatsApp (Baileys / QR Connector)',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Unofficial WhatsApp Web (multi-device) connector via a Baileys bridge - no Meta Business approval required',
    'description': """
WhatsApp Baileys Connector
===========================
Adds a second WhatsApp provider option on crm.channel, alongside the
official Cloud API delivered by crm_omnichannel_meta_connector:

* Pair a normal WhatsApp number by scanning a QR code (no Meta Business
  verification, no message templates, no 24-hour session window)
* Live connection status (Disconnected / Waiting for QR / Connected)
  shown as a ribbon on the channel form, same idea as the reference
  "Baileys Whatsapp" connector screen
* Inbound webhook receiver for messages + connection/QR events pushed
  from the bridge microservice (bridge/server.js in this module, a
  small Node.js service using the open-source @whiskeysockets/baileys
  library - this is a SEPARATE PROCESS, Baileys cannot run inside Odoo)
* Outbound send hooked into crm.chat.message, dispatched automatically
  through the shared _send_via_meta() pipeline in crm_omnichannel_meta_connector
* Every inbound/outbound message auto-creates/updates crm.chat.session
  and crm.chat.message exactly like the Cloud API path, so the Chat
  Room UI, SLA, assignment rules and CRM lead auto-creation all work
  identically regardless of which WhatsApp provider is used.

REQUIRES: the bridge/server.js microservice running somewhere reachable
by both this Odoo instance and the internet (see bridge/README.md).
""",
    'author': 'Nelsis Tech',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['crm_omnichannel_hub', 'crm_omnichannel_meta_connector'],
    'data': [
        'views/crm_channel_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
