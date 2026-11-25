from odoo import fields, models, api, _
from odoo.addons.helper import validator


class BudgetHeadAddWizardMaster(models.TransientModel):
    _name = "budget.head.add.wizard.master"
    _description = "Budget Head Add Wizard Master"

    budget_id = fields.Many2one('budget.particular.head', string='Name')
    fiscal_year = fields.Many2one('account.fiscal.year', string='Fiscal Year', ondelete='restrict')
    sub_parent_id = fields.Many2one('budget.particular.settings', string='Budget Sub-Parent',
                                    domain="[('particular_type', '=', 'sub_parent')]")
    line_ids = fields.One2many('budget.head.add.wizard.master.line', 'master_id', string='Head Add Details')

    @api.model
    def default_get(self, fields):
        res = super(BudgetHeadAddWizardMaster, self).default_get(fields)
        budget_parti_head = self.env['budget.particular.head'].browse(self.env.context.get('active_id'))
        res['budget_id'] = budget_parti_head.id
        res['fiscal_year'] = budget_parti_head.fiscal_year.id
        return res

    @api.onchange('sub_parent_id')
    def _onchange_sub_parent_id(self):
        if self.sub_parent_id:
            self.line_ids = [(5, 0, 0)]
            # if line already exists in budget particular line append in wizard line
            parti_line = self.env['budget.particular.line'].search(
                [('head_id', '=', self.budget_id.id), ('sub_parent_id', '=', self.sub_parent_id.id)])
            parti_line_list = []
            for rec in parti_line:
                vals = {
                    'master_id': self.id,
                    'budget_parti_child_id': rec.budget_parti_child_id.id,
                    'account_id': rec.account_id.id,
                    'budget_amount': rec.budget_amount
                }
                parti_line_list.append((0, 0, vals))
            self.line_ids = parti_line_list

            # if line not exists then append in wizard line
            child_obj = self.env['budget.particular.settings'].search(
                [('particular_type', '=', 'child'), ('parent_id', '=', self.sub_parent_id.id)])
            child_list = []
            for rec in child_obj:
                if rec.id not in self.line_ids.mapped('budget_parti_child_id').ids:
                    vals = {
                        'master_id': self.id,
                        'budget_parti_child_id': rec.id,
                        'account_id': rec.account_id.id,
                    }
                    child_list.append((0, 0, vals))
            self.line_ids = child_list

    def action_submit(self):
        if self.budget_id:
            parti_obj = self.env['budget.particular.line']
            for rec in self.line_ids:
                parti_line = parti_obj.search(
                    [('head_id', '=', self.budget_id.id), ('budget_parti_child_id', '=', rec.budget_parti_child_id.id)],
                    limit=1)
                if parti_line:
                    parti_line.budget_amount = rec.budget_amount
                else:
                    vals = {
                        'head_id': self.budget_id.id,
                        'sub_parent_id': self.sub_parent_id.id,
                        'budget_parti_child_id': rec.budget_parti_child_id.id,
                        'account_id': rec.account_id.id,
                        'budget_amount': rec.budget_amount
                    }
                    parti_obj.create(vals)


class BudgetHeadAddWizardMasterLine(models.TransientModel):
    _name = "budget.head.add.wizard.master.line"
    _description = "Budget Head Add Wizard Master Line"
    _order = "budget_parti_child_id ASC"

    master_id = fields.Many2one('budget.head.add.wizard.master', string='Budget Particular Head', ondelete="cascade")
    account_id = fields.Many2one('account.account', string='Chart of Accounts', ondelete='restrict')
    budget_parti_child_id = fields.Many2one('budget.particular.settings', string='Budget Head',
                                            domain="[('parent_id', '=', 'child')]")
    budget_amount = fields.Float(string='Budget Amount')

    @api.onchange('budget_parti_child_id')
    def _onchange_budget_parti_child_id(self):
        for rec in self:
            if rec.master_id.sub_parent_id:
                return {'domain': {
                    'budget_parti_child_id': [('parent_id', '=', rec.master_id.sub_parent_id.id)]
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
                envobj = self.env['budget.head.add.wizard.master.line']
                conditionlist = [('master_id', '=', rec.master_id.id),
                                 ('budget_parti_child_id', '=', rec.budget_parti_child_id.id)]
                validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.onchange('budget_parti_child_id')
    def _onchange_budget_parti_child_id(self):
        for rec in self:
            rec.account_id = rec.budget_parti_child_id.account_id.id or rec.budget_parti_child_id.account_id
