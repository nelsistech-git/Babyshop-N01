from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.helper import validator


class BudgetParticularHead(models.Model):
    _name = "budget.particular.head"
    _description = "Budget Particular Head"

    name = fields.Char(string='Name')
    fiscal_year = fields.Many2one('account.fiscal.year', string='Fiscal Year', ondelete='restrict')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='State', index=True, default='draft')
    budget_particular_line_ids = fields.One2many('budget.particular.line', 'head_id', string='Budget Particular Line')

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        for rec in self.budget_particular_line_ids:
            if rec.budget_amount < 0:
                raise UserError(_("Amount cannot be negative."))
        self.state = 'confirm'

    def action_approve(self):
        self.state = 'approve'

    def action_cancel(self):
        self.state = 'cancel'

    def action_budget_head_add_wizard(self):
        return {
            'name': 'Budget Head Add',
            'res_model': 'budget.head.add.wizard.master',
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }


class BudgetParticularLine(models.Model):
    _name = "budget.particular.line"
    _description = "Budget Particular Line"
    _order = "sub_parent_id ASC, budget_parti_child_id ASC"

    head_id = fields.Many2one('budget.particular.head', string='Budget Particular Head', ondelete="cascade")
    sub_parent_id = fields.Many2one('budget.particular.settings', string='Budget Sub-Parent',
                                    domain="[('particular_type', '=', 'sub_parent')]")
    budget_parti_child_id = fields.Many2one('budget.particular.settings', string='Budget Head',
                                            domain="[('parent_id', '=', sub_parent_id)]")
    budget_amount = fields.Float(string='Budget Amount')
    account_id = fields.Many2one('account.account', string='Chart of Accounts', ondelete='restrict')

    @api.onchange('sub_parent_id')
    def _onchange_sub_parent_id(self):
        for rec in self:
            if rec.sub_parent_id:
                return {'domain': {
                    'budget_parti_child_id': [('parent_id', '=', rec.sub_parent_id.id)]
                }, 'value': {'budget_parti_child_id': None, 'account_id': None, 'budget_amount': None}}
            else:
                return {'domain': {
                    'budget_parti_child_id': [('parent_id', '=', None)]
                }}

    @api.constrains('budget_parti_child_id')
    def _check_unique_constraint_account_id(self):
        for rec in self:
            if rec.budget_parti_child_id:
                msg = 'Budget Head "%s"' % rec.budget_parti_child_id.name
                envobj = self.env['budget.particular.line']
                conditionlist = [('head_id', '=', rec.head_id.id),
                                 ('budget_parti_child_id', '=', rec.budget_parti_child_id.id)]
                validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.onchange('budget_parti_child_id')
    def _onchange_budget_parti_child_id(self):
        for rec in self:
            rec.account_id = rec.budget_parti_child_id.account_id.id or rec.budget_parti_child_id.account_id
