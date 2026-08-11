from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PFConfiguration(models.Model):
    _name = "pf.configuration"
    _description = "Provident Fund Settlement Configuration"

    type = fields.Selection([('loan', 'PF Loan Policy'), ('settlement', 'PF Settlement Policy'),
                             ('loan_settlement', 'PF Loan & Settlement Policy')], string='Apply Type',
                            default='loan_settlement')

    name = fields.Char(string='Name', required=True)
    eligibility_based_on = fields.Selection([('joining_date', 'Joining Date'),
                                             ('confirmation_date', 'Confirmation Date'),
                                             ('pf_membership_date', 'PF Membership Date')],
                                            string="Eligibility Based On",
                                            required=True)
    amount_source = fields.Selection([
        ('pf', 'PF Salary Portion'),
        ('pf_both', 'PF ALL Portion'),
        ('cpf', 'CPF Salary Portion'),
        ('cpf_both', 'CPF ALL Portion'),
        ('pf_cpf', 'PF & CPF Salary Portion'),
        ('pf_cpf_both', 'PF & CPF ALL Portion')
    ],
        string="Amount Source")
    note = fields.Char(string='Note')
    minimum_loan_amount = fields.Float(string="Min Loan Amount", default=0.0)
    max_no_installment = fields.Integer(string="Max No. of Installment", default=1)
    minimum_installment_amount = fields.Float(string="Min Installment Amount", default=0.0)

    pf_conf_line = fields.One2many(comodel_name='pf.configuration.line', inverse_name='pf_conf_id', required=True,
                                   string='Configuration Line',
                                   copy=False, auto_join=True)

    # accounts
    journal_id_settlement = fields.Many2one('account.journal', string='Settlement Journal')

    payable_acc_id = fields.Many2one('account.account', 'Payable (Full) Account (DR)')
    loan_acc_id = fields.Many2one('account.account', 'Loan Receivable Account (CR)')
    reserve_acc_id = fields.Many2one('account.account', 'Reserve Account (CR)')
    other_acc_id = fields.Many2one('account.account', 'Other Account (CR)')
    payable_emp_acc_id = fields.Many2one('account.account', 'Employee Payable Account (CR)')

    journal_id_payment = fields.Many2one('account.journal', string='Settlement Payment Journal')
    payment_acc_id = fields.Many2one('account.account', 'Bank/Cash Account (CR)')


class PFConfigurationLine(models.Model):
    _name = "pf.configuration.line"
    _description = "Provident Fund Settlement Configuration Lines"

    pf_conf_id = fields.Many2one(comodel_name='pf.configuration', required=True, ondelete='cascade',
                                 string="Configuration ID", index=True)
    from_month = fields.Integer(string='From (Month)', required=True)
    to_month = fields.Integer(string='To (Month)', required=True)
    pf_percentage = fields.Float(string="PF (%)", default=0, required=True)
    cpf_percentage = fields.Float(string="CPF (%)", default=0, required=True)
    pf_profit_percentage = fields.Float(string="PF Profit (%)", default=0, required=True)
    cpf_profit_percentage = fields.Float(string="CPF Profit (%)", default=0, required=True)
    type = fields.Selection([
        ('0', 'General'),
        ('1', 'Termination'),
        ('2', 'Death'),
    ], string="Settlement Type", default="0")

    @api.constrains('cpf_percentage')
    def _check_cpf_percentage(self):
        for rec in self:
            if rec.pf_percentage:
                if rec.pf_percentage > 100 or rec.pf_percentage < 0:
                    raise UserError(
                        _('PF Percentage must not greater than 100 or Less than 0. Please update PF Percentage.'))

            if rec.cpf_percentage:
                if rec.cpf_percentage > 100 or rec.cpf_percentage < 0:
                    raise UserError(
                        _('CPF Percentage must not greater than 100 or Less than 0. Please update CPF Percentage.'))

            if rec.pf_profit_percentage:
                if rec.pf_profit_percentage > 100 or rec.pf_profit_percentage < 0:
                    raise UserError(
                        _('PF Profit Percentage must not greater than 100 or Less than 0. Please update PF Profit Percentage.'))

            if rec.cpf_profit_percentage:
                if rec.cpf_profit_percentage > 100 or rec.cpf_profit_percentage < 0:
                    raise UserError(
                        _('CPF Profit Percentage must not greater than 100 or Less than 0. Please update CPF Profit Percentage.'))


class PFProfitDisbConfiguration(models.Model):
    _name = "pf.profit.disb.configuration"
    _description = "PF Profit Disbursement Configuration"
    _rec_name = 'journal_id_disbursement'

    # accounts
    journal_id_disbursement = fields.Many2one('account.journal', string='Disbursement Journal', required=True,
                                              domain="[('is_pf_display','=',True)]")

    payable_acc_id = fields.Many2one('account.account', 'Payable Account (DR)', required=True)
    expense_acc_id = fields.Many2one('account.account', 'Expense Account (CR)', required=True)
