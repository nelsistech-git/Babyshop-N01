# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. All rights reserved.
# Developer / Product Owner: Nur Uddin Ahammed
import logging

_logger = logging.getLogger(__name__)

LC_MODEL = 'nelsis.lc'


def post_init_hook(env):
    """Align existing data once, when the suite core is installed."""
    # 1. one bond classification for all existing locations
    env['stock.location'].with_context(active_test=False).search([])._bond_suite_sync()

    # 2. point Bond Inventory and Commercial Management at the real LC model
    #    (only when the field is still empty: never overwrite a manual choice)
    lc_model = env['ir.model']._get(LC_MODEL)
    if not lc_model:
        _logger.warning('LC model %s not found: LC links not configured.', LC_MODEL)
        return
    for company in env['res.company'].sudo().search([]):
        if not company.bond_lc_model_name:
            company.bond_lc_model_name = LC_MODEL
    Setting = env['nelsis.commercial.setting'].sudo()
    for company in env['res.company'].sudo().search([]):
        setting = Setting.with_company(company).get_setting()
        if not setting.lc_model_id:
            setting.lc_model_id = lc_model.id
