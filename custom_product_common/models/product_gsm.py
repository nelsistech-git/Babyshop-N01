from odoo import models, fields

class ProductGsm(models.Model):
    _name = 'product.gsm'
    _description = 'Product GSM'

    name = fields.Char(string='GSM Value', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'GSM value must be unique!')
    ]