from odoo import fields, models, api, _, exceptions
from odoo.addons.helper import validator


class UomConversionRate(models.Model):
    _name = 'uom.conversion.rate'
    _description = 'UoM Conversion Rate'

    from_uom_id = fields.Many2one('uom.uom', string='From 1 UoM')
    to_value = fields.Float('To Value', default=1.00)
    to_uom_id = fields.Many2one('uom.uom', string='To UoM')

    @api.onchange('to_value')
    def _onchange_to_value(self):
        if self.to_value < 0:
            raise exceptions.ValidationError(_('To value should be positive number!'))

    @api.constrains('from_uom_id', 'to_uom_id')
    def _check_unique_constraint_date_currency(self):
        msg = 'From Unit %s and To Unit %s' % (self.from_uom_id.name, self.to_uom_id.name)
        envobj = self.env['uom.conversion.rate']
        conditionlist = [('from_uom_id', '=', self.from_uom_id.id), ('to_uom_id', '=', self.to_uom_id.id)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)
