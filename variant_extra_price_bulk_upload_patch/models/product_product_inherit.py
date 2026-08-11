from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    extra_price = fields.Float(
        string="Variant Extra Price for Bulk Upload Extra Price"
    )

    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        if "extra_price" in vals:
            for product in self:
                ptav_ids = product.product_template_attribute_value_ids
                if ptav_ids:
                    ptav_ids.write({"price_extra": 0})
                    ptav_ids[0].price_extra = vals.get("extra_price", 0)
        return res
