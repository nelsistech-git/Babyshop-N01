from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import date


class InheritedStockChangeStandardPriceInheritCustomStock(models.TransientModel):
    _inherit = "stock.change.standard.price"
    _description = "Change Standard Price"

    currency_id = fields.Many2one('res.currency', 'Currency',
                                  domain="['|', ('active', '=', True), ('active', '=', False)]",
                                  default=lambda self: self.env['res.currency'].search([('name', '=', 'BDT')]))
    currency = fields.Char('Currency Name', related='currency_id.name')
    rate = fields.Float(string='Rate (BDT)', digits=(16, 2))
    foreign_cost_price = fields.Float(string='Foreign Cost Price', default=0.00, digits=(16, 2))

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

    @api.onchange('foreign_cost_price')
    def _onchange_foreign_cost_price(self):
        for rec in self:
            if rec.currency_id:
                if rec.currency_id.name != 'BDT':
                    if rec.foreign_cost_price < 0:
                        rec.rate = rec.foreign_cost_price * (-1)
                    elif rec.foreign_cost_price == 0:
                        raise UserError('Input Foreign Cost Price that is greater than zero.')

    @api.onchange('currency_id', 'rate', 'foreign_cost_price')
    def _onchange_currency(self):
        if self.currency_id.name != 'BDT':
            new_sales_price = self.rate * self.foreign_cost_price
            self.new_price = new_sales_price

    def change_price(self):
        res = super(InheritedStockChangeStandardPriceInheritCustomStock, self).change_price()
        if self.currency_id.name != 'BDT':
            if self._context['active_model'] == 'product.template':
                products = self.env['product.template'].browse(self._context['active_id']).product_variant_ids
            else:
                products = self.env['product.product'].browse(self._context['active_id'])
            for rec in products:
                rec.foreign_cost_currency_id = self.currency_id
                rec.foreign_cost_rate = self.rate
                rec.foreign_cost_price = self.foreign_cost_price
        return res