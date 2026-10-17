# -*- coding: utf-8 -*-
from odoo import fields, models

POLICIES = [('off', 'Do not check'), ('warn', 'Warn (note on the order)'), ('block', 'Block confirmation')]


class ResCompany(models.Model):
    _inherit = 'res.company'

    bond_po_require_lc = fields.Boolean(string='Bonded Purchase Requires an LC', default=True)
    bond_po_lc_limit_policy = fields.Selection(
        POLICIES, string='LC Limit Check', default='block', required=True,
        help='Orders linked to an LC must fit the LC approved amount plus its tolerance.')
    bond_po_entitlement_policy = fields.Selection(
        POLICIES, string='Entitlement Check', default='warn', required=True,
        help='Bonded orders are compared with the available quantity / value of the active entitlement. '
             'Only validated utilization counts; other open orders are not reserved.')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bond_po_require_lc = fields.Boolean(related='company_id.bond_po_require_lc', readonly=False)
    bond_po_lc_limit_policy = fields.Selection(related='company_id.bond_po_lc_limit_policy', readonly=False)
    bond_po_entitlement_policy = fields.Selection(related='company_id.bond_po_entitlement_policy', readonly=False)
