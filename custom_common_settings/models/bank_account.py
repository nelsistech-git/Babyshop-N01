from odoo import models, fields


class BankAccount(models.Model):
    _name = "bank.account"
    _description = "Bank Account"

    name = fields.Char(string='A/C Name')
    acc_number = fields.Char(string='A/C Number')
    bank_id = fields.Many2one('cheque.book.bank', ondelete='cascade')
    bank_branch_id = fields.Many2one('cheque.book.bank.branch', domain="[('bank_id', '=', bank_id)]")
    account_type_id = fields.Many2one('bank.account.type')
    remarks = fields.Text(string='Remarks')
    active = fields.Boolean(default=True)

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.acc_number:
                name = "%s - %s" % (name, record.acc_number)
            result.append((record.id, name))
        return result

    # @api.constrains('bank_id', 'bank_branch_id', 'acc_number')
    # def _check_unique_constraint_acc_number(self):
    #     for rec in self:
    #         msg = 'Account Number "%s"' % rec.name
    #         envobj = self.env['bank.account']
    #         conditionlist = [('bank_id', '=', rec.bank_id),('bank_branch_id', '=', rec.bank_branch_id),('acc_number', '=', rec.acc_number)]
    #         validator.check_duplicate_value(rec, envobj, conditionlist, msg)
