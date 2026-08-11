from odoo import models, fields, api


class InheritedResPartnerInheritProductCommon(models.Model):
    _inherit = "res.partner"
    _description = "Vendor Modification"

    vat_exempted = fields.Selection([
        ('no', 'No'),
        ('yes', 'Yes'), ], string="VAT Exempted", default="no")
    tin_number = fields.Char(string='TIN No.')
    bin_no = fields.Char(string='BIN', tracking=True)
    trade_license_nd_authority = fields.Char(string='Trade License No. & Authority')
    #credit_limit = fields.Char(string='Credit Limit')
    vendor_code = fields.Char(string='Code', readonly=True, default='')
    vendor_type = fields.Selection([
        ('local', 'LOCAL'),
        ('foreign', 'FOREIGN')
    ], string='Local/Foreign', default='local', copy=False)
