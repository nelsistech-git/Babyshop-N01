from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date


class SalesPriceUpdateWizard(models.TransientModel):
    _name = 'sales.price.update.wizard'
    _description = "Sales Price Update Wizard"

    product_id = fields.Many2one('product.template', string='Product', required=True)
    old_sales_price = fields.Float('Old Sales Price', digits='Product Price')
    new_sales_price = fields.Float('New Sales Price', digits='Product Price', required=True, default=0.0)
    cost_price = fields.Float('Cost Price', digits='Product Price')
    other_cost_price = fields.Float('Other Cost Price', digits='Product Price')
    total_cost_price = fields.Float('Total Cost Price', digits='Product Price')
    approved_by_id = fields.Many2one('res.users', string='Approved By', required=True)
    warning_msg = fields.Char()
    success_msg = fields.Char()
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  domain="['|', ('active', '=', True), ('active', '=', False)]",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'BDT')]))
    currency = fields.Char('Currency Name', related='currency_id.name')
    rate = fields.Float(string='Rate (BDT)', default=0.00, digits=(16, 2))
    foreign_sales_price = fields.Float(string='Foreign Sales Price', default=0.00, digits=(16, 2))

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id.name != 'BDT':
            currency_rate_obj = self.env['currency.conversion.rate'].search(
                [('date', '<=', date.today()), ('currency_id', '=', self.currency_id.id)], order='date DESC',
                limit=1)
            currency_rate = currency_rate_obj.rate
            return {'value': {'rate': currency_rate}}

    @api.onchange('rate')
    def _onchange_rate(self):
        for rec in self:
            if rec.currency_id:
                if rec.currency_id.name != 'BDT':
                    if rec.rate < 0:
                        rec.rate = rec.rate * (-1)
                    elif rec.rate == 0:
                        raise UserError('Input Foreign Rate that is greater than zero.')

    @api.onchange('foreign_sales_price')
    def _onchange_foreign_sales_price(self):
        for rec in self:
            if rec.currency_id:
                if rec.currency_id.name != 'BDT':
                    if rec.foreign_sales_price < 0:
                        rec.rate = rec.foreign_sales_price * (-1)
                    elif rec.foreign_sales_price == 0:
                        raise UserError('Input Foreign Sales Price that is greater than zero.')

    @api.onchange('product_id')
    def _onchange_product_price(self):
        # for rec in self:
        old_sales_price = self.product_id.list_price
        self.old_sales_price = old_sales_price
        cost_price_obj = self.env['product.product'].search([('product_tmpl_id', '=', self.product_id.id)])
        cost_price_list = []
        for rec in cost_price_obj:
            if rec.standard_price > 0:
                self.warning_msg = ""
                cost_price_list.append(rec.standard_price)
            else:
                self.warning_msg = "Warning! Set the cost price of '%s'." % rec.display_name
        self.cost_price = max(cost_price_list, default=0)
        # other_cost_price_obj = self.env['stock.quant'].search([('product_id.product_tmpl_id', '=', self.product_id.id), ('location_id.usage', '=', 'internal')])
        # other_cost_price_list = [other_cost.other_cost_rate for other_cost in other_cost_price_obj if other_cost.other_cost_rate >= 0]
        # self.other_cost_price = max(other_cost_price_list, default=0)
        other_cost_price_obj = self.env['product.product'].search(
            [('product_tmpl_id', '=', self.product_id.id), ('other_cost', '>', 0)], order='other_cost desc', limit=1)
        if other_cost_price_obj:
            self.other_cost_price = other_cost_price_obj[0].other_cost
        else:
            self.other_cost_price = 0

        self.total_cost_price = self.cost_price + self.other_cost_price
        self.success_msg = ""

    @api.onchange('currency_id', 'rate', 'foreign_sales_price')
    def _onchange_currency(self):
        if self.currency_id.name != 'BDT':
            new_sales_price = self.rate * self.foreign_sales_price
            self.new_sales_price = new_sales_price

    def action_confirm(self):
        if self.new_sales_price <= self.total_cost_price:
            self.warning_msg = "Warning! New sales price is equal or less than the total cost price."
        if self.new_sales_price == self.old_sales_price:
            raise UserError(
                _("Warning! New sales price and old sales price is same.")
            )
        else:
            self.product_id.list_price = self.new_sales_price
            # self.product_id.mapped("product_variant_ids").write({"fix_price": self.new_sales_price})
            self.product_id.mapped("product_variant_ids").write(
                {"list_price": self.new_sales_price,
                 "lst_price": self.new_sales_price,
                 "foreign_sales_currency_id": self.currency_id.id,
                 "foreign_sales_rate": self.rate,
                 "foreign_sales_price": self.foreign_sales_price}
            )
            self.env['sales.price.update'].create({
                'product_id': self.product_id.id,
                'currency_id': self.currency_id.id,
                'rate': self.rate,
                'foreign_sales_price': self.foreign_sales_price,
                'old_sales_price': self.old_sales_price,
                'new_sales_price': self.new_sales_price,
                'cost_price': self.cost_price,
                'other_cost_price': self.other_cost_price,
                'total_cost_price': self.total_cost_price,
                'approved_by_id': self.approved_by_id.id,
            })
            if self._context.get('is_confirmed'):
                self.success_msg = "New sales price {:.2f} of '{}' updated successfully.".format(self.new_sales_price,
                                                                                                 self.product_id.display_name)
            self.new_sales_price = 0
            # self.warning_msg = ""
            return {
                'name': _('Sales Price Update'),
                'context': self.env.context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sales.price.update.wizard',
                'res_id': self.id,
                'view_id': False,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }
