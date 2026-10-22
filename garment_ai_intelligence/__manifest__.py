# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 25: AI Intelligence Platform
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - AI Intelligence Platform',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Central AI provider config, prompt governance, unified cross-module insight log, '
               'demand forecasting and API usage/cost audit for the Smart Garment suite',
    'description': """
Smart Complete Garment Software — AI Intelligence Platform
==============================================================
Module 25 of the Smart Complete Garment Software suite.

Several sibling modules (Buyer CRM, Order Management, Quality, Maintenance,
Compliance, PLM, Industrial Engineering...) already extend a shared abstract
``garment.ai.engine`` model with their own deterministic heuristic scoring
methods (lead scoring, order risk, quality risk, breakdown prediction...).
This module gives that pattern a proper home:

* A real, governed provider configuration model
  (``garment.ai.provider.config``) — OpenAI / Anthropic / Azure OpenAI /
  Custom endpoint, API key (password widget, admin-only field), model name,
  enabled flag and per-feature routing — replacing scattered
  ``ir.config_parameter`` reads with an editable, auditable record.
* A reusable Prompt Template library (``garment.ai.prompt.template``) so
  every external LLM call in the suite is built from a centrally governed,
  versioned prompt instead of an inline string buried in Python.
* A UNIFIED cross-module AI Insight log (``garment.ai.insight``) — a single
  place every module's AI predictions/recommendations/alerts can point at
  via a generic ``res_model``/``res_id`` back-reference, with confidence
  score and a new/reviewed/actioned/dismissed review workflow. This is the
  natural consolidation point for the several scattered
  ``garment.xxx.ai.*`` log models already built in sibling modules (see
  IMPLEMENTATION_NOTES.md for the follow-up migration plan — not done in
  this module).
* A real, working Demand Forecast (``garment.demand.forecast``): a
  deterministic moving-average / weighted-trend heuristic computed over
  actual historical ``garment.order`` / ``garment.order.line`` records for
  a Style (optionally narrowed to one Buyer) — genuinely computed from ERP
  data, not a hardcoded number.
* An API Usage Log (``garment.ai.usage.log``) for cost governance — tokens
  in/out, estimated cost and latency for every external AI call the suite
  makes through this module's engine extension.

External LLM calls are implemented behind a clearly guarded
``try/except`` using Python ``requests`` (see ``garment.ai.engine.call_llm``)
so the feature is genuinely wired end-to-end, while every deterministic
heuristic (like the demand forecast) works with zero external dependency
and zero API key, exactly like its sibling modules.
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'garment_buyer_crm', 'garment_style_library', 'garment_order_management'],
    'data': [
        'security/garment_ai_intelligence_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_ai_prompt_template_data.xml',
        'views/garment_ai_provider_config_views.xml',
        'views/garment_ai_prompt_template_views.xml',
        'views/garment_ai_insight_views.xml',
        'views/garment_ai_usage_log_views.xml',
        'views/garment_demand_forecast_views.xml',
        'views/garment_ai_intelligence_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
