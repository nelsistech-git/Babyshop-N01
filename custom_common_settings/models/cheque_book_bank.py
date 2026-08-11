from odoo import models, fields, api
from odoo.addons.helper import validator


class ChequeBookBank(models.Model):
    _name = "cheque.book.bank"
    _description = "Cheque Book Bank"

    name = fields.Char(string='Name', required=True)
    swift_code = fields.Char(string='SWIFT Code')
    routing = fields.Char(string='Routing')
    remarks = fields.Text(string='Remarks')
    active = fields.Boolean(default=True)

    debit_acc = fields.Many2one('account.account', 'Debit A/C', domain="[('account_type', '!=', 'view')]")
    credit_acc = fields.Many2one('account.account', 'Credit A/C', domain="[('account_type', '!=', 'view')]")
    excise_dr = fields.Many2one('account.account', 'Excise A/C', domain="[('account_type', '!=', 'view')]")
    interest_income_cr = fields.Many2one('account.account', 'Interest Income A/C',
                                         domain="[('account_type', '!=', 'view')]")
    tax_dr = fields.Many2one('account.account', 'TAX A/C', domain="[('account_type', '!=', 'view')]")
    other_charge_acc = fields.Many2one('account.account', 'Other Charge A/C', domain="[('account_type', '!=', 'view')]")

    # not used
    profit_dr = fields.Many2one('account.account', 'Profit (Dr.)', domain="[('account_type', '!=', 'view')]")
    profit_cr = fields.Many2one('account.account', 'Profit (Cr.)', domain="[('account_type', '!=', 'view')]")

    journal_id = fields.Many2one('account.journal', string='Journal')

    @api.constrains('name')
    def _check_unique_constraint_cheque_name(self):
        for rec in self:
            msg = 'Bank name "%s"' % rec.name
            envobj = self.env['cheque.book.bank']
            conditionlist = [('name', '=', rec.name)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)
