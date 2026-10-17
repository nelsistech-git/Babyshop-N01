# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Load the demo data. Every step is isolated: a failing step is logged in
    Bond Demo Data > Load Log and never blocks the module installation."""
    from .loader.runner import run_all
    try:
        run_all(env)
    except Exception:  # pragma: no cover - last-resort guard, the install must not fail
        _logger.exception('nelsis_bond_demo: loader aborted unexpectedly')
