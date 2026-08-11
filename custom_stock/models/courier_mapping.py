from odoo import models, fields, api,_
from odoo.addons.helper import validator
from datetime import date
from odoo.exceptions import UserError


class CourierMapping(models.Model):
    _name = "courier.mapping"
    _description = "Courier Service"
    _rec_name = 'vendor_id'

    vendor_id = fields.Many2one('res.partner',required=True, string='Vendor', domain=[('is_courier', '=', True)])
    courier_ids = fields.One2many('courier.mapping.line', 'courier_id', string='Courier Line', copy=False)

    @api.constrains('vendor_id')
    def _check_unique_constraint_courier(self):
        for rec in self:
            msg = 'Vendor  "%s"' % rec.vendor_id.name
            envobj = self.env['courier.mapping']
            conditionlist = [('vendor_id', '=', rec.vendor_id.id)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)


class CourierMappingLine(models.Model):
    _name = "courier.mapping.line"
    _description = "Courier Service Line"
    _rec_name = 'product_id'

    courier_id = fields.Many2one('courier.mapping', required=True, string='Courier')
    product_id = fields.Many2one('product.product', required=True, string='Product', domain=[('type', '=', 'service')])
    amount = fields.Float(string='Amount', default=0,required=True)

    @api.constrains('amount')
    def _check_amount(self):
        if self.amount < 1:
            raise UserError(
                _("Amount can't be less than 1.")
            )

