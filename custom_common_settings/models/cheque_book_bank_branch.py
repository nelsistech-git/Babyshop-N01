from odoo import models, fields, api
from odoo.addons.helper import validator


class ChequeBookBankBranch(models.Model):
    _name = "cheque.book.bank.branch"
    _description = "Cheque Book Bank Branch"

    name = fields.Char(string='Branch Name', required=True)
    bank_id = fields.Many2one('cheque.book.bank', required=True, ondelete='cascade')
    routing = fields.Char(string='Routing No.')
    address = fields.Char(string='Address')
    remarks = fields.Text(string='Remarks')
    active = fields.Boolean(default=True)

    @api.constrains('name', 'bank_id')
    def _check_unique_constraint_cheque_name(self):
        for rec in self:
            msg = 'Branch name "%s"' % rec.name
            envobj = self.env['cheque.book.bank.branch']
            conditionlist = [('bank_id', '=', rec.bank_id.id), ('name', '=', rec.name)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)
