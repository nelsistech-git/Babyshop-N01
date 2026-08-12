# -*- coding: utf-8 -*-
{
    'name': 'CRM Omni-Channel - Meta (Facebook / Instagram / WhatsApp) Connector',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Webhook receiver and send-API bridge for Facebook Messenger, Instagram and WhatsApp',
    'description': """
CRM Omni-Channel - Meta Connector
==================================
Bridges Facebook Messenger, Instagram Direct Messages and WhatsApp Business
(all via Meta's Graph API) into the crm.channel / crm.chat.session /
crm.chat.message models provided by crm_omnichannel_hub.

IMPORTANT - READ BEFORE GOING LIVE
-----------------------------------
This module was written against Meta's *publicly documented* webhook and
Send API payload shapes. Meta has changed these payload structures between
API versions in the past (and the exact shape used for Instagram DMs in
particular has shifted more than once). It has not been exercised against
a live Meta App / webhook in this environment. Before relying on it in
production:

1. Create a Meta App, enable the Messenger / Instagram / WhatsApp products.
2. Point the webhook URL at ``https://<your-odoo>/omni/webhook/meta`` and
   use the Verify Token you set on the relevant crm.channel record.
3. Send a real test message from each channel and check
   Settings > Technical > Logs (or the server log) for the raw payload
   Odoo received, and compare it against what ``_process_*`` expects in
   ``controllers/meta_webhook.py``. Adjust the parsing there if Meta's
   current payload differs.
4. Confirm outbound sends (agent replies) actually arrive on the customer's
   side - check the Graph API response captured in the chatter log on the
   crm.chat.message record.

What this module DOES do out of the box:
* Signature-verifies every inbound webhook call (HMAC-SHA256 against the
  App Secret you configure per channel) and rejects anything that fails.
* Deduplicates inbound messages using the platform's own message ID, since
  Meta retries webhook deliveries.
* Creates/updates crm.chat.session and crm.chat.message automatically,
  which then flows into the existing auto-lead-creation, SLA and
  dashboard logic from crm_omnichannel_hub with no further changes needed.
* Sends agent replies back out via the Send API / WhatsApp Cloud API.
""",
    'author': 'Nelsis Tech',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['crm_omnichannel_hub'],
    'data': [
        'views/crm_channel_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
