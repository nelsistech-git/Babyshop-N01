# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'express.approval.mixin']

    style_number = fields.Char(
        string='Style Number', index=True,
        help='Used to match Style Number-wise loyalty/discount rules.')

    def write(self, vals):
        if self.env.context.get('express_approval_bypass'):
            return super().write(vals)
        if 'list_price' in vals:
            for product in self:
                old_price = product.list_price
                if old_price == vals['list_price']:
                    continue
                product._express_create_approval(
                    action_type='price_change',
                    old_values={'list_price': old_price},
                    new_values={'list_price': vals['list_price']},
                    reason=self.env.context.get('express_approval_reason'),
                )
                raise UserError(_(
                    'Changing the sales price of "%s" requires Manager -> GM -> MD approval. '
                    'A request has been submitted.') % product.name)
        return super().write(vals)
