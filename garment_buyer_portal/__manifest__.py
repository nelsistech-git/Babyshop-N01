# -*- coding: utf-8 -*-
###############################################################################
#
#    Smart Complete Garment Software
#    Module 10: Buyer Portal Management System
#
#    Copyright (c) Nelsis Tech (www.nelsistech.com)
#    Developer: Nur Uddin Ahammed
#    License: LGPL-3
#
###############################################################################
{
    'name': 'Smart Garment ERP - Buyer Portal Management System',
    'version': '17.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Self-service buyer portal (/my) - order, sample, shipment & quality visibility plus '
               'tech pack / sample / style buyer approvals and buyer-factory messaging',
    'description': """
Smart Complete Garment Software — Buyer Portal Management System
===================================================================
Module 10 of the Smart Complete Garment Software suite.

A secure, self-service Odoo Portal (standard `portal.mixin` / `base.group_portal`
pattern, buyer contacts log in at /my) that lets a garment buyer's own people
collaborate with the factory without email, built strictly as a read-access
and buyer-approval-action layer on top of the real transactional modules —
it does not duplicate any order/sample/shipment/techpack/quality data:

* Buyer Dashboard — active order / sample / shipment summary cards (SRS 8)
* Buyer Order Tracking — PO, style, quantity, size/color breakdown, stage
  progress and Order Details page (garment.order, garment_order_management,
  SRS 9-10)
* Buyer Sample Approval Portal — sample status, images, measurements and
  Approve / Request Revision / Reject (garment.sample, garment_sample_management,
  SRS 12)
* Buyer Shipment Tracking — container, vessel, ETD/ETA, port, tracking status
  (garment.shipment, garment_logistics, SRS 30)
* Buyer Quality Portal — read-only inspection/defect summary once released
  (garment.quality.inspection, garment_quality, SRS 29)
* Tech Pack / Sample / Style buyer sign-off unified into one Approvals inbox
  that writes back to the real approval records on those models
  (garment.portal.approval.action — new in this module — driving
  garment.tech.approval / garment.sample.approval / garment.style.approval,
  SRS 12, 26, 32)
* Buyer Portal Access Request — buyer registration & approval workflow that
  provisions a real Odoo portal user against a buyer contact
  (garment.portal.access.request — new in this module, SRS 21-22)
* Buyer Portal Message — buyer <-> factory message thread with a
  Comment -> Assigned Team -> Action Taken -> Response -> Buyer Confirmation
  workflow (garment.portal.message — new in this module, SRS 13, 16)
* Buyer Portal Activity Log — audit of buyer logins, document views,
  approval decisions and comments (garment.portal.activity.log — new in
  this module, SRS 46)

Built for Bangladesh garment manufacturing & buying-house operations on
Odoo 17 Community. See IMPLEMENTATION_NOTES.md for exactly what is covered,
what is deliberately deferred, and how buyer data-visibility (no supplier
info / cost / margin / internal chatter) is enforced.
""",
    'author': 'Nelsis Tech, Nur Uddin Ahammed',
    'website': 'https://www.nelsistech.com',
    'maintainer': 'Nelsis Tech',
    'license': 'LGPL-3',
    'depends': [
        'base', 'mail', 'portal',
        'garment_buyer_crm',
        'garment_order_management',
        'garment_sample_management',
        'garment_logistics',
        'garment_techpack',
        'garment_style_library',
        'garment_quality',
    ],
    'data': [
        'security/garment_buyer_portal_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/garment_portal_access_request_views.xml',
        'views/garment_portal_approval_action_views.xml',
        'views/garment_portal_message_views.xml',
        'views/garment_portal_activity_log_views.xml',
        'views/res_partner_views.xml',
        'views/portal_templates.xml',
        'views/garment_buyer_portal_menus.xml',
    ],
    'demo': [],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
