# -*- coding: utf-8 -*-
import base64

from odoo import SUPERUSER_ID, api
from odoo.tools import file_open


def migrate(cr, version):
    """1.3.0: the letterhead logo no longer carries the black bands above/below it."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    with file_open('custom_account_day_book/static/src/img/mtailor_logo.png', 'rb') as f:
        logo = base64.b64encode(f.read())
    env['res.company'].sudo().search([]).write({'letterhead_logo': logo})
