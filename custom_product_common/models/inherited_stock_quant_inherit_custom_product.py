from odoo import fields, models, api, _


class InheritedStockQuantInheritCustomProduct(models.Model):
    _inherit = 'stock.quant'

    # brand_id = fields.Many2one('product.brand', related="product_tmpl_id.brand")
    # item_group_id = fields.Many2one('product.item.group', related="product_tmpl_id.product_item_group_id")
    # item_group_type_id = fields.Many2one('product.item.group.type', related="product_tmpl_id.product_item_group_type_id")
    # categ_id = fields.Many2one('product.category', related="product_tmpl_id.categ_id")
    reserved_quantity = fields.Float(default=0)


