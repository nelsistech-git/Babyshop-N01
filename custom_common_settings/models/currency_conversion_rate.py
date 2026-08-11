import logging
from odoo import fields, models, api
from odoo.addons.helper import validator
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)


class CurrencyConversionRate(models.Model):
    _name = 'currency.conversion.rate'
    _description = 'Currency Conversion Rate'
    _rec_name = 'date'
    _order = 'date desc'

    date = fields.Date(string='Date', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  domain=['|', ('active', '=', True), ('active', '=', False)], required=True)
    rate = fields.Float(string='Amount (BDT)', default=0, required=True, digits=(16, 4))

    def name_get(self):
        res = []
        for field in self:
            res.append((field.id, '%s (%s %s)' % (
            format_date(self.env, self.date, date_format="dd-MMM-Y"), field.currency_id.name, field.rate)))
        return res

    @api.constrains('date', 'currency_id')
    def _check_unique_constraint_date_currency(self):
        msg = 'Same currency "%s" of the Date ' % self.currency_id.name
        envobj = self.env['currency.conversion.rate']
        conditionlist = [('date', '=', self.date), ('currency_id', '=', self.currency_id.id), ('rate', '=', self.rate)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)
