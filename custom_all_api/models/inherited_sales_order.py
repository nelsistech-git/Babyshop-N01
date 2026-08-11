from odoo import models, fields, _
from odoo.exceptions import UserError


class SalesOrder(models.Model):
    _inherit = 'sale.order'
    _description = 'Sales Order for E-commerce'

    is_ecom_sale = fields.Boolean(string='Is Ecommerce Sale?', default=False, readonly=True)
