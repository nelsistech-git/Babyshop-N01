from odoo import api, fields, models
from odoo.addons.helper import validator


class Division(models.Model):
    _name = "division"
    _description = "Division"
    _order = 'name asc'

    name = fields.Char(string="Name", required=True, size=100, help="Name can be maximum 100 characters")
    country_id = fields.Many2one("res.country", string="Country", required=True)

    @api.onchange('country_id')
    def _onchange_country_division(self):
        self.name = False

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Division Name of the country"
        envObj = self.env['division']
        conditionList = [('country_id', '=', self.country_id.id), ('name', '=ilike', self.name)]
        validator.check_duplicate_value(self, envObj, conditionList, msg)
