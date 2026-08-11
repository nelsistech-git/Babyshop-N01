from odoo import models, fields


class SalesPriceUpdate(models.Model):
    _name = 'sales.price.update'
    _description = "Sales Price Update"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    product_id = fields.Many2one('product.template', string='Product', readonly=False, required=True)
    old_sales_price = fields.Float('Old Sales Price', digits='Product Price')
    new_sales_price = fields.Float('New Sales Price', digits=(16, 2), required=True, default=0.0)
    cost_price = fields.Float('Cost Price', digits='Product Price')
    other_cost_price = fields.Float('Other Cost Price', digits='Product Price')
    total_cost_price = fields.Float('Total Cost Price', digits='Product Price')
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    currency_id = fields.Many2one('res.currency', 'Currency',
                                          domain="['|', ('active', '=', True), ('active', '=', False)]",
                                          default=lambda self: self.env['res.currency'].search([('name', '=', 'BDT')]))
    currency = fields.Char('Currency Name', related='currency_id.name')
    rate = fields.Float(string='Rate', digits=(16, 2))
    foreign_sales_price = fields.Float(string='Foreign Sales Price', digits=(16, 2))

    def name_get(self):
        res = []
        for field in self:
            res.append((field.id, '%s - %s %s' % (field.product_id.display_name, field.currency_id.name, field.new_sales_price)))
        return res

    def js_python_method(self, model_name, active_id):
        pass
