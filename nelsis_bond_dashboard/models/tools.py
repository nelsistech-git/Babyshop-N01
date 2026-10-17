# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tools.safe_eval import safe_eval

PARAM_REVIEW_DAYS = 'nelsis_bond_dashboard.renewal_review_days'
DEFAULT_REVIEW_DAYS = 90

ROLE_GROUPS = (
    'nelsis_bond_dashboard.group_bond_dash_storekeeper',
    'nelsis_bond_dashboard.group_bond_dash_warehouse_manager',
    'nelsis_bond_dashboard.group_bond_dash_commercial',
    'nelsis_bond_dashboard.group_bond_dash_bond_manager',
    'nelsis_bond_dashboard.group_bond_dash_auditor',
    'nelsis_bond_dashboard.group_bond_dash_admin',
)
ADMIN_GROUPS = ('nelsis_bond_dashboard.group_bond_dash_admin', 'base.group_system')

ALERT_TYPES = [
    ('license_expiry', 'License Expiry'),
    ('security_expiry', 'Security / Guarantee Expiry'),
    ('storage_deadline', 'Storage-Period Deadline'),
    ('missing_document', 'Missing Document'),
    ('pending_verification', 'Pending Verification'),
    ('reconciliation_discrepancy', 'Reconciliation Discrepancy'),
    ('entitlement_threshold', 'Entitlement Threshold'),
    ('unauthorized_attempt', 'Unauthorized Transaction Attempt'),
    ('outstanding_approval', 'Outstanding Approval'),
]
SEVERITIES = [('info', 'Information'), ('warning', 'Warning'), ('critical', 'Critical')]


def is_dashboard_admin(env):
    return any(env.user.has_group(xmlid) for xmlid in ADMIN_GROUPS)


def has_dashboard_role(env):
    return is_dashboard_admin(env) or any(env.user.has_group(x) for x in ROLE_GROUPS)


def get_review_days(env):
    value = env['ir.config_parameter'].sudo().get_param(PARAM_REVIEW_DAYS, DEFAULT_REVIEW_DAYS)
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return DEFAULT_REVIEW_DAYS


def eval_domain(env, domain_text):
    """Safely evaluate a stored domain string.

    Available names: today, now, relativedelta, timedelta, alert_days, uid.
    """
    text = (domain_text or '').strip() or '[]'
    context = {
        'today': fields.Date.context_today(env['res.users']),
        'now': fields.Datetime.now(),
        'relativedelta': relativedelta,
        'timedelta': timedelta,
        'alert_days': get_review_days(env),
        'uid': env.uid,
    }
    domain = safe_eval(text, context)
    if not isinstance(domain, (list, tuple)):
        raise ValueError('A domain must evaluate to a list.')
    return list(domain)


def jsonable(value):
    """Make a domain JSON-safe (dates to strings, tuples to lists)."""
    if isinstance(value, datetime):
        return fields.Datetime.to_string(value)
    if isinstance(value, date):
        return fields.Date.to_string(value)
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value
