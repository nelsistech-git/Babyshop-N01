from odoo import models, exceptions, fields, api, _
from odoo.exceptions import ValidationError
from odoo.addons.helper import validator
from datetime import date
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class InheritedPurchaseOrderCustomStock(models.Model):
    _inherit = 'purchase.order'

    is_service_invoice = fields.Boolean(string='Service Invoice', default=False)