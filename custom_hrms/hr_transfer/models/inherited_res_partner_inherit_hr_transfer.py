from odoo import models, fields, api,_,tools
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class InheritedResPartnerHRTransfer(models.Model):
    _inherit = 'res.partner'

    other_company_code = fields.Char(string="Other Company Code.", copy=False)