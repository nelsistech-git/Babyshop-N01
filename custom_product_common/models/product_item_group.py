from odoo import fields, models, api, _
from odoo.addons.helper import validator


class ProductItemGroup(models.Model):
    _name = "product.item.group"
    _description = "Product Item Group"

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Char(string='Description')
    active = fields.Boolean(string='Active Status', default=True)

    @api.constrains('code', 'name')
    def _check_unique_constraint_code_name(self):
        for rec in self:
            msg1 = "Name `%s`" % (rec.name)
            msg2 = "Code `%s`" % (rec.code)
            envObj = self.env['product.item.group']

            conditionList1 = [('name', '=ilike', str(rec.name))]
            conditionList2 = [('code', '=ilike', str(rec.code))]

            validator.check_duplicate_value(rec, envObj, conditionList1, msg1)
            validator.check_duplicate_value(rec, envObj, conditionList2, msg2)

class ProductItemGroupType(models.Model):
    _name = "product.item.group.type"
    _description = "Product Item Group Type"

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Char(string='Description')
    active = fields.Boolean(string='Active Status', default=True)

    @api.constrains('code', 'name')
    def _check_unique_constraint_code_name(self):
        for rec in self:
            msg1 = "Name `%s`" % (rec.name)
            msg2 = "Code `%s`" % (rec.code)
            envObj = self.env['product.item.group.type']

            conditionList1 = [('name', '=ilike', str(rec.name))]
            conditionList2 = [('code', '=ilike', str(rec.code))]

            validator.check_duplicate_value(rec, envObj, conditionList1, msg1)
            validator.check_duplicate_value(rec, envObj, conditionList2, msg2)
