from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

import math


class EmployeeLoan(models.Model):
    _name = 'employee.loan'
    _description = 'Employee Loan'
    _inherit = 'mail.thread'
    _order = 'name desc'

    loan_state = [('draft', 'Draft'),
                  ('request', 'Submit Request'),
                  ('dep_approval', 'Dept Manager Approved'),
                  ('hr_approval', 'HR Approved'),
                  ('acc_approval', 'Accounts Approved'),
                  ('trusty_approval', 'Trusty Approved'),
                  ('paid', 'Payment Disbursed'),
                  ('done', 'Running'),
                  ('close', 'Closed'),
                  ('reject', 'Rejected'),
                  ('cancel', 'Cancelled')]

    @api.model
    def _get_employee(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        return employee_id

    def _get_employees_domain(self):
        if self.env.user.user_work_location_id:
            return [('user_work_location_id', '=', self.env.user.user_work_location_id.id)]
        else:
            return []

    @api.depends('start_date', 'term')
    def _get_end_date(self):
        for loan in self:
            if loan.start_date and loan.term:
                start_date = self.start_date
                end_date = start_date + relativedelta(months=self.term)
                loan.end_date = end_date.strftime("%Y-%m-%d")
            else:
                loan.end_date = None

    @api.model
    def _get_default_type(self):
        type_obj = self.env['employee.loan.type'].search([('is_default', '=', True)], order="id asc", limit=1)
        if type_obj:
            return type_obj.id
        else:
            return []

    name = fields.Char('Name', default='/', copy=False)
    state = fields.Selection(loan_state, string='State', default='draft', tracking=True)
    employee_id = fields.Many2one('hr.employee', default=_get_employee, domain=_get_employees_domain, required=True)
    id_card_no = fields.Char(string="Employee ID", groups="hr.group_hr_user",
                             related='employee_id.id_card_no')
    joining_date = fields.Date(string='Joining Date', related='employee_id.initial_employment_date')
    date_of_confirmation = fields.Date("Confirmation Date", related='employee_id.date_of_confirmation')

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string="Designation")

    hr_manager_id = fields.Many2one('hr.employee', string='HR Manager (Approver)')
    acc_manager_id = fields.Many2one('hr.employee', string='Accounts Manager (Approver)')
    trusty_manager_id = fields.Many2one('hr.employee', string='Trusty Manager (Approver)')
    manager_id = fields.Many2one('hr.employee', string='Recommended by', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    user_id = fields.Many2one('res.users', string='Request User', default=lambda self: self.env.user)
    # job_id = fields.Many2one('hr.job', string="Job Position")
    date = fields.Date('Apply Date', default=fields.Date.context_today)
    approve_date = fields.Date('Trusty Approve Date')
    disburse_date = fields.Date('Disburse Date', default=fields.Date.context_today)
    start_date_requested = fields.Date('Requested Start Date', default=fields.Date.context_today, required=True)
    start_date = fields.Date('Approved Start Date', default=fields.Date.context_today, required=True)
    end_date = fields.Date('End Date', compute='_get_end_date')
    term = fields.Integer('EMI (Inst.) No', compute='compute_term', store=True)
    loan_type_id = fields.Many2one('employee.loan.type', string='Loan Type', required=True,
                                   default=lambda self: self._get_default_type())

    payment_method = fields.Selection([('by_payslip', 'By Payslip')], string='Payment Method', default='by_payslip',
                                      required=True)
    loan_amount = fields.Float('Actual Loan Amount', required=True)
    loan_amount_pf = fields.Float('Actual Loan (PF)', default=0, compute='_compute_loan_pf_cpf', store=True)
    loan_amount_cpf = fields.Float('Actual Loan (CPF)', default=0, compute='_compute_loan_pf_cpf', store=True)

    process_fee_amount = fields.Float('Process Fee Amount', default=0)
    loan_disbursement_amount = fields.Float('Loan Disbursable Amount', default=0,
                                            compute='_compute_loan_disbursement_amount')

    paid_amount = fields.Float('Paid Amount', compute='get_paid_amount', store=True)
    remaing_amount = fields.Float('Remaining Amount', compute='get_remaining_amount', store=True)
    remaining_pf = fields.Float('Remaining Amount (PF)', compute='get_remaining_amount', store=True)
    remaining_cpf = fields.Float('Remaining Amount (CPF)', compute='get_remaining_amount', store=True)

    installment_amount = fields.Float('EMI (Inst.) Amount', compute='compute_inst_amt', store=True)
    installment_amount_previous = fields.Float('Previous EMI (Inst.) Amount')

    requested_term = fields.Integer('Requested EMI (Inst.) No', default=0)
    requested_installment_amount = fields.Float('Requested EMI (Inst.) Amount', default=0)

    loan_url = fields.Char('URL', compute='get_loan_url')
    is_apply_interest = fields.Boolean('Apply Interest')
    interest_type = fields.Selection([('liner', 'Liner'), ('reduce', 'Reduce')], string='Interest Type')
    interest_rate = fields.Float(string='Interest Rate')
    interest_amount = fields.Float('Interest Amount', compute='get_interest_amount')
    extra_in_amount = fields.Float('Extra Int. Amount', compute='get_extra_interest')
    n_paid_amount = fields.Float(related='paid_amount', string='Paid Amount', store=True)
    n_extra_in_amount = fields.Float(related='extra_in_amount', string='Extra Interest Amount', store=True)
    n_interest_amount = fields.Float(related='interest_amount', string='Interest Amount', store=True)
    n_remaing_amount = fields.Float(related='remaing_amount', string='Remaining Amount', store=True)
    # ins_interest_amount = fields.Float('Installment Interest Amount', compute='get_install_interest_amount')
    installment_lines = fields.One2many('installment.line', 'loan_id', string='Installments')
    notes = fields.Text('Loan Reason')
    is_close = fields.Boolean('Is close?', default=False)
    move_id = fields.Many2one('account.move', string='Journal Entry')

    loan_document_line_ids = fields.One2many('dev.loan.document', 'loan_id')
    installment_count = fields.Integer(string='Inst. Count', compute='get_interest_count')
    paid_count = fields.Integer(string='Paid Count', compute='get_interest_count') #, store=True
    remaining_count = fields.Integer(string='Remaining Count', compute='get_interest_count')
    is_dm = fields.Boolean('Is Department Manager', compute='is_department_manager')
    reject_reason = fields.Text('Dept.Manager Reject Reason', copy=False)
    reject_reason_hr = fields.Text('HR Manager Reject Reason', copy=False)
    reject_reason_acc = fields.Text('Acc.Manager Reject Reason', copy=False)
    reject_reason_trusty = fields.Text('Trusty Manager Reject Reason', copy=False)
    disbursement_notes = fields.Text('Disbursement Remarks', copy=False, default='')

    loan_no = fields.Integer('Loan No')
    distributed_by = fields.Selection([
        ('term', 'EMI (Installment) No'),
        ('inst', 'EMI (Installment) Amount'),
    ], string="Distributed By", default="term")
    partner_id = fields.Many2one('res.partner', string='Private Address', related='employee_id.address_home_id')
    journal_id = fields.Many2one('account.journal', string='Journal')
    debit_loan_account = fields.Many2one('account.account', string='Loan Debit Account')
    debit_process_fee_account = fields.Many2one('account.account', string='Loan Process Fee Credit Account')
    debit_interest_account = fields.Many2one('account.account', string='Interest Debit Account')
    credit_loan_account = fields.Many2one('account.account', string='Loan Credit Account')

    is_revised = fields.Boolean('Is Revised?')

    current_balance = fields.Float('Current PF Balance', default=0.0)
    eligible_amount = fields.Float('Eligible Amount', default=0.0)
    eligible_pf = fields.Float('Eligible PF', default=0.0)
    eligible_cpf = fields.Float('Eligible CPF', default=0.0)
    current_loan = fields.Float('Current Loan', default=0.0)
    applicable_amount = fields.Float('Applicable Amount', default=0.0)
    requested_amount = fields.Float('Requested Amount', default=0.0)
    approved_amount = fields.Float('Approved Amount', default=0.0)
    is_apply_top_up = fields.Boolean('Is Top-Up Apply?')
    type_id_type = fields.Selection(string='PF/General?',
                                    related="loan_type_id.type")

    def send_loan_detail(self):
        if self.employee_id and self.employee_id.work_email:
            template_id = self.env['ir.model.data']._xmlid_lookup('dev_hr_loan.dev_employee_loan_detail_send_mail')

            template_id = self.env['mail.template'].browse(template_id[1])
            template_id.send_mail(self.ids[0], True)
        return True

    @api.depends('employee_id', 'manager_id', 'state')
    def is_department_manager(self):
        for loan in self:
            if loan.manager_id:
                if loan.manager_id.user_id.id == self.env.user.id:
                    loan.is_dm = True
                else:
                    loan.is_dm = False
            else:
                loan.is_dm = False

    @api.onchange('interest_rate', 'interest_type')
    def onchange_term_interest_type(self):
        if self.loan_type_id:
            # self.term = self.loan_type_id.loan_term
            self.interest_rate = self.loan_type_id.interest_rate
            self.interest_type = self.loan_type_id.interest_type

    @api.depends('loan_amount', 'process_fee_amount')
    def _compute_loan_disbursement_amount(self):
        for rec in self:
            rec.loan_disbursement_amount = rec.approved_amount - rec.process_fee_amount

    @api.depends('loan_amount', 'eligible_amount', 'eligible_pf')
    def _compute_loan_pf_cpf(self):
        for rec in self:
            loan_amount_pf = 0
            loan_amount_cpf = 0
            if rec.loan_type_id.type == 'pf_loan' and rec.eligible_amount > 0:
                loan_amount_pf = round((rec.loan_amount * rec.eligible_pf) / rec.eligible_amount, 2)
                loan_amount_cpf = round(rec.loan_amount - loan_amount_pf, 2)

            rec.loan_amount_pf = loan_amount_pf
            rec.loan_amount_cpf = loan_amount_cpf

    @api.depends('installment_lines')
    def get_paid_amount(self):
        for loan in self:
            amt = 0
            for line in loan.installment_lines:
                if line.is_paid:
                    if line.is_skip:
                        amt += line.ins_interest
                    else:
                        amt += line.total_installment

            loan.paid_amount = round(amt, 2)

    def compute_installment(self):
        vals = []
        loan_amt = self.loan_amount
        installment_amt = 0
        for i in range(0, self.term):
            date = self.start_date + relativedelta(months=i)
            amount = self.loan_amount
            interest_amount = 0.0
            ins_interest_amount = 0.0
            if self.is_apply_interest:
                amount = self.loan_amount
                interest_amount = (amount * self.term / 12 * self.interest_rate) / 100

                if self.interest_rate and self.loan_amount and self.interest_type == 'reduce':
                    amount = self.loan_amount - self.installment_amount * i
                    interest_amount = (amount * self.term / 12 * self.interest_rate) / 100
                ins_interest_amount = interest_amount / self.term

            if loan_amt > self.installment_amount:
                installment_amt = self.installment_amount
                loan_amt = loan_amt - installment_amt
            else:
                installment_amt = loan_amt
            vals.append((0, 0, {
                'name': 'INS - ' + self.name + ' - ' + str(i + 1),
                'employee_id': self.employee_id and self.employee_id.id or False,
                'date': date,
                'amount': amount,
                'interest': interest_amount,
                'installment_amt': installment_amt,
                'ins_interest': ins_interest_amount,
            }))
        if self.installment_lines:
            for l in self.installment_lines:
                l.unlink()
        self.installment_lines = vals

    @api.depends('paid_amount', 'loan_amount', 'interest_amount', 'extra_in_amount')
    def get_remaining_amount(self):
        for loan in self:
            loan.remaing_amount = (loan.loan_amount + loan.interest_amount + loan.extra_in_amount) - loan.paid_amount

            remaining_pf = 0
            remaining_cpf = 0
            if loan.loan_type_id.type == 'pf_loan' and loan.loan_amount > 0:
                remaining_pf = round((loan.remaing_amount * loan.loan_amount_pf) / loan.loan_amount, 2)
                remaining_cpf = round(loan.remaing_amount - remaining_pf, 2)
            loan.remaining_pf = remaining_pf
            loan.remaining_cpf = remaining_cpf

            if loan.remaing_amount <= 0 and loan.state == 'done':
                loan.is_close = True
                loan.state = 'close'

    @api.depends('installment_lines')
    def get_interest_count(self):
        for loan in self:
            if loan.installment_lines:
                loan.installment_count = len(loan.installment_lines.filtered(lambda line: line.is_skip == False))
                loan.paid_count = len(loan.installment_lines.filtered(lambda line: line.is_paid == True))
                loan.remaining_count = loan.installment_count - loan.paid_count
            else:
                loan.installment_count = 0
                loan.paid_count = 0
                loan.remaining_count = 0

    @api.depends('installment_lines', 'paid_amount')
    def get_extra_interest(self):
        for loan in self:
            amount = 0
            for installment in loan.installment_lines:
                if installment.is_skip:
                    amount += installment.ins_interest
            loan.extra_in_amount = amount

    @api.depends('loan_amount', 'interest_rate', 'is_apply_interest')
    def get_interest_amount(self):
        for loan in self:
            if loan.is_apply_interest:
                if loan.interest_rate and loan.loan_amount and loan.interest_type == 'liner':
                    loan.interest_amount = (loan.loan_amount * loan.term / 12 * loan.interest_rate) / 100
                elif loan.interest_rate and loan.loan_amount and loan.interest_type == 'reduce':
                    loan.interest_amount = (loan.remaing_amount * loan.term / 12 * loan.interest_rate) / 100
                    amt = 0.0
                    for line in loan.installment_lines:
                        amt += line.ins_interest
                    if amt:
                        loan.interest_amount = amt
                else:
                    loan.interest_amount = 0.0
                    #raise ValidationError("Loan Amount must be given.")
            else:
                loan.interest_amount = 0.0

    @api.onchange('interest_type', 'interest_rate')
    def onchange_interest_rate_type(self):
        if self.interest_type and self.is_apply_interest:
            if self.interest_rate != self.loan_type_id.interest_rate:
                self.interest_rate = self.loan_type_id.interest_rate
            if self.interest_type != self.loan_type_id.interest_type:
                self.interest_type = self.loan_type_id.interest_type

    @api.depends('term')
    def get_loan_url(self):
        for loan in self:
            if loan.term:
                base_url = self.env['ir.config_parameter'].get_param('web.base.url', default='http://localhost:8069')
                if base_url:
                    base_url += '/web/login?db=%s&login=%s&key=%s#id=%s&model=%s' % (
                        self._cr.dbname, '', '', loan.id, 'employee.loan')
                    loan.loan_url = base_url
            else:
                loan.loan_url = ''

    @api.depends('distributed_by', 'loan_amount', 'installment_amount')
    def compute_term(self):
        for loan in self:
            if loan.distributed_by == 'inst':
                if loan.loan_amount and loan.installment_amount:
                    loan.term = math.ceil(loan.loan_amount / loan.installment_amount)
                else:
                    loan.term = 0.0
            else:
                pass

    @api.depends('distributed_by', 'term', 'loan_amount')
    def compute_inst_amt(self):
        for loan in self:
            if loan.distributed_by == 'term':
                if loan.loan_amount and loan.term:
                    loan.installment_amount = loan.loan_amount / loan.term
                else:
                    loan.installment_amount = 0.0
            else:
                pass

    @api.constrains('loan_amount', 'term', 'loan_type_id', 'employee_id')
    def _check_loan_amount_term(self):
        for loan in self:
            if self.state != 'draft':
                if loan.loan_amount <= 0:
                    raise ValidationError("Loan Amount must be greater 0.00")
                elif loan.loan_amount > loan.loan_type_id.loan_limit:
                    raise ValidationError("Your can apply only %s amount loan" % loan.loan_type_id.loan_limit)

                if loan.term <= 0:
                    raise ValidationError("Loan Term must be greater than %s" % loan.term)

    @api.onchange('approved_amount')
    def _onchange_loan_type(self):
        if self.loan_type_id:

            self.is_apply_interest = self.loan_type_id.is_apply_interest
            self.is_apply_top_up = self.loan_type_id.is_apply_top_up
            if self.is_apply_interest:
                self.interest_rate = self.loan_type_id.interest_rate
                self.interest_type = self.loan_type_id.interest_type

            self.journal_id = self.loan_type_id.journal_id
            self.debit_loan_account = self.loan_type_id.loan_account
            self.credit_loan_account = self.loan_type_id.loan_payment_account
            self.debit_interest_account = self.loan_type_id.interest_account
            self.debit_process_fee_account = self.loan_type_id.debit_process_fee_account

            if self.is_apply_top_up:
                if self.approved_amount > 0:
                    self.loan_amount = round(self.current_loan + self.approved_amount, 2)
            else:
                self.loan_amount = round(self.approved_amount, 2)

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.user_work_location_id = self.employee_id.user_work_location_id.id

            self.job_id = self.employee_id and self.employee_id.job_id and \
                          self.employee_id.job_id.id or False
            self.department_id = self.employee_id and self.employee_id.department_id and \
                                 self.employee_id.department_id.id or False
            self.manager_id = self.department_id and self.department_id.manager_id and \
                              self.department_id.manager_id.id or self.employee_id.parent_id.id or False

    @api.onchange('employee_id', 'loan_type_id', 'date', 'approved_amount')
    def onchange_employee_id_type_date(self):
        if self.employee_id and self.loan_type_id and self.date:

            balance_data = self.env['hr.employee.pf']._get_pf_emp_balance(self.date, self.employee_id)
            if balance_data:
                self.current_balance = balance_data['salary_pf'] + balance_data['salary_cpf'] + balance_data[
                    'profit_pf'] + balance_data['profit_cpf']

            if self.loan_type_id.pf_policy_id:
                eligible_data = self.env['hr.employee.pf']._get_eligible_emp_loan_amount(self.date, self.employee_id,
                                                                                         self.loan_type_id.pf_policy_id)
                if eligible_data:
                    self.eligible_amount = eligible_data['salary_pf'] + eligible_data['salary_cpf'] + eligible_data[
                        'profit_pf'] + eligible_data['profit_cpf']
                    self.eligible_pf = eligible_data['salary_pf'] + eligible_data['profit_pf']
                    self.eligible_cpf = eligible_data['salary_cpf'] + eligible_data['profit_cpf']
                else:
                    self.eligible_amount = 0
            else:
                self.eligible_amount = self.loan_type_id.loan_limit

            loan_data = self._get_emp_loan_balance(self.date, self.employee_id, self.loan_type_id)
            if loan_data:
                self.current_loan = loan_data['remaining_amount']
            else:
                self.current_loan = 0

            self.applicable_amount = self.eligible_amount - self.current_loan

            self._onchange_loan_type()

            running_loan = self.env['employee.loan'].sudo().search(
                [('employee_id', '=', self.employee_id.id), ('loan_type_id', '=', self.loan_type_id.id),
                 ('state', '=', 'done')], limit=1)
            if running_loan:
                self.installment_amount_previous = running_loan[0].installment_amount

    @api.onchange('requested_amount')
    def onchange_requested_amount(self):
        if self.requested_amount:
            self.loan_amount = self.requested_amount
            self.approved_amount = self.requested_amount

    def action_send_request(self):
        self._check_duplicate_loan_type()

        if not self.manager_id:
            raise ValidationError(_('Please Select Department manager'))

        if self.requested_amount <= 0:
            raise ValidationError(_('Requested amount can not be Zero or Negative!'))

        if self.requested_amount > self.applicable_amount:
            raise ValidationError(_('Requested amount can not be greater than Applicable amount!'))

        # Top-up validation checking
        if self.is_apply_top_up:
            running_loan = self.env['employee.loan'].sudo().search(
                [('employee_id', '=', self.employee_id.id), ('loan_type_id', '=', self.loan_type_id.id),
                 ('state', '=', 'done')], limit=1)
            if running_loan:
                chk_paid_percent = self.loan_type_id.top_up_paid_chk_amt
                chk_paid_count_month = self.loan_type_id.top_up_paid_chk_month

                paid_count = running_loan[0].paid_count
                paid_amount = running_loan[0].paid_amount
                loan_amount = running_loan[0].loan_amount

                paid_percent = round((paid_amount / loan_amount) * 100, 2)
                if not (paid_percent >= chk_paid_percent or paid_count >= chk_paid_count_month):
                    raise ValidationError(
                        _("Running loan must paid `{0}%` or Number of Paid Installment `{1}`!".format(chk_paid_percent,
                                                                                                      chk_paid_count_month)))

        if not self.installment_lines:
            self.compute_installment()

        self.requested_term = self.term
        self.requested_installment_amount = self.installment_amount
        self.state = 'request'

        return True

    def get_hr_manager_email(self):
        group_id = self.env['ir.model.data']._xmlid_lookup('hr.group_hr_manager')[1]
        group_ids = self.env['res.groups'].browse(group_id)
        email = ''
        if group_ids:
            employee_ids = self.env['hr.employee'].search([('user_id', 'in', group_ids.users.ids)])
            for emp in employee_ids:
                if email:
                    email = email + ',' + str(emp.work_email)
                else:
                    email = emp.work_email
        return email

    def dep_manager_approval_loan(self):
        self._check_duplicate_loan_type()

        if self.approved_amount <= 0:
            raise ValidationError(_('Approved amount can not be Zero or Negative!'))

        if self.approved_amount > self.requested_amount:
            raise ValidationError(_('Approved amount can not be greater than Requested amount!'))

        if self.is_apply_top_up:
            self.loan_amount = round(self.current_loan + self.approved_amount, 2)
        else:
            self.loan_amount = round(self.approved_amount, 2)

        self.compute_installment()

        self.state = 'dep_approval'

        return True

    def hr_manager_approval_loan(self):
        self._check_duplicate_loan_type()

        self.state = 'hr_approval'
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        self.hr_manager_id = employee_id and employee_id.id or False

        return True

    def acc_manager_approval_loan(self):
        self._check_duplicate_loan_type()

        self.compute_installment()

        self.state = 'acc_approval'
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        self.acc_manager_id = employee_id and employee_id.id or False

        return True

    def trusty_manager_approval_loan(self):
        self._check_duplicate_loan_type()

        self.state = 'trusty_approval'
        self.approve_date = fields.Date.today()
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        self.trusty_manager_id = employee_id and employee_id.id or False

        return True

    def action_close_loan(self):
        self.state = 'close'
        return True

    def cancel_loan(self):
        self.state = 'cancel'

    def set_to_draft(self):
        self.state = 'draft'
        self.is_close = False
        self.hr_manager_id = False

    def paid_loan(self):
        self._check_duplicate_loan_type()

        if not self.employee_id.address_home_id:
            raise ValidationError(_('Employee Private Address is not selected in Employee Form !!!'))
        else:
            partner_id = self.employee_id.address_home_id.id

        if not self.journal_id:
            raise ValidationError(_('Required Journal !!!'))
        if not self.debit_loan_account:
            raise ValidationError(_('Required Debit account !!!'))
        if not self.credit_loan_account:
            raise ValidationError(_('Required Credit account !!!'))
        if self.process_fee_amount < 0:
            raise ValidationError(_('Process fee can not be negative !!!'))
        if self.loan_amount <= 0:
            raise ValidationError(_('Required Loan amount!!!'))
        if self.process_fee_amount > 0:
            if not self.debit_process_fee_account:
                raise ValidationError(_('Required Process Fee Credit account !!!'))

        if self.is_apply_top_up:
            self.action_loan_top_up_settlement()

        self.env.cr.execute(
            (
                'SELECT loan_no FROM employee_loan WHERE employee_id = %s ORDER BY loan_no DESC LIMIT 1') % self.employee_id.id
        )
        loan_no = self.env.cr.fetchone()[0]
        if loan_no:
            self.loan_no = loan_no + 1
        else:
            self.loan_no = 1

        if self.loan_type_id.journal_id and self.loan_type_id.journal_id.is_pf_display:
            fs_dept = 'pf'
        else:
            fs_dept = 'accounts'

        vals = {
            'date': self.disburse_date,
            'ref': self.name,
            'journal_id': self.loan_type_id.journal_id and self.loan_type_id.journal_id.id,
            'company_id': self.env.user.company_id.id,
            'partner_id': partner_id,
            'location_id': self.user_work_location_id and self.user_work_location_id.id,
            'fs_dept': fs_dept,
        }
        acc_move_id = self.env['account.move'].create(vals)
        lst = []
        #  credit part
        process_fee_amount = self.process_fee_amount
        bank_cr_amount = self.approved_amount - process_fee_amount

        notes = self.name + ': ' + self.disbursement_notes

        lst.append((0, 0, {
            'account_id': self.loan_type_id and self.loan_type_id.loan_account.id,
            'partner_id': self.employee_id.address_home_id and self.employee_id.address_home_id.id or False,
            'name': notes,
            'debit': self.approved_amount,
        }))
        lst.append((0, 0, {
            'account_id': self.credit_loan_account and self.credit_loan_account.id,
            'partner_id': False,
            'name': notes,
            'credit': bank_cr_amount,
        }))
        if process_fee_amount > 0:
            lst.append((0, 0, {
                'account_id': self.loan_type_id and self.loan_type_id.debit_process_fee_account.id,
                'partner_id': False,
                'name': notes,
                'credit': process_fee_amount,
            }))

        acc_move_id.line_ids = lst
        if acc_move_id:
            self.move_id = acc_move_id.id
            acc_move_id.action_post()

        self.state = 'paid'

        self.action_done_loan()

    def view_journal_entry(self):
        if self.move_id:
            return {
                'view_mode': 'form',
                'res_id': self.move_id.id,
                'res_model': 'account.move',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': {'default_type': 'entry'}
            }

    def action_done_loan(self):
        self._check_duplicate_loan_type()

        self.state = 'done'

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get('name', '/') == '/':
                val['name'] = self.env['ir.sequence'].next_by_code(
                    'employee.loan') or '/'
        return super(EmployeeLoan, self).create(vals)

    def copy(self, default=None):
        if default is None:
            default = {}
        default['name'] = '/'
        return super(EmployeeLoan, self).copy(default=default)

    def unlink(self):
        for loan in self:
            if loan.state != 'draft':
                raise ValidationError(_('Loan delete in draft state only !!!'))
        return super(EmployeeLoan, self).unlink()

    def action_view_loan_installment(self):
        action = self.env.ref('dev_hr_loan.action_installment_line').read()[0]

        installment = self.mapped('installment_lines')
        if len(installment) > 1:
            action['domain'] = [('id', 'in', installment.ids)]
        elif installment:
            action['views'] = [(self.env.ref('dev_hr_loan.view_loan_emi_form').id, 'form')]
            action['res_id'] = installment.id
        return action

    def _get_emp_loan_balance(self, date, emp, loan_type_id):
        loan_rows = self.env['employee.loan'].sudo().search(
            [('employee_id', '=', emp.id), ('loan_type_id', '=', loan_type_id.id), ('date', '<=', date),
             ('state', '=', 'done'), ('is_close', '=', False)])
        loan_amount = 0
        paid_amount = 0
        remaining_amount = 0
        for rec in loan_rows:
            loan_amount += rec.loan_amount
            paid_amount += rec.paid_amount
            remaining_amount += rec.remaing_amount

        dict_data = {
            'loan_amount': loan_amount,
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount
        }
        return dict_data

    def _get_emp_all_loan_balance(self, date, emp):
        loan_rows = self.env['employee.loan'].sudo().search(
            [('employee_id', '=', emp.id), ('date', '<=', date), ('state', '=', 'done'), ('is_close', '=', False)])
        loan_amount = 0
        paid_amount = 0
        remaining_amount = 0
        for rec in loan_rows:
            loan_amount += rec.loan_amount
            paid_amount += rec.paid_amount
            remaining_amount += rec.remaing_amount

        dict_data = {
            'loan_amount': loan_amount,
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount
        }
        return dict_data

    def _get_emp_pf_loan_balance(self, date, emp):
        loan_rows = self.env['employee.loan'].sudo().search(
            [('employee_id', '=', emp.id), ('type_id_type', '=', 'pf_loan'), ('date', '<=', date),
             ('state', '=', 'done'), ('is_close', '=', False)])
        loan_amount = 0
        paid_amount = 0
        remaining_amount = 0
        for rec in loan_rows:
            loan_amount += rec.loan_amount
            paid_amount += rec.paid_amount
            remaining_amount += rec.remaing_amount

        dict_data = {
            'loan_amount': loan_amount,
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount
        }
        return dict_data

    def _get_emp_general_loan_balance(self, date, emp):
        loan_rows = self.env['employee.loan'].sudo().search(
            [('employee_id', '=', emp.id), ('type_id_type', '=', 'general'), ('date', '<=', date),
             ('state', '=', 'done'), ('is_close', '=', False)])
        loan_amount = 0
        paid_amount = 0
        remaining_amount = 0
        for rec in loan_rows:
            loan_amount += rec.loan_amount
            paid_amount += rec.paid_amount
            remaining_amount += rec.remaing_amount

        dict_data = {
            'loan_amount': loan_amount,
            'paid_amount': paid_amount,
            'remaining_amount': remaining_amount
        }
        return dict_data

    def _check_duplicate_loan_type(self):
        loan_obj = self.env['employee.loan'].sudo().search(
            [('employee_id', '=', self.employee_id.id), ('loan_type_id', '=', self.loan_type_id.id),
             ('state', 'in', ('request', 'dep_approval', 'hr_approval', 'acc_approval', 'paid'))])
        if len(loan_obj) > 1:
            raise ValidationError("Same type of loan '%s' already under processing!" % self.loan_type_id.name)

        return True

    def action_loan_top_up_settlement(self):
        loan_rows = self.env['employee.loan'].sudo().search(
            [('employee_id', '=', self.employee_id.id), ('loan_type_id', '=', self.loan_type_id.id),
             ('date', '<=', self.date), ('state', '=', 'done')])
        for loan in loan_rows:
            remaining_amt = loan.remaing_amount
            if remaining_amt > 0:

                for line in loan.installment_lines.filtered(lambda x: x.is_paid is False):
                    line.is_paid = True
                    line.is_early_settlement = True
                    line.paid_date = fields.Date.today()
                    line.move_id = None

            loan.get_paid_amount()

        return True

    def action_chk_paid_remaining(self):
        loan_rows = self.env['employee.loan'].sudo().search([('state', '=', 'done')])
        for rec in loan_rows:
            rec.get_paid_amount()

    def action_loan_application_print(self):
        if self:
            loan_obj = self.env['employee.loan']
            loan_data = loan_obj._get_emp_pf_loan_balance(self.date, self.employee_id)
            current_loan = 0
            if loan_data:
                current_loan = loan_data['remaining_amount']

            loan_type = ''
            if self.type_id_type == 'pf_loan':
                loan_type = 'PF'
            elif self.type_id_type == 'general':
                loan_type = 'General'

            data = {
                'id': self.id,
                'model': 'employee.loan',
                'form': self.read()[0],
                'loan_outstanding': current_loan,
                'loan_type': loan_type
            }
            return self.env.ref('dev_hr_loan.report_loan_application_tmpl').with_context(landscape=False).report_action(
                self, data=data)
