from odoo import models, fields


class BankAccountType(models.Model):
    _name = "bank.account.type"
    _description = " Account Type"

    name = fields.Char(string='Name', required=True)
    remarks = fields.Text(string='Remarks')
    active = fields.Boolean(default=True)
