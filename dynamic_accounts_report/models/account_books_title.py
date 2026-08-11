from odoo import fields, models, api


class AccountBooksTitle(models.Model):
    _name = "account.books.title"
    _description = "Account Books Title"
    _order = "name"

    name = fields.Char(string='Name')
    account_tag_ids = fields.Many2many('account.account.tag', string='Account Groups')
    account_ids = fields.Many2many('account.account', string='Accounts')

    @api.onchange('account_tag_ids')
    def _onchange_get_account_ids(self):
        if self.account_tag_ids:
            account_ids = self.env['account.account'].search([('tag_ids', '=', self.account_tag_ids.ids)]).mapped('id')
            # return {'domain': {'account_ids': [('id', 'in', account_ids)]}, 'value': {'account_ids': account_ids}}
            return {'domain': {'account_ids': [('id', 'in', account_ids)]}}
        else:
            return {'domain': {'account_ids': [('id', 'in', None)]}, 'value': {'account_ids': None}}
