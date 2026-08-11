from odoo import models, fields, _, api


class CheckBarcodeDetailsWizard(models.TransientModel):
    _name = 'check.barcode.details.wizard'
    _description = 'Check Barcode Details Wizard'

    barcode = fields.Char(string='Barcode')
    product_id = fields.Many2one('product.product', string='Product')
    style = fields.Many2one('product.style', string='Style')
    attribute_ids = fields.Many2many('product.template.attribute.value', 'barcode_details_attribute_rel', 'barcode_details_id', 'attribute_id', string='Attribute(s)')
    country = fields.Many2one('res.country', string='Country')
    brand = fields.Many2one('product.brand', string='Brand')
    category_id = fields.Many2one('product.category', string='Category')
    sales_price = fields.Float(string='Sales Price')

    @api.onchange('barcode')
    def _onchange_product_details(self):
        if self.barcode:
            product_id = self.env['product.product'].search([('barcode', '=', self.barcode)])
            product_tmpl_id = product_id.product_tmpl_id
            self.product_id = product_id.id
            self.category_id = product_tmpl_id.categ_id.id
            self.sales_price = product_id.lst_price
            self.style = product_tmpl_id.style_id.id
            self.attribute_ids = product_id.product_template_attribute_value_ids.ids
            self.country = product_id.country_id
            self.brand = product_id.brand




