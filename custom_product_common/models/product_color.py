from odoo import fields, models, api, _
from odoo.addons.helper import validator

class ProductColor(models.Model):
    _name = "product.color"
    _description = "Product Color"

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Char(string='Description')
    active = fields.Boolean(string='Active Status', default=True)

    # _sql_constraints = [
    #     ('code', 'unique(code)', 'This style already exists!'),
    # ]

    @api.constrains('code', 'name')
    def _check_unique_constraint_code_name(self):
        for rec in self:
            msg1 = "Name `%s`" % (rec.name)
            msg2 = "Code `%s`" % (rec.code)
            envObj = self.env['product.color']

            conditionList1 = [('name', '=ilike', str(rec.name))]
            conditionList2 = [('code', '=ilike', str(rec.code))]
            
            validator.check_duplicate_value(rec, envObj, conditionList1, msg1)
            validator.check_duplicate_value(rec, envObj, conditionList2, msg2)
