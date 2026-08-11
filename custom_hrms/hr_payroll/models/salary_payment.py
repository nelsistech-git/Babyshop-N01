from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

class SalaryPayment(models.Model):
    _name = "salary.payment"
    _description = "Salary Payment"

    @api.onchange('disbursement_type')
    def _onchange_payment_type(self):
        accounts = []
        if self.disbursement_type == 'bank':
            bank_journals = self.env['account.journal'].search([('type', '=', self.disbursement_type)])
            for journal in bank_journals:
                accounts.append(journal.default_account_id.id)
            return {'domain': {'bank_credit_account_id': [('id', 'in', accounts)],
                               'cash_credit_account_id': [('id', 'in', None)]}}
        elif self.disbursement_type == 'cash':
            cash_journals = self.env['account.journal'].search([('type', '=', self.disbursement_type)])
            for journal in cash_journals:
                accounts.append(journal.default_account_id.id)
            return {'domain': {'bank_credit_account_id': [('id', 'in', None)],
                               'cash_credit_account_id': [('id', 'in', accounts)]}}
        else:
            bank_accounts = []
            cash_accounts = []
            bank_journals = self.env['account.journal'].search([('type', '=', 'bank')])
            cash_journals = self.env['account.journal'].search([('type', '=', 'cash')])

            for journal in bank_journals:
                bank_accounts.append(journal.default_account_id.id)
            for journal in cash_journals:
                cash_accounts.append(journal.default_account_id.id)

            return {'domain': {'bank_credit_account_id': [('id', 'in', bank_accounts)],
                               'cash_credit_account_id': [('id', 'in', cash_accounts)]}}

    @api.onchange('struct_id')
    def _onchange_debit_acc_id(self):
        if self.struct_id:
            debit_acc_id = self.struct_id.journal_id.default_account_id

            return {'value': {'debit_account_id': debit_acc_id}}

    name = fields.Char()
    slip_ids = fields.One2many('hr.payslip', 'salary_payment_id', string='Payslips')
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    inter_company_id = fields.Many2one('internal.company', string='Inter Company',
                                       related='user_work_location_id.inter_company_id', store=True)

    department_id = fields.Many2one('hr.department', string='Department')
    company_id = fields.Many2one('res.company', string='Company', readonly=True, copy=False, required=True,
                                 default=lambda self: self.env.company)
    payment_method = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
    ], string='Payment Method', default='bank')
    disbursement_type = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('bank_cash', 'Bank & Cash')
    ], string="Payment Type", default="cash")


    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], string='Status', readonly=True, copy=False, default='draft')
    struct_id = fields.Many2one('hr.payroll.structure', string="Salary Structure")
    journal_id = fields.Many2one('account.journal', string='Journal')
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal',
                                      domain=[('type', '=', 'bank')])
    cash_journal_id = fields.Many2one('account.journal', string='Cash Journal',
                                      domain=[('type', '=', 'cash')])
    payslip_count = fields.Integer(compute='_compute_payslip_count')
    payment_date = fields.Date(string="Payment Date", default=datetime.now().date())

    bank_payment_move_id = fields.Many2one('account.move', string='Bank Payment Entry')
    cash_payment_move_id = fields.Many2one('account.move', string='Cash Payment Entry')

    date_from = fields.Date(string='Payslip From', required=True,
                            default=lambda self: fields.Date.to_string(
                                date.today().replace(day=1) - relativedelta(months=1))
                            )
    date_to = fields.Date(string='Payslip To', required=True,
                          default=lambda self: fields.Date.to_string(
                              ((date.today().replace(day=1) - relativedelta(months=1)) + relativedelta(months=+1, day=1,
                                                                                                       days=-1)))
                          )

    @api.constrains('date_from', 'date_to')
    def _check_unique_constraint_date(self):
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise UserError(_('From Date can not be greater than To date!'))

    def _compute_payslip_count(self):
        for rec in self:
            rec.payslip_count = len(self.slip_ids)

    @api.onchange('user_work_location_id')
    def _onchange_batch_payment_name(self):
        self.name = 'Batch Salary Payment{0}'.format(
            (': ' + str(self.user_work_location_id.display_name)) if self.user_work_location_id else ': All Location')

    def unlink(self):
        for rec in self:
            if any(rec.filtered(lambda rec: rec.state not in ('draft'))):
                raise UserError(_('%s can be deleted in draft state.') % rec.name)
        return super(SalaryPayment, self).unlink()

    # @api.onchange('struct_id')
    # def _onchange_debit_acc_id(self):
    #     if self.struct_id:
    #         debit_acc_id = self.struct_id.journal_id.default_account_id
    #
    #         return {'value': {'debit_account_id': debit_acc_id}}

    @api.onchange('payment_method')
    def _onchange_credit_acc_id(self):
        accounts = []
        journals = self.env['account.journal'].search([('type', '=', self.payment_method)])
        for journal in journals:
            accounts.append(journal.default_account_id.id)

        return {'domain': {'credit_account_id': [('id', 'in', accounts)],
                           'journal_id': [('type', '=', self.payment_method)]},
                'value': {'credit_account_id': accounts, 'journal_id': None}}

    # debit_account_id = fields.Many2one('account.account', 'Debit Account',
    #                                    domain="[('user_type_id.type', '!=', 'view')]")
    credit_account_id = fields.Many2one('account.account', 'Credit Account',
                                        domain="[('account_type', '!=', 'view')]")
    bank_credit_account_id = fields.Many2one('account.account', 'Bank Credit Account',
                                             domain="[('account_type', '!=', 'view')]")
    debit_account_id = fields.Many2one('account.account', 'Debit Account',
                                       domain="[('account_type', '!=', 'view')]")
    cash_credit_account_id = fields.Many2one('account.account', 'Cash Credit Account',
                                             domain="[('account_type', '!=', 'view')]")

    # comment-for-upgrade
    # bank_credit_inter_company_id = fields.Many2one('internal.company', string='Bank Inter Company',
    #                                                related='bank_credit_account_id.inter_company_id', store=True)
    # cash_credit_inter_company_id = fields.Many2one('internal.company', string='Cash Inter Company',
    #                                                related='cash_credit_account_id.inter_company_id', store=True)

    bank_credit_inter_company_id = fields.Many2one('internal.company', string='Bank Inter Company')
    cash_credit_inter_company_id = fields.Many2one('internal.company', string='Cash Inter Company')
    def action_draft(self):
        self.state = 'draft'
    def action_cancel(self):
        self.state = 'cancel'
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError('Only draft or cancelled record can be deleted!')
        return super(SalaryPayment, self).unlink()

    def action_open_payslips(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.slip_ids.ids]],
            "name": "Employee Payslips",
        }
