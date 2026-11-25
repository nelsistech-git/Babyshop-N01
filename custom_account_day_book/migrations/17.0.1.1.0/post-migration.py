# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Upgrading an existing database: apply letterhead, paper format, legacy bills and VAT tax."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.custom_account_day_book import post_init_hook
    post_init_hook(env)
