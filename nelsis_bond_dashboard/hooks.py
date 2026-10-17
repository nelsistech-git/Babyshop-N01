# -*- coding: utf-8 -*-
# Copyright (c) Nelsis Tech. Developer / Product Owner: Nur Uddin Ahammed.
"""Grant the Auditor role READ-ONLY access to audit-relevant models.

Done in a hook (not CSV) so that models which may not exist in a given
installation never break the install. Only perm_read is ever granted.
"""
import logging

_logger = logging.getLogger(__name__)

ACCESS_PREFIX = 'nelsis_bond_dashboard auditor read '
AUDITOR_READ_MODELS = [
    'stock.move', 'stock.move.line', 'stock.picking', 'stock.picking.type',
    'stock.quant', 'stock.lot', 'stock.location', 'stock.warehouse',
    'product.product', 'product.template', 'product.category', 'uom.uom',
    # Bond models named in the Master Prompt contract (skipped if absent):
    'bond.warehouse.license', 'bond.warehouse.security',
    'bond.warehouse.entitlement', 'bond.warehouse.document',
    'bond.warehouse.register', 'bond.warehouse.reconciliation',
    'nelsis.commercial.document',
]


def post_init_hook(env):
    group = env.ref('nelsis_bond_dashboard.group_bond_dash_auditor')
    Access = env['ir.model.access'].sudo()
    for model_name in AUDITOR_READ_MODELS:
        model = env['ir.model']._get(model_name)
        if not model:
            _logger.info('Auditor read access skipped, model not installed: %s', model_name)
            continue
        if Access.search_count([('model_id', '=', model.id), ('group_id', '=', group.id)]):
            continue
        Access.create({
            'name': ACCESS_PREFIX + model_name,
            'model_id': model.id,
            'group_id': group.id,
            'perm_read': True,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
        })


def uninstall_hook(env):
    env['ir.model.access'].sudo().search([('name', '=like', ACCESS_PREFIX + '%')]).unlink()
