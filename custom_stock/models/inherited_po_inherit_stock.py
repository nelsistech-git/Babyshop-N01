from odoo import models, _, fields, api


class InheritedPOInheritStock(models.Model):
    _inherit = "purchase.order"

    is_created_from_bill = fields.Boolean(default=False)