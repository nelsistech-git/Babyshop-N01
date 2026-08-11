from odoo import exceptions, fields, models, _
from odoo.exceptions import UserError
import base64
import datetime, time


class ProductDetailWizard(models.TransientModel):
    _name = "product.detail.wizard"
    _description = "Product Detail Wizard"

    product_id = fields.Many2one('product.product', string='Product')
    product_group = fields.Selection(related='product_id.product_group')
    tracking = fields.Selection(related='product_id.tracking')
    is_old_product = fields.Boolean(related='product_id.is_old_product')
    product_brand = fields.Many2one('product.brand') #, related='product_id.brand'
    vendor_id = fields.Many2one('res.partner', related='product_id.vendor_id')
    style_id = fields.Many2one('product.style', related='product_id.style_id')
    color_id = fields.Many2one('product.color', related='product_id.color_id')
    product_item_group_id = fields.Many2one('product.item.group', related='product_id.product_item_group_id')
    product_item_group_type_id = fields.Many2one('product.item.group.type', related='product_id.product_item_group_type_id')
    country_id = fields.Many2one('res.country', related='product_id.country_id')
    categ_id = fields.Many2one('product.category', related='product_id.categ_id')
    parent_categ_id = fields.Many2one('product.category', related='product_id.parent_categ_id')
    list_price = fields.Float(related='product_id.list_price')
    standard_price = fields.Float(related='product_id.standard_price')
    qty_available = fields.Float(related='product_id.qty_available')
    minimum_stock_qty = fields.Float(related='product_id.minimum_stock_qty')
    uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    uom_po_id = fields.Many2one('uom.uom', related='product_id.uom_po_id')
    default_code = fields.Char(related='product_id.default_code')
    barcode = fields.Char(related='product_id.barcode')
    category_code = fields.Char(related='product_id.category_code')
    default_qty = fields.Float(related='product_id.default_qty')
    type = fields.Selection(related='product_id.type')


