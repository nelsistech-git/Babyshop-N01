from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_office_vendor = fields.Boolean(
        string='Office Vendor',
        default=False,
        help='Check this box if this vendor is an Office Vendor.',
    )

    type_of_work = fields.Char(string="Type of Work")