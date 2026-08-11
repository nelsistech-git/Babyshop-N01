from odoo import models, fields, api
from odoo.addons.helper import validator


class BudgetParticularSettings(models.Model):
    _name = "budget.particular.settings"
    _description = "Budget Particular Settings"

    particular_type = fields.Selection([
        ('parent', 'Parent'),
        ('sub_parent', 'Sub-Parent'),
        ('child', 'Child'),
    ], string='Particular Type')
    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    parent_id = fields.Many2one('budget.particular.settings', string='Parent')
    report_type = fields.Selection([
        ('income', 'Income'),
        ('expense', 'Expense')], string='Report Type')
    account_id = fields.Many2one('account.account', string='Chart of Accounts', ondelete='restrict')
    active = fields.Boolean(string='Active', default=True)

    @api.onchange("parent_id", "report_type")
    def _onchange_parent_id(self):
        if self.parent_id:
            self.report_type = self.parent_id.report_type

    @api.onchange('particular_type')
    def _onchange_particular_type(self):
        if self.particular_type:
            code = ''
            if self.particular_type == 'parent':
                code_row = self.env['budget.particular.settings'].search([('particular_type', '=', 'parent')],
                                                                         order='code desc', limit=1)
                if code_row:
                    try:
                        code = 'P' + str(int((code_row[0].code)[1:]) + 1).zfill(4)
                    except:
                        code = 'P' + '0001'
                else:
                    code = 'P' + '0001'

            elif self.particular_type == 'sub_parent':
                code_row = self.env['budget.particular.settings'].search([('particular_type', '=', 'sub_parent')],
                                                                         order='code desc', limit=1)
                if code_row:
                    try:
                        code = 'S' + str(int((code_row[0].code)[1:]) + 1).zfill(4)
                    except:
                        code = 'S' + '0001'
                else:
                    code = 'S' + '0001'

            elif self.particular_type == 'child':
                code_row = self.env['budget.particular.settings'].search([('particular_type', '=', 'child')],
                                                                         order='code desc', limit=1)
                if code_row:
                    try:
                        code = 'C' + str(int((code_row[0].code)[1:]) + 1).zfill(4)
                    except:
                        code = 'C' + '0001'
                else:
                    code = 'C' + '0001'

            self.code = code

            # ------------------
            if self.particular_type in ['parent', 'sub_parent']:
                domain = [('particular_type', '=', 'parent')]
            elif self.particular_type == 'child':
                domain = [('particular_type', '=', 'sub_parent')]
            else:
                domain = []

            return {'domain': {
                'parent_id': domain
            }}

    @api.constrains('name')
    def _check_unique_constraint_name(self):
        msg = 'Name "%s"' % self.name
        envobj = self.env['budget.particular.settings']
        conditionlist = [('name', '=', self.name)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.constrains('code')
    def _check_unique_constraint_code(self):
        msg = 'Code "%s"' % self.code
        envobj = self.env['budget.particular.settings']
        conditionlist = [('code', '=', self.code)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.constrains('account_id')
    def _check_unique_constraint_account_id(self):
        if self.account_id:
            msg = 'Account "%s"' % self.account_id.name
            envobj = self.env['budget.particular.settings']
            conditionlist = [('account_id', '=', self.account_id.id)]
            validator.check_duplicate_value(self, envobj, conditionlist, msg)
