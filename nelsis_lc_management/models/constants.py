# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
"""Shared constants for Nelsis LC Management."""

LC_STATES = [
    ('draft', 'Draft'),
    ('review', 'Submitted for Review'),
    ('approved', 'Approved'),
    ('opened', 'Opened / Active'),
    ('in_progress', 'Shipment / Documentation'),
    ('partial', 'Partially Utilized / Cleared'),
    ('cleared', 'Fully Cleared'),
    ('hold', 'On Hold'),
    ('closed', 'Completed / Closed'),
    ('cancelled', 'Cancelled'),
]

# States in which the LC is operationally alive (shipments, receipts allowed).
LIVE_STATES = ('opened', 'in_progress', 'partial', 'cleared')
# States in which an amendment may be raised.
AMEND_STATES = LIVE_STATES + ('hold',)

SHIPMENT_STATES = [
    ('planned', 'Planned'),
    ('shipped', 'Shipped'),
    ('docs_received', 'Documents Received'),
    ('customs_cleared', 'Customs Cleared'),
    ('received', 'Received in Warehouse'),
    ('cancelled', 'Cancelled'),
]
# Shipment states counted as "utilization" of the LC value.
UTILIZED_SHIPMENT_STATES = ('shipped', 'docs_received', 'customs_cleared', 'received')
OPEN_SHIPMENT_STATES = ('planned', 'shipped', 'docs_received', 'customs_cleared')

MODULE = 'nelsis_lc_management'
G_USER = MODULE + '.group_lc_user'
G_OFFICER = MODULE + '.group_lc_officer'
G_MANAGER = MODULE + '.group_lc_manager'
G_BOND = MODULE + '.group_lc_bond_officer'
G_AUDITOR = MODULE + '.group_lc_auditor'
LC_VIEW_GROUPS = ','.join([G_USER, G_BOND, G_AUDITOR])

# Technical fields that may be written by the framework (chatter, activities, reminders)
# without being treated as business edits.
TECH_FIELDS = frozenset([
    'message_main_attachment_id', 'message_follower_ids', 'message_ids',
    'message_partner_ids', 'message_has_error', 'message_needaction',
    'message_attachment_count', 'website_message_ids',
    'activity_ids', 'activity_state', 'activity_user_id', 'activity_type_id',
    'activity_date_deadline', 'activity_summary', 'activity_exception_decoration',
    'activity_exception_icon', 'expiry_reminded', 'deadline_reminded', 'reminded',
])
