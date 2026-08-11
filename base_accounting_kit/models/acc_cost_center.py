from odoo import api, fields, models
from odoo.addons.helper import validator


class AccCostCenter(models.Model):
    _name = "acc.cost.center"
    _description = "Accounts Cost Center"
    _order = 'name asc'

    name = fields.Char(string="Name", required=True, size=100, help="Name can be maximum 100 characters", trim=True)
    active = fields.Boolean(default=True)

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Cost Center `%s`" % (self.name)
        envObj = self.env['acc.cost.center']
        conditionList = [('name', '=ilike', self.name), '|', ('active', '=', True), ('active', '=', False)]
        validator.check_duplicate_value(self, envObj, conditionList, msg)
