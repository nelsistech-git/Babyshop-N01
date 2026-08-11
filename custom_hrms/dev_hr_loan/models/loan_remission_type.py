from odoo import models, fields


class EmployeeLoanRemissionType(models.Model):
    _name = 'loan.remission.type'
    _description = 'Loan Remission Type'

    name = fields.Char('Name', required=True)
    debit_account_id = fields.Many2one('account.account', string='Debit Account',
                                       required=True)
    credit_account_id = fields.Many2one('account.account', string='Credit Account')
