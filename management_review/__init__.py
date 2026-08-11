# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from odoo import api, SUPERUSER_ID

def _generate_summary_data(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    dashboard = env['ssp.review.dashboard'].search([],limit=1)
    dashboard.generate_summary_data()
