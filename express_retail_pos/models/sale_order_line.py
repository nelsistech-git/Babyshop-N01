# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'express.approval.mixin']

    express_pos_is_offer_line = fields.Boolean(
        default=False, copy=False,
        help='Technical flag identifying an auto-generated loyalty/offer discount line.')

    GUARDED_FIELDS = {'discount', 'price_unit', 'product_uom_qty'}

    def write(self, vals):
        if self.env.context.get('express_approval_bypass'):
            return super().write(vals)
        touched = self.GUARDED_FIELDS.intersection(vals.keys())
        if touched:
            for line in self:
                if line.order_id.state in ('sale', 'done') or line.order_id.is_daily_closed:
                    action_type = 'discount' if 'discount' in touched else 'edit'
                    line._express_create_approval(
                        action_type=action_type,
                        old_values=line._express_snapshot(list(self.GUARDED_FIELDS)),
                        new_values=vals,
                        reason=self.env.context.get('express_approval_reason'),
                    )
                    raise UserError(_(
                        'This order line belongs to a confirmed/closed order. The change has '
                        'been submitted for Manager -> GM -> MD approval.'))
        return super().write(vals)

    def unlink(self):
        if self.env.context.get('express_approval_bypass'):
            return super().unlink()
        for line in self:
            if line.order_id.state in ('sale', 'done') or line.order_id.is_daily_closed:
                line._express_create_approval(
                    action_type='delete',
                    old_values=line._express_snapshot(['product_id', 'product_uom_qty', 'price_unit']),
                    new_values={},
                    reason=self.env.context.get('express_approval_reason'),
                )
                raise UserError(_(
                    'This order line belongs to a confirmed/closed order and cannot be deleted '
                    'directly. A deletion approval request has been submitted.'))
        return super().unlink()
