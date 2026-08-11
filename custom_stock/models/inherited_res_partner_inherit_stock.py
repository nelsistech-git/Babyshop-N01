from odoo import fields, models, _


class InheritResPartnerStock(models.Model):
    _inherit = "res.partner"
    _description = "Inherited Res Partner Inherit Custom Stock"

    is_courier = fields.Boolean(default=False)

