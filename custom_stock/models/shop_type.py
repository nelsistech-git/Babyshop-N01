from odoo import api, fields, models
from odoo.addons.helper import validator


class ShopType(models.Model):
    _name = "shop.type"
    _description = "Shop Type"

    name = fields.Char(string="Name", size=100, required=True, help="Name can be maximum 100 characters")
    active = fields.Boolean(string="Active", default=True)
    description = fields.Text(string="Description", help="Description can be maximum 300 characters")

    @api.constrains('description')
    def _check_grade_description_length(self):
        limit = 300
        record = self.description
        field_name = "Description"
        validator._check_length(self, record, limit, field_name)

    @api.onchange("name")
    def _onchange_name(self):
        if self.name:
            self.name = str(self.name).strip()

    @api.constrains('name')
    def _check_unique_constraint(self):
        msg = "Type Name"
        envObj = self.env['shop.type']
        conditionList = [('name', '=ilike', self.name), '|', ('active', '=', True), ('active', '=', False)]
        validator.check_duplicate_value(self, envObj, conditionList, msg)
