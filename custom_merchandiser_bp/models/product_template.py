from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fabric_type = fields.Char(string="Fabric Type")
    gsm = fields.Char(string="GSM")
    color = fields.Char(string="Color")
    size_range = fields.Char(string="Size Range")
