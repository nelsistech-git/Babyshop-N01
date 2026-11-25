# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """New 'Paid' status: recompute the stored status of the existing rows."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['payment.due.item'].search([])._compute_state()
