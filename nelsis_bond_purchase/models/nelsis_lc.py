# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class NelsisLc(models.Model):
    _inherit = 'nelsis.lc'

    purchase_count = fields.Integer(compute='_compute_po_amounts')
    po_committed_amount = fields.Monetary('Purchase Orders Committed', currency_field='currency_id',
                                          compute='_compute_po_amounts',
                                          help='Total of confirmed purchase orders linked to this LC.')
    po_balance_amount = fields.Monetary('LC Left After Purchase Orders', currency_field='currency_id',
                                        compute='_compute_po_amounts')

    def _bond_po_committed(self, exclude=None):
        """Sum of confirmed purchase orders (same currency as the LC by constraint)."""
        self.ensure_one()
        domain = [('lc_id', '=', self.id), ('state', 'in', ('purchase', 'done'))]
        if exclude:
            domain.append(('id', 'not in', exclude.ids))
        return sum(self.env['purchase.order'].sudo().search(domain).mapped('amount_total'))

    @api.depends('current_amount', 'tolerance_percent')
    def _compute_po_amounts(self):
        counts = {}
        real_ids = [i for i in self.ids if isinstance(i, int)]
        if real_ids:
            for lc, n in self.env['purchase.order'].sudo()._read_group(
                    [('lc_id', 'in', real_ids)], ['lc_id'], ['__count']):
                counts[lc.id] = n
        for lc in self:
            lc.purchase_count = counts.get(lc.id, 0)
            committed = lc._bond_po_committed() if isinstance(lc.id, int) else 0.0
            lc.po_committed_amount = committed
            lc.po_balance_amount = lc.current_amount - committed

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Purchase Orders'), 'res_model': 'purchase.order',
                'view_mode': 'tree,form', 'domain': [('lc_id', '=', self.id)]}
