from odoo import fields, api, models, _
from odoo.addons.helper import validator


class ProductBrand(models.Model):
    _name = "product.brand"
    _inherit = ['image.mixin']
    _description = "Product Brand"

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    image_1920 = fields.Image(required=False)
    detail = fields.Text(string='Description') #description
    active = fields.Boolean(string='Status', default=True)
    
    # _sql_constraints = [
    #     ('code', 'unique(code)', 'This brand already exists!'),
    # ]
    
    @api.constrains('code', 'name')
    def _check_unique_constraint_code_name(self):
        for rec in self:        
            msg1 = "Name `%s`" % (rec.name)
            msg2 = "Code `%s`" % (rec.code)
            envObj = self.env['product.brand']
            
            conditionList1 = [('name', '=ilike', str(rec.name))]
            conditionList2 = [('code', '=ilike', str(rec.code))]
            
            validator.check_duplicate_value(rec, envObj, conditionList1, msg1)
            validator.check_duplicate_value(rec, envObj, conditionList2, msg2)
        
        