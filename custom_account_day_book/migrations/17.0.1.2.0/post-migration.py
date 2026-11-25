# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """1.2.0: letterhead footer / logo were empty on existing companies - fill them in."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.company']._fill_letterhead_defaults()
