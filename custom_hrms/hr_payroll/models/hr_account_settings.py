from odoo import models, fields, api


class HRAccountSettings(models.Model):
    _name = 'hr.account.settings'
    _description = 'HR Account Settings'

    type = fields.Selection([
        ('loan', 'Loan'),
        ('loan_interest', 'Loan Interest'),
        ('salary_advance', 'Salary Advance'),
        ('tds', 'TDS'),
        ('pf', 'PF'),
        ('salary_payable', 'Salary Payable')
    ], required=True, default="", string='Type')

    dr_acc = fields.Many2one('account.account', string='Debit Account')
    is_transfer_dr = fields.Boolean(string='Allow Transfer?')
    is_receive_dr = fields.Boolean(string='Allow Receive?')
    cr_acc = fields.Many2one('account.account', string='Credit Account')
    is_transfer_cr = fields.Boolean(string='Allow Transfer?')
    is_receive_cr = fields.Boolean(string='Allow Receive?')

    @api.depends('type')
    def name_get(self):
        result = []
        for rec in self:
            name = dict(self._fields['type'].selection).get(rec.type)
            result.append((rec.id, name))

        return result
