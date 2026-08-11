from odoo import fields, api, models, _


class InheritSaleOrderStock(models.Model):
    _inherit = "sale.order"
    _description = "Inherited Sale Order Inherit Custom Stock"
    
    is_created_from_invoice = fields.Boolean(default=False)
    is_service_invoice = fields.Boolean(default=False)

    # customer_reference_id = fields.Many2one('res.users', string='Customer Reference')
    # 
    # @api.onchange('partner_id')
    # def _onchange_customer_reference(self):
    #     if self.partner_id:
    #         if self.partner_id.reference_id:
    #             self.customer_reference_id = self.partner_id.reference_id.id