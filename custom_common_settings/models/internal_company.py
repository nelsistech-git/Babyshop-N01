from odoo import models, fields, api
from odoo.addons.helper import validator


class InternalCompany(models.Model):
    _name = "internal.company"
    _description = "Internal Company"
    _order = 'name asc'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, copy=False)
    address = fields.Char(string='Address')
    note = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    receivable_acc_id = fields.Many2one('account.account', 'Receivable Account',
                                        domain="[('account_type', '!=', 'view')]")
    payable_acc_id = fields.Many2one('account.account', 'Payable Account', domain="[('account_type', '!=', 'view')]")

    payment_journal_id = fields.Many2one('account.journal', string='Payment Journal Type')
    payment_acc_id = fields.Many2one('account.account', 'Payment Account', domain="[('account_type', '!=', 'view')]")

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.name:
                name = "%s [%s]" % (name, record.code)
            result.append((record.id, name))
        return result

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = "Name"
        envObj = self.env['internal.company']
        conditionList = [('name', '=ilike', self.name)]
        validator.check_duplicate_value(self, envObj, conditionList, msg)

    @api.constrains('code')
    def _check_unique_constraint_code(self):
        msg = "Code"
        envObj = self.env['internal.company']
        conditionList = [('code', '=ilike', self.code)]
        validator.check_duplicate_value(self, envObj, conditionList, msg)
