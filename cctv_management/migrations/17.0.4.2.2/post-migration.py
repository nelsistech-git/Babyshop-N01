# -*- coding: utf-8 -*-
"""Remove 'hour'/'minute' date granularities that Odoo 17's web client rejects.

Odoo 17 graph/pivot only accept day/week/month/quarter/year, so anything like
interval_start:hour or reading_time:hour raises "Invalid groupBy description".
Cleans saved favorites, stale/customised graph+pivot views, and action contexts.
"""
import re

from odoo import api, SUPERUSER_ID

BAD_INTERVAL = re.compile(r'interval=(["\'])(hour|minute)\1')
BAD_GROUPBY = re.compile(r':(hour|minute)\b')


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. Saved favorites
    cr.execute("DELETE FROM ir_filters WHERE context LIKE '%:hour%' OR context LIKE '%:minute%'")

    # 2. Graph / pivot views (including leftovers or manual customisations)
    views = env['ir.ui.view'].with_context(active_test=False).search(
        [('type', 'in', ('graph', 'pivot'))])
    for view in views:
        arch = view.arch_db or ''
        new = BAD_INTERVAL.sub('interval="day"', arch)
        if new != arch:
            view.arch_db = new

    # 3. Action contexts with a bad group-by
    actions = env['ir.actions.act_window'].with_context(active_test=False).search(
        [('context', 'like', ':hour')])
    for act in actions:
        act.context = BAD_GROUPBY.sub(':day', act.context)
