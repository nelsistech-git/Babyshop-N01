import logging

from . import models

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Fill the database with the demo story right after installation (also works when only some of the
    Nelsis modules are installed - missing parts are skipped and listed in Field Force > Configuration > Demo Data)."""
    try:
        for line in env['nelsis.demo.generator'].sudo().generate():
            _logger.info('nelsis_field_demo: %s', line)
    except Exception:  # noqa: BLE001
        _logger.exception('nelsis_field_demo: could not create demo data - open Field Force > Configuration > '
                          'Demo Data and press Generate')
