# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """1.2.0: bills posted by the Head of Finance are listed in Due for Payment regardless of due date."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['payment.due.item']._sync()
