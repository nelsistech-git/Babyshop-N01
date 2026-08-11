from odoo import models, fields, api
from odoo.addons.helper import validator
from odoo.osv import expression


class InheritedProductInheritCustomProductCommon(models.Model):
    _inherit = 'product.product'

    other_cost = fields.Float(default=0, string='Other Cost', copy=False, digits=(16, 3))
    default_qty = fields.Float(string="Default Quantity", default=1)

    # @api.model
    # def create(self, vals):
    #     res = super(InheritedProductInheritCustomProductCommon, self).create(vals)
    #     if res.product_tmpl_id.default_qty:
    #         res.default_qty = res.product_tmpl_id.default_qty
    #     return res
    
    # @api.model
    # def name_search(self, name, args=None, operator='ilike', limit=100):
    #     """
    #     name search that supports searching by tag code
    #     """
    #     args = args or []
    #     domain = []
    #     if name:
    #         # search_value = name.split(" ", 1)
    #         # if len(search_value) > 1 and  search_value[1]:
    #         #     domain = [('code', '=ilike', search_value[0] + '%'), ('name', '=ilike', search_value[1] + '%')]
    #         #     domain = ['|', ('product_template_attribute_value_ids', 'ilike', search_value[0]), ('name', operator, search_value[0])]
    #         # else:
    #         domain = ['|', '|', ('product_template_attribute_value_ids', 'ilike', name), ('name', operator, name), ('barcode', 'ilike', name)]
    #         if operator in expression.NEGATIVE_TERM_OPERATORS:
    #             domain = ['&'] + domain
    #     products = self.search(domain + args, limit=limit)
    #     return products.name_get()