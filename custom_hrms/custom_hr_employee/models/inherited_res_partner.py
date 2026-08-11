from odoo import models, fields, api
from odoo.addons.helper import validator


class InheritedResPartnerInheritHr(models.Model):
    _inherit = 'res.partner'
    _description = 'Inherited Res Partner Inherit HR'

    is_employee = fields.Boolean(string='Is Employee?', default=False)
    employee_id = fields.Char(string='Employee ID')
    followers_type = fields.Char(string='Followers Type')
    product_details = fields.Char(string='Product Details')
    fabric_type = fields.Selection([
        ('kint', 'Knit'),
        ('woven', 'Woven'),
        ('both', 'Both'),
    ],string='Fabric Type')

    business_type = fields.Char(string='Business Type')

    # hide_peppol_fields = fields.Boolean(string="Hide Peppol Fields")

class InheritedResBank(models.Model):
    """ Customization of res.partner.bank model """

    _inherit = 'res.partner.bank'

    acc_number = fields.Char('Account Number', required=True)

    @api.onchange('acc_number')
    def _remove_space_acc_number(self):
        for r in self:
            if r.acc_number:
                r.acc_number = str(r.acc_number).strip()

    @api.constrains('acc_number')
    def _check_unique_constraint_acc_number(self):
        msg = "Bank Account"
        envObj = self.env['res.partner.bank']

        conditionList1 = [('acc_number', '=ilike', self.acc_number)]
        validator.check_duplicate_value(self, envObj, conditionList1, msg)

class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    followers_type = fields.Char(
        string='Followers Type',
    )
    product_details = fields.Char(
        string='Product Details',
    )
    fabric_type = fields.Selection([
        ('kint', 'Knit'),
        ('woven', 'Woven'),
        ('both', 'Both'),
    ], string='Fabric Type',
    )
    business_type = fields.Char(
        string='Business Type',
    )