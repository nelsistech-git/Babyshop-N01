# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All Rights Reserved.
# Developer: Nur Uddin Ahammed
{
    'name': 'FW CRM - Buyer Acquisition - Footwear ERP',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing/Footwear',
    'summary': 'Kanban pipeline for prospective buyer acquisition, with one-click '
                'conversion to a full Buyer record on winning the deal.',
    'description': """
FW CRM - Buyer Acquisition
=============================
Phase 6 module of the Nelsis Footwear ERP platform (Odoo Community 17).
A lightweight, footwear-specific CRM covering the "before they're a
buyer" stage - trade show leads, agent referrals, cold outreach - that
FW Core Master's Buyer master does not cover (it assumes the buyer
relationship already exists).

Features
--------
* Configurable Kanban pipeline stages (e.g. New, Contacted, Sample
  Requested, Negotiation, Won)
* Lead capture with source, expected category, and expected annual
  volume
* Win/Loss tracking with reason
* One-click conversion of a won lead into a full FW Buyer record (and
  a linked Contact), so downstream Buyer 360 / Merchandising modules
  pick it up immediately

Author: Nur Uddin Ahammed
Copyright: Nelsis Tech
""",
    'author': 'Nur Uddin Ahammed (Nelsis Tech)',
    'company': 'Nelsis Tech',
    'maintainer': 'Nelsis Tech',
    'website': 'https://www.nelsistech.com',
    'license': 'OPL-1',
    'depends': ['fw_core_master', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/fw_crm_stage_data.xml',
        'views/fw_crm_lead_views.xml',
        'views/fw_crm_stage_views.xml',
        'views/fw_crm_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
