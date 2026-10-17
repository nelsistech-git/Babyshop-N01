# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class NelsisCommercialFile(models.Model):
    _inherit = 'nelsis.commercial.file'

    purchase_count = fields.Integer(compute='_compute_purchase_count')

    def _compute_purchase_count(self):
        counts = {}
        real_ids = [i for i in self.ids if isinstance(i, int)]
        if real_ids:
            for f, n in self.env['purchase.order'].sudo()._read_group(
                    [('commercial_file_id', 'in', real_ids)], ['commercial_file_id'], ['__count']):
                counts[f.id] = n
        for rec in self:
            rec.purchase_count = counts.get(rec.id, 0)

    @api.constrains('lc_ref')
    def _check_purchase_lc(self):
        for rec in self:
            lc = rec.sudo().lc_ref
            if not lc or lc._name != 'nelsis.lc':
                continue
            for po in self.env['purchase.order'].sudo().search([('commercial_file_id', '=', rec.id)]):
                if po.lc_id and po.lc_id != lc:
                    raise ValidationError(_('Purchase order %(po)s is linked to LC %(a)s, not %(b)s.',
                                            po=po.name, a=po.lc_id.display_name, b=lc.display_name))

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Purchase Orders'), 'res_model': 'purchase.order',
                'view_mode': 'tree,form', 'domain': [('commercial_file_id', '=', self.id)]}
