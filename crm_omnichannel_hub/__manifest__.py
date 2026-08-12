# -*- coding: utf-8 -*-
{
    'name': 'CRM Omni-Channel Communication Hub',
    'version': '17.0.1.8.0',
    'category': 'Sales/CRM',
    'summary': 'Unified inbox, call center, auto lead creation, SLA & agent performance for CRM communications',
    'description': """
CRM Omni-Channel Communication Hub (Phase 1 + 3 + 4 - Core, Call Center & Dashboards)
=======================================================================================
This module implements the core, self-contained foundation of the Omni-Channel
CRM Communication Suite:

* Unified inbox (crm.chat.session) with filters, priorities and tags
* Three-panel Chat Room UI (conversation list, WhatsApp-style thread with
  sent/delivered/read ticks and date separators, contextual right-hand
  panel with live Contact / CRM / Sales / Deliveries / History tabs that
  gracefully degrade if Sales, Invoicing or Inventory aren't installed) -
  plus star/favorite, Reply vs. internal Note, real file/image attachments,
  emoji picker, quick replies, and one-click Convert to Lead / Close /
  Reopen / Spam - alongside the classic list/kanban views
* Call Center (crm.call.log) with lifecycle actions, disposition / after-call-work,
  call recording storage and Click-to-Call from Contacts and Leads
* Automatic CRM Lead creation / customer matching (chat and calls)
* Configurable assignment rules - keyword match, VIP customer, working-hours
  windows, and channel/team routing - falling back to round-robin
* Round-robin agent assignment (independent queues for chat and calls)
* SLA policy engine with green/yellow/red response status and escalation
* Agent response-time and call performance tracking
* Role based access: Agent / Supervisor / Manager
* Customer communication timeline embedded on CRM Lead
* Quick Reply (canned response) library
* Executive, Manager and Agent dashboards (KPI cards + team leaderboard)
* Printable PDF reports (Call Detail Report, Conversation Transcript) and
  Daily/Weekly/Monthly/Yearly grouping on all list/pivot reports
* Customer Satisfaction (CSAT) surveys - one click sends a public rating
  link through the customer's most recent conversation; results roll up
  into the Executive Dashboard

External channel connectors (WhatsApp, Facebook Messenger, Instagram, IP
Calling / Race Online) are delivered as separate add-on modules that plug
into the crm.channel / crm.chat.session / crm.chat.message / crm.call.log
models defined here, once live API credentials and webhook endpoints are
available.
""",
    'author': 'Nelsis Tech',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'crm', 'contacts'],
    'data': [
        'security/omni_security_groups.xml',
        'security/omni_record_rules.xml',
        'security/ir.model.access.csv',
        'data/crm_channel_data.xml',
        'data/sla_cron.xml',
        'views/crm_channel_views.xml',
        'views/crm_communication_tag_views.xml',
        'views/crm_quick_reply_views.xml',
        'views/crm_sla_views.xml',
        'views/crm_assignment_rule_views.xml',
        'views/crm_chat_message_views.xml',
        'views/crm_chat_session_views.xml',
        'views/crm_call_recording_views.xml',
        'views/crm_call_log_views.xml',
        'report/crm_call_log_report.xml',
        'report/crm_chat_session_report.xml',
        'views/crm_communication_views.xml',
        'views/crm_response_time_views.xml',
        'views/crm_lead_views.xml',
        'views/res_partner_views.xml',
        'views/chatroom_actions.xml',
        'views/menus.xml',
        'views/dashboard_actions.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_omnichannel_hub/static/src/js/dashboard.js',
            'crm_omnichannel_hub/static/src/xml/dashboard.xml',
            'crm_omnichannel_hub/static/src/scss/dashboard.scss',
            'crm_omnichannel_hub/static/src/js/chatroom.js',
            'crm_omnichannel_hub/static/src/xml/chatroom.xml',
            'crm_omnichannel_hub/static/src/scss/chatroom.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
