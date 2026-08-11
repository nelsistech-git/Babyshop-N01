from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
import math
from dateutil.relativedelta import relativedelta


class EmployeeLoanEarlySettlementRemissionWizard(models.TransientModel):
    _name = "emp.loan.early.settle.remission.wizard"
    _description = "Employee Loan Early Settlement Remission Wizard"

    employee_id = fields.Many2one('hr.employee', string='Employee')
    type = fields.Selection([
        ('es', 'Early Settlement'),
        ('remission', 'Remission')
    ], string='Type', default='es')
    loan_amt = fields.Float('Loan Amount')
    paid_amt = fields.Float('Paid Amount')
    remain_amt = fields.Float('Remaining Amount')
    new_remain_amt = fields.Float('New Remaining Amount', compute='_compute_new_remain_amt')
    term = fields.Integer('Term')
    amount = fields.Float()
    remission_reason = fields.Many2one('loan.remission.type', 'Remission Reason')
    remain_term = fields.Float('Remaining Term')

    journal_id = fields.Many2one('account.journal', 'Journal')
    debit_account_id = fields.Many2one('account.account', 'Debit(Bank/Cash) Account')
    credit_account_id = fields.Many2one('account.account', 'Credit (Loan) Account')
    paid_date = fields.Date('Paid Date')

    @api.model
    def default_get(self, fields):
        res = super(EmployeeLoanEarlySettlementRemissionWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        loan_obj = self.env['employee.loan'].browse(active_id)
        res['employee_id'] = loan_obj.employee_id.id
        res['loan_amt'] = loan_obj.loan_amount
        res['paid_amt'] = loan_obj.paid_amount
        res['remain_amt'] = loan_obj.remaing_amount
        res['term'] = loan_obj.term
        res['journal_id'] = loan_obj.loan_type_id.journal_id.id if loan_obj.loan_type_id.journal_id else None
        res[
            'debit_account_id'] = loan_obj.loan_type_id.loan_payment_account_rcv.id if loan_obj.loan_type_id.loan_payment_account_rcv else None
        res['credit_account_id'] = loan_obj.loan_type_id.loan_account.id if loan_obj.loan_type_id.loan_account else None
        unpaid_inst_lines = loan_obj.installment_lines.filtered(lambda x: x.is_paid is False)
        res['remain_term'] = len(unpaid_inst_lines)
        return res

    @api.onchange('remission_reason')
    def _onchange_remission_reason(self):
        if self.remission_reason:
            self.debit_account_id = self.remission_reason.debit_account_id.id

    @api.onchange('amount', 'type')
    def _onchange_early_settle_amt_check(self):
        if self.amount > self.remain_amt:
            if self.type == 'es':
                raise ValidationError("Early Settlement Amount can't be more than remain amount.")
            else:
                raise ValidationError("Remission Amount can't be more than remain amount.")

    @api.depends('amount')
    def _compute_new_remain_amt(self):
        if self.amount <= self.remain_amt:
            self.new_remain_amt = self.remain_amt - self.amount

    def recompute_inst_and_confirm(self):
        new_distribution = False

        type = self.type
        paid_date = self.paid_date

        active_id = self.env.context.get('active_id')
        loan_obj = self.env['employee.loan'].browse(active_id)

        unpaid_inst_lines = loan_obj.installment_lines.filtered(lambda x: x.is_paid is False)
        new_remain_amt = self.new_remain_amt
        pay_amt = self.amount

        ref = ''

        if len(unpaid_inst_lines) > 0:
            # account move create start
            if self.journal_id and self.journal_id.is_pf_display:
                fs_dept = 'pf'
            else:
                fs_dept = 'accounts'
            vals = {
                'date': paid_date,
                'journal_id': self.journal_id and self.journal_id.id,
                'company_id': self.env.user.company_id.id,
                'partner_id': loan_obj.partner_id.id,
                'fs_dept': fs_dept
            }
            acc_move_id = self.env['account.move'].create(vals)
            # account move create end

        # early settlement or remission loop
        for rec in range(len(unpaid_inst_lines)):
            inst_amt = unpaid_inst_lines[rec].installment_amt

            if inst_amt <= pay_amt:
                pay_amt = pay_amt - inst_amt
                unpaid_inst_lines[rec].is_paid = True
                unpaid_inst_lines[rec].paid_date = paid_date
                unpaid_inst_lines[rec].move_id = acc_move_id.id or None

                # early settlement or remission
                if type == 'es':
                    unpaid_inst_lines[rec].is_early_settlement = True
                else:
                    unpaid_inst_lines[rec].is_remission = True

                # Account Move Reference
                ref = ref + unpaid_inst_lines[rec].name + ', '

                if pay_amt == 0:
                    break
            else:
                unpaid_inst_lines[rec - 1].installment_amt = unpaid_inst_lines[rec - 1].installment_amt + pay_amt
                new_distribution = True
                pay_amt = 0
                break

        # journal entry start

        if type == 'es':
            ref = 'Early Settlement: ' + ref  # Early Settlement Move Reference
        else:
            ref = 'Remission: ' + ref  # Remission Move Reference

        lst = []

        lst.append((0, 0, {
            'account_id': self.debit_account_id.id or False,
            'partner_id': False,
            'name': ref,
            'debit': self.amount or 0.0,
        }))

        lst.append((0, 0, {
            'account_id': self.credit_account_id.id or False,
            'partner_id': loan_obj.partner_id.id or False,
            'name': ref,
            'credit': self.amount or 0.0,
        }))

        acc_move_id.line_ids = lst
        acc_move_id.ref = ref
        acc_move_id.action_post()

        # journal entry end

        # recomputing installment lines
        if new_distribution:
            unpaid_inst_lines = loan_obj.installment_lines.filtered(lambda x: x.is_paid is False)
            last_remain_amt = new_remain_amt
            new_term = len(unpaid_inst_lines)
            new_inst = math.ceil(last_remain_amt / new_term)

            for rec2 in range(len(unpaid_inst_lines)):
                if last_remain_amt < new_inst:
                    new_inst = last_remain_amt

                unpaid_inst_lines[rec2].installment_amt = new_inst
                last_remain_amt = last_remain_amt - new_inst

                if last_remain_amt < 0:
                    break

        loan_obj.get_paid_amount()


class LoanInstallmentPaymentWizard(models.TransientModel):
    _name = "loan.installment.payment.wizard"
    _description = "Loan Installment Payment Wizard"

    loan_id = fields.Many2one('employee.loan', string='Loan')
    employee_id = fields.Many2one('hr.employee', string='Employee', related="loan_id.employee_id")
    partner_id = fields.Many2one('res.partner', string='Private Address', related='employee_id.address_home_id')
    installment_id = fields.Many2one('installment.line', string='Installment')
    date = fields.Date('Date', related="installment_id.date")
    is_skip = fields.Boolean('Skip EMI (Inst.)', related="installment_id.is_skip")
    is_paid = fields.Boolean('Paid', related="installment_id.is_paid")
    paid_date = fields.Date('Paid Date')

    installment_amt = fields.Float('EMI (Inst.) Amount', related="installment_id.installment_amt")
    ins_interest = fields.Float('Interest Amount', related="installment_id.ins_interest")
    total_installment = fields.Float('Paid Amount', related="installment_id.total_installment")

    journal_id = fields.Many2one('account.journal', 'Journal')
    credit_account_id = fields.Many2one('account.account', 'Loan/Credit Account')
    debit_account_id = fields.Many2one('account.account', 'Payment/Debit Account')
    interest_account_id = fields.Many2one('account.account', 'Interest/Debit Account')

    @api.model
    def default_get(self, fields):
        res = super(LoanInstallmentPaymentWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        loan_line_obj = self.env['installment.line'].browse(active_id)
        loan_obj = loan_line_obj.loan_id

        res['loan_id'] = loan_obj.id
        res['installment_id'] = loan_line_obj.id

        d2 = loan_line_obj.date.replace(day=1) + relativedelta(months=1) - relativedelta(days=1)
        res['paid_date'] = d2

        res['journal_id'] = loan_obj.loan_type_id.journal_id.id if loan_obj.loan_type_id.journal_id else None
        res['credit_account_id'] = loan_obj.loan_type_id.loan_account.id if loan_obj.loan_type_id.loan_account else None
        res[
            'debit_account_id'] = loan_obj.loan_type_id.loan_payment_account_rcv.id if loan_obj.loan_type_id.loan_payment_account_rcv else None
        res[
            'interest_account_id'] = loan_obj.loan_type_id.interest_account.id if loan_obj.loan_type_id.interest_account else None

        return res

    def confirm(self):
        loan_obj = self.loan_id
        installment_obj = self.installment_id
        installment_amt = self.installment_amt
        ins_interest = self.ins_interest
        pay_amt = installment_amt + ins_interest

        # account move create start
        if self.journal_id and self.journal_id.is_pf_display:
            fs_dept = 'pf'
        else:
            fs_dept = 'accounts'
        vals = {
            'date': self.paid_date,
            'journal_id': self.journal_id and self.journal_id.id,
            'company_id': self.env.user.company_id.id,
            'partner_id': self.partner_id.id or False,
            'ref': 'Loan Inst.Paid: ' + installment_obj.loan_id.name,
            'fs_dept': fs_dept
        }
        acc_move_id = self.env['account.move'].create(vals)

        ref = 'Loan paid Inst.No: %s' % (installment_obj.name)
        lst = []
        lst.append((0, 0, {
            'account_id': self.debit_account_id.id or False,
            'partner_id': False,
            'name': ref,
            'debit': installment_amt or 0.0,
        }))
        if ins_interest > 0:
            lst.append((0, 0, {
                'account_id': self.interest_account_id.id or False,
                'partner_id': self.partner_id.id or False,
                'name': ref,
                'debit': ins_interest or 0.0,
            }))

        lst.append((0, 0, {
            'account_id': self.credit_account_id.id or False,
            'partner_id': self.partner_id.id or False,
            'name': ref,
            'credit': pay_amt or 0.0,
        }))

        acc_move_id.line_ids = lst
        if acc_move_id:
            installment_obj.is_paid = True
            installment_obj.paid_date = self.paid_date
            installment_obj.move_id = acc_move_id.id

            acc_move_id.action_post()

        loan_obj.get_paid_amount()
