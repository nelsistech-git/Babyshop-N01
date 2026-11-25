# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Advances above the limit that already wait in Accounts Review join Due for Payment."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['payment.due.item']._sync()
