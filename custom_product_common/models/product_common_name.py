from odoo import fields, api, models, _
from odoo.addons.helper import validator


class ProductCommonName(models.Model):
    _name = "product.common.name"
    _inherit = ['image.mixin']
    _description = "Product Brand"

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(string='Status', default=True)
    
    @api.constrains('name')
    def _check_unique_constraint_name(self):
        for rec in self:        
            msg1 = "Name `%s`" % (rec.name)
            envObj = self.env['product.common.name']
            conditionList1 = [('name', '=ilike', str(rec.name))]
            validator.check_duplicate_value(rec, envObj, conditionList1, msg1)
        