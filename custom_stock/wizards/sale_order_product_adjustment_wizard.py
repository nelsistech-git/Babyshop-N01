from odoo import models, fields, _, api
from odoo.exceptions import AccessError


class SaleProductAdjustmentWizard(models.TransientModel):
    _name = 'sale.product.adjustment.wizard'

    pr_err_msg = fields.Text(string='Products')
    product_ids = fields.Many2many('product.product')
    location_id = fields.Many2one('stock.location')

    @api.model
    def default_get(self, fields):
        res = super(SaleProductAdjustmentWizard, self).default_get(fields)
        pr_err_msg = self.env.context.get('pr_err_msg')
        location_id = self.env.context.get('location_id')
        pro_ids = self.env.context.get('pro_ids')
        res.update({'pr_err_msg': pr_err_msg, 'location_id': location_id, 'product_ids': pro_ids})
        return res

    def action_adjustment(self):
        pro_ids = [x.id for x in self.product_ids]
        action_vals = {
            'name': _('Inventory Adjustments'),
            'domain': [],
            'res_model': 'stock.inventory',
            'view_mode': 'form',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {'location': self.location_id, 'pro_ids': pro_ids},
        }
        return action_vals


