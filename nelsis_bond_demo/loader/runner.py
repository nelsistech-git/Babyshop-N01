# -*- coding: utf-8 -*-
"""Runs the loading units in order. Every unit and every step is isolated: a failure is
logged in "Bond Demo Data > Load Log" and never blocks the module installation."""
import importlib
import logging
import traceback

from odoo import SUPERUSER_ID, api

from .ctx import Ctx, MissingDependency

_logger = logging.getLogger(__name__)

UNITS = [
    'u01_users', 'u02_master', 'u03_classification', 'u04_compliance', 'u05_licenses',
    'u06_entitlements', 'u07_lc', 'u08_receipts', 'u09_lc_link', 'u10_commercial',
    'u11_utilization', 'u12_movements', 'u13_recon', 'u14_dashboard', 'u15_purchase',
]


def run_all(env):
    env = api.Environment(env.cr, SUPERUSER_ID, {'tracking_disable': False})
    ctx = Ctx(env)
    Log = env['nelsis.bond.demo.log']
    for index, name in enumerate(UNITS, start=1):
        ctx.unit = name
        ctx.seq = index * 1000
        ctx._counter = 0
        try:
            module = importlib.import_module('odoo.addons.nelsis_bond_demo.loader.' + name)
            with env.cr.savepoint():
                module.run(ctx)
        except MissingDependency as exc:
            Log._record(name, 'skipped', str(exc), unit=name, sequence=index * 1000)
        except Exception as exc:  # noqa - isolate every unit
            _logger.warning('nelsis_bond_demo unit %s failed: %s', name, exc)
            Log._record(name, 'failed', '%s: %s\n\n%s' % (type(exc).__name__, exc, traceback.format_exc()),
                        unit=name, sequence=index * 1000)
            ctx.failed.append(name)
            env.invalidate_all()
    return ctx.failed
