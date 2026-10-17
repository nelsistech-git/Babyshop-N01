# -*- coding: utf-8 -*-
# Copyright © Nelsis Tech. Developer: Nur Uddin Ahammed. All rights reserved.
from odoo import _
from odoo.exceptions import AccessError

G_USER = 'nelsis_commercial.group_commercial_user'
G_OFFICER = 'nelsis_commercial.group_commercial_officer'
G_MANAGER = 'nelsis_commercial.group_commercial_manager'

TRANSACTION_TYPES = [
    ('import_lc', 'Import against LC'),
    ('import_non_lc', 'Import (without LC)'),
    ('local_ref', 'Local / Back-to-back Reference'),
    ('export_ref', 'Export Reference'),
    ('other', 'Other'),
]

FILE_STATES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted for Review'),
    ('verification', 'Under Verification'),
    ('docs_complete', 'Documents Complete'),
    ('customs', 'Customs Clearance in Progress'),
    ('receipt_pending', 'Cleared / Receipt Pending'),
    ('done', 'Completed'),
    ('returned', 'Returned for Correction'),
    ('rejected', 'Rejected'),
    ('hold', 'On Hold'),
    ('cancel', 'Cancelled'),
]


def require_group(env, xmlid):
    """Server-side permission check. Sudo/cron contexts are trusted."""
    if env.su:
        return
    if not env.user.has_group(xmlid):
        raise AccessError(_("You do not have the permission required for this operation."))
