# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 23: Document Management & Digital Workflow System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Document Management & Digital Workflow System',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Generic cross-module document register, version control, check-in/out, configurable approval workflow engine, retention policy and access log usable by every module',
    'description': """
Smart Complete Garment Software — Document Management & Digital Workflow System
=================================================================================
Module 23 of the Smart Complete Garment Software suite.

POSITIONING (read IMPLEMENTATION_NOTES.md for the full rationale)
-------------------------------------------------------------------
Almost every other module in this suite already stores its own working
documents on its own model (garment.style.document, garment.supplier.document,
garment.hr.document, garment.tech.attachment, garment.compliance.document,
garment.order.document, garment.lc.document, garment.shipment.document ...).
This module does NOT migrate or replace any of that — those Binary/
attachment=True fields stay exactly where they are and keep working exactly
as before.

Instead this module is a thin, standalone FOUNDATION LAYER that any other
module can optionally plug into:

* ``garment.document`` — a central, cross-module document register. Any
  record in the suite can be linked into it through a generic
  ``res_model``/``res_id`` reference (the same pattern Odoo's own
  ``ir.attachment`` / Documents app uses) without this module ever needing
  to depend on that module.
* ``garment.document.category`` — a shared, hierarchical folder/category
  taxonomy (Commercial / Production / HR / Compliance / Finance ...).
* ``garment.document.version`` — full version history with check-in/
  check-out locking.
* ``garment.document.approval.workflow`` + ``.workflow.step`` — a GENERIC,
  configurable multi-step (sequential or parallel) approval chain that any
  module can assign to a document, driven by amount/category/model rules.
* ``garment.document.access.log`` — audit trail of who viewed, downloaded,
  edited, checked in/out, approved or rejected each document.
* ``garment.document.tag`` — free many2many tagging for fast search.
* ``garment.document.retention.policy`` — configurable expiry/archival
  rules (keep N years, or permanently) with an automatic daily check.
* ``garment.document.mixin`` — an abstract mixin any other module's model
  can add to its own ``_inherit`` list to get a ready-made "Documents"
  smart button wired to the shared register (see IMPLEMENTATION_NOTES.md
  for the wiring itself, left as a follow-up integration task per module).

Because it only depends on base/mail/portal, ANY other module in the suite
(including ones not yet built) can add this module to its own `depends` and
start routing its own records through the shared approval engine or listing
them in the shared register, without pulling in the rest of the ERP.

Key Features
------------
* Central document repository with hierarchical folder/category taxonomy
  and free full-text-searchable metadata (name, number, keywords, tags)
* Document version control with a complete version history per document
* Check-in / check-out locking to prevent concurrent-edit conflicts
* Generic multi-step approval workflow engine (sequential and parallel,
  amount/category/model driven dynamic rules) usable by any module
* Document expiry / renewal tracking driven by configurable retention
  policies, with a daily cron for reminders and auto-archive/lock actions
* Access control by role and a 4-level security classification (Public /
  Internal / Confidential / Highly Confidential)
* Audit trail of every view / download / edit / check-in-out / approve /
  reject action
* Reusable ``garment.document.mixin`` for a "Documents" smart button on any
  other module's model
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'portal'],
    'data': [
        'security/garment_document_management_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/garment_document_category_data.xml',
        'data/garment_document_retention_policy_data.xml',
        'data/ir_cron_data.xml',
        'views/garment_document_category_views.xml',
        'views/garment_document_tag_views.xml',
        'views/garment_document_retention_policy_views.xml',
        'views/garment_document_approval_workflow_views.xml',
        'views/garment_document_views.xml',
        'views/garment_document_version_views.xml',
        'views/garment_document_access_log_views.xml',
        'views/garment_document_dashboard_views.xml',
        'views/garment_document_management_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
