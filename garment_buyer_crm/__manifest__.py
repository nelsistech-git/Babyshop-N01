# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 1: Buyer CRM & Relationship Management
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Buyer CRM & Relationship Management',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Buyer lifecycle, RFQ, opportunity pipeline and communication hub for garment buying houses',
    'description': """
Smart Complete Garment Software — Buyer CRM & Relationship Management
=======================================================================
Module 1 of the Smart Complete Garment Software suite.

Manages the complete lifecycle of garment buyers: lead capture, prospect
qualification, opportunity pipeline, RFQ intake, communication history,
buyer documents/compliance certificates, and buyer performance analytics.

Built for Bangladesh garment manufacturing & buying house operations on
Odoo 17 Community.

Key Features
------------
* Centralized Buyer 360 master (business, financial, compliance, buying
  preference, communication preference data)
* Multi-contact buyer directory with role tagging (decision maker,
  technical/finance/shipment/sample contacts)
* Configurable Lead Sources with cost/ROI/conversion tracking
* Opportunity pipeline (Kanban) from New Opportunity to Order Confirmed / Lost
* RFQ intake with full product, quantity, commercial & date fields
* Buyer document vault with expiry reminders and approval workflow
* Full communication log (calls, email, WhatsApp, meetings, factory visits, audits)
* Buyer performance dashboard (conversion rate, revenue, top buyers/merchandisers)
* Built-in AI Assist hook for lead scoring / next-best-action suggestions,
  pluggable to any external AI provider via System Parameters
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal', 'contacts', 'account'],
    'data': [
        'security/garment_buyer_crm_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_lead_source_data.xml',
        'data/garment_opportunity_stage_data.xml',
        'data/garment_crm_tag_data.xml',
        'data/garment_whatsapp_template_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'views/garment_buyer_views.xml',
        'views/garment_buyer_contact_views.xml',
        'views/garment_buyer_document_views.xml',
        'views/garment_communication_log_views.xml',
        'views/garment_lead_source_views.xml',
        'views/garment_opportunity_views.xml',
        'views/garment_rfq_views.xml',
        'views/garment_crm_meeting_views.xml',
        'views/garment_crm_activity_views.xml',
        'views/garment_buyer_visit_views.xml',
        'views/garment_buyer_complaint_views.xml',
        'views/garment_whatsapp_template_views.xml',
        'views/garment_crm_dashboard_views.xml',
        'views/res_config_settings_views.xml',
        'report/garment_buyer_profile_report.xml',
        'views/garment_buyer_crm_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
