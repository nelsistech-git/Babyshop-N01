# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech.
# Developer / Product Owner: Nur Uddin Ahammed
"""Shared constants and helpers for the Nelsis Bond Compliance addon."""
import re

from odoo import _, fields
from odoo.exceptions import AccessError, UserError

WORKFLOW_CTX = 'bond_compliance_workflow'

G_USER = 'nelsis_bond_compliance.group_bond_compliance_user'
G_OFFICER = 'nelsis_bond_compliance.group_bond_compliance_officer'
G_REVIEWER = 'nelsis_bond_compliance.group_bond_compliance_reviewer'
G_APPROVER = 'nelsis_bond_compliance.group_bond_compliance_approver'
G_MANAGER = 'nelsis_bond_compliance.group_bond_compliance_manager'

ICP_SEGREGATION = 'nelsis_bond_compliance.enforce_segregation'
ICP_WARNING_DAYS = 'nelsis_bond_compliance.expiry_warning_days'

CODE_RE = re.compile(r'^[A-Z0-9][A-Z0-9_.\-]*$')
KEY_RE = re.compile(r'^[a-z][a-z0-9_]*$')
URL_RE = re.compile(r'^https?://[^\s/$.?#][^\s]*$', re.IGNORECASE)

DISCLAIMER = (
    'Software validation result only. It is not an official customs approval '
    'and does not by itself establish legal compliance.'
)


def normalize_code(value):
    """Return a stripped, upper-case technical code."""
    return value.strip().upper() if value else value


def require_any_group(env, group_xmlids, action):
    """Raise AccessError unless the current user holds one of the groups."""
    if env.su:
        return
    if any(env.user.has_group(xmlid) for xmlid in group_xmlids):
        return
    roles = ', '.join(env.ref(xmlid).name for xmlid in group_xmlids)
    raise AccessError(_(
        'You are not allowed to %(action)s. Required role: %(roles)s.',
        action=action, roles=roles))


def segregation_enabled(env):
    value = env['ir.config_parameter'].sudo().get_param(ICP_SEGREGATION, 'True')
    return str(value).strip().lower() in ('true', '1', 'yes')


def check_segregation(env, other_user, message):
    """Block the current user when the segregation-of-duties rule is violated."""
    if other_user and other_user == env.user and segregation_enabled(env):
        raise UserError(message)


def get_warning_days(env):
    value = env['ir.config_parameter'].sudo().get_param(ICP_WARNING_DAYS, '30')
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 30


def schedule_group_activity(record, group_xmlid, summary, note='', deadline=None):
    """Schedule one To-Do activity per active internal user of a group (no duplicates)."""
    group = record.env.ref(group_xmlid, raise_if_not_found=False)
    if not group:
        return
    deadline = deadline or fields.Date.context_today(record)
    existing = record.sudo().activity_ids
    for user in group.sudo().users.filtered(lambda u: u.active and not u.share):
        if existing.filtered(lambda a: a.user_id == user and a.summary == summary):
            continue
        record.activity_schedule(
            'mail.mail_activity_data_todo', date_deadline=deadline,
            summary=summary, note=note, user_id=user.id)


def schedule_user_activity(record, user, summary, note='', deadline=None):
    if not user or not user.active:
        return
    deadline = deadline or fields.Date.context_today(record)
    record.activity_schedule(
        'mail.mail_activity_data_todo', date_deadline=deadline,
        summary=summary, note=note, user_id=user.id)


def clear_activities(record, summaries):
    """Remove open workflow activities (all users) matching the summaries."""
    record.sudo().activity_ids.filtered(lambda a: a.summary in summaries).unlink()
