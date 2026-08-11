from odoo import fields, models, api
from odoo.exceptions import ValidationError
import math
from dateutil.relativedelta import relativedelta


class LoanRescheduleWizard(models.TransientModel):
    _name = "loan.reschedule.wizard"
    _description = "Loan Reschedule Wizard"

    employee_id = fields.Many2one('hr.employee', string='Employee')
    loan_amt = fields.Float('Loan Amount')
    paid_amt = fields.Float('Paid Amount')
    remain_amt = fields.Float('Remaining Amount')
    term = fields.Integer('Term')
    installment_amt = fields.Integer('Installment Amount')
    distributed_by = fields.Selection([
        ('term', 'Term'),
        ('inst', 'Installment Amount'),
    ], string="Distributed By", default="term")
    new_term = fields.Integer('New Term', default=0)
    new_installment_amt = fields.Float('New Installment Amount', default=0.0)

    @api.model
    def default_get(self, fields):
        res = super(LoanRescheduleWizard, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        loan_obj = self.env['employee.loan'].browse(active_id)
        res['employee_id'] = loan_obj.employee_id.id
        res['loan_amt'] = loan_obj.loan_amount
        res['paid_amt'] = loan_obj.paid_amount
        res['remain_amt'] = loan_obj.remaing_amount
        res['term'] = loan_obj.term
        res['installment_amt'] = loan_obj.installment_amount
        res['term'] = len(loan_obj.installment_lines.ids)
        res['installment_amt'] = loan_obj.installment_lines[0].installment_amt
        return res

    @api.onchange('new_installment_amt')
    def _onchange_new_installment_amt_amt_check(self):
        if self.new_installment_amt > self.remain_amt:
            raise ValidationError("New Installment Amount can't be more than remain amount.")

    @api.depends('distributed_by', 'new_term', 'remain_amt')
    def _compute_new_inst_amt(self):
        for loan in self:
            if loan.distributed_by == 'term':
                if loan.remain_amt > 0 and loan.new_term > 0:
                    loan.new_installment_amt = round(loan.remain_amt / loan.new_term)
                else:
                    loan.new_installment_amt = 0.0

    @api.depends('distributed_by', 'remain_amt', 'new_installment_amt')
    def _compute_new_term(self):
        for loan in self:
            if loan.distributed_by == 'inst':
                if loan.remain_amt > 0 and loan.new_installment_amt > 0:
                    loan.new_term = math.ceil(loan.remain_amt / loan.new_installment_amt)
                else:
                    loan.new_term = 0.0

    @api.onchange('distributed_by', 'remain_amt', 'new_installment_amt', 'new_term')
    def _onchange_distributed_by(self):
        if self.distributed_by == 'inst':
            if self.remain_amt > 0 and self.new_installment_amt > 0:
                self.new_term = math.ceil(self.remain_amt / self.new_installment_amt)
            else:
                self.new_term = 0.0
        elif self.distributed_by == 'term':
            if self.remain_amt > 0 and self.new_term > 0:
                self.new_installment_amt = round(self.remain_amt / self.new_term)
            else:
                self.new_installment_amt = 0.0
        else:
            self.new_term = 0.0
            self.new_installment_amt = 0.0

    def recompute_inst_and_confirm(self):
        active_id = self.env.context.get('active_id')
        loan_obj = self.env['employee.loan'].browse(active_id)

        new_inst_amt = self.new_installment_amt
        new_term = self.new_term
        loan_amt = self.remain_amt

        if new_term <= 0:
            raise ValidationError("New Term must be greater than zero.")
        if new_inst_amt <= 0:
            raise ValidationError("New Installment Amount must be greater than zero.")

        unpaid_inst_lines = loan_obj.installment_lines.filtered(lambda x: x.is_paid is False)
        paid_inst_lines = loan_obj.installment_lines.filtered(lambda x: x.is_paid is True)

        loan_no = len(paid_inst_lines)

        start_date = []

        # deleting unpaid installment lines
        if unpaid_inst_lines:
            for rec in unpaid_inst_lines:
                rec.unlink()

        if paid_inst_lines:
            start_date = [rec.date for rec in paid_inst_lines]
            inst_start_date = start_date[-1] + relativedelta(months=1)
        else:
            inst_start_date = loan_obj.start_date
        # recomputing installment lines
        new_inst_list = []
        for i in range(0, new_term):
            date = inst_start_date + relativedelta(months=i)
            amount = self.loan_amt
            interest_amount = 0.0
            ins_interest_amount = 0.0
            if loan_obj.is_apply_interest:
                interest_amount = ((amount * new_term / 12) * loan_obj.interest_rate) / 100

                if loan_obj.interest_rate and amount and loan_obj.interest_type == 'reduce':
                    amount = interest_amount - (new_inst_amt * i)
                    interest_amount = ((amount * new_term / 12) * loan_obj.interest_rate) / 100
                ins_interest_amount = interest_amount / new_term

            if loan_amt > new_inst_amt:
                installment_amt = new_inst_amt
                loan_amt = loan_amt - installment_amt
            else:
                installment_amt = loan_amt
            new_inst_list.append((0, 0, {
                'name': 'INS - ' + loan_obj.name + ' - ' + str(loan_no + 1),
                'employee_id': loan_obj.employee_id and loan_obj.employee_id.id or False,
                'date': date,
                'amount': amount,
                'interest': interest_amount,
                'installment_amt': installment_amt,
                'ins_interest': ins_interest_amount,
            }))
            loan_no = loan_no + 1

        loan_obj.installment_lines = new_inst_list

        msg = """
            Distributed by: {0},
            New Term: {1},
            New Installment Amount: {2}
            """.format(dict(self._fields['distributed_by'].selection).get(self.distributed_by), self.new_term,
                       self.new_installment_amt)
        loan_obj.message_post(body=msg)
        loan_obj.is_revised = True
