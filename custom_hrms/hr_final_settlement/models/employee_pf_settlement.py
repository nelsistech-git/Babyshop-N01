# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from num2words import num2words
from itertools import groupby
from dateutil.relativedelta import relativedelta

class EmployeePFSettlement(models.Model):
    _name = 'employee.pf.settlement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee PF Settlement"
    _rec_name = "employee_id"
    _order = "id desc"

    name = fields.Char(string='Doc Ref.', copy=False, tracking=True)
    date_requested = fields.Datetime(string="Submission Date", default=fields.Datetime.now())

    pf_profile_id = fields.Many2one('pf.profile', string='PF Profile', domain="[('is_active','=',True)]")
    pf_board_id = fields.Many2one(comodel_name="pf.provident.board", string="Board", related="pf_profile_id.pf_board_id")
    membership_date = fields.Date(string="Membership Date", related="pf_profile_id.membership_date")

    employee_id = fields.Many2one('hr.employee', string='Employee')
    partner_id = fields.Many2one('res.partner', string='Private Address', related='employee_id.address_home_id')

    company_id = fields.Many2one('res.company', string='Company')
    department_id = fields.Many2one('hr.department', string="Department")
    old_empid = fields.Char(string="Employee ID")
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    job_position = fields.Many2one('hr.job', string="Designation")
    initial_employment_date = fields.Date(string='Date of Joining')

    length_of_service = fields.Char(string='Length of Service')
    membership_period = fields.Char(string="Membership Period")

    separation_type_id = fields.Char(string='Separation Type') #will delete late
    last_day_of_work = fields.Date(string="Last Working Day", tracking=True)
    ref_id = fields.Many2one('hr.resignation', string='Separation Reference')
    resignation_type_id = fields.Many2one('hr.separation.type.settings', string='Separation Type', related='ref_id.resignation_type_id')
    date_of_separation = fields.Date(string="Date of Separation", tracking=True, related='ref_id.resign_confirm_date')


    notice_served = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Notice Served", default='yes', tracking=True, copy=False)
    notice_period = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'N/A'),
    ], string="Notice Period(Given)", default='no', tracking=True, copy=False)
    notice_period_days = fields.Char(string="Notice Period Days")
    deduction_value = fields.Integer(string="Deduction")
    date_of_notice = fields.Date(string="Date of Notice", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Submitted'),
        ('hr', 'HR Approved'),
        ('account', 'Accounts Approved'),
        ('admin', 'Trusty Approved'),
        ('settlement', 'Settlement Done'),
        ('done', 'Payment Done'),
        ('cancel', 'Cancelled'),
    ], string="State", default='draft', tracking=True, copy=False)
    submitted_by_id = fields.Many2one('hr.employee', string='Submitted By')
    submitted_date = fields.Datetime(string='Submitted Date')
    hr_approver_id = fields.Many2one('hr.employee', string='HR Approver')
    hr_approved_date = fields.Datetime(string='HR Approved Date')
    acc_approver_id = fields.Many2one('hr.employee', string='Accounts Approver')
    acc_approved_date = fields.Datetime(string='Accounts Approved Date')
    admin_approver_id = fields.Many2one('hr.employee', string='Trusty Approver')
    admin_approved_date = fields.Datetime(string='Trusty Approved Date')
    settlement_by_id = fields.Many2one('hr.employee', string='Settlement By')
    done_by_id = fields.Many2one('hr.employee', string='Payment By')


    pf_policy_id = fields.Many2one('pf.configuration', string='Settlement Policy', domain="[('type','in',['settlement', 'loan_settlement'])]")

    contribution_pf = fields.Float('Contribution', digits=(16, 2), default=0.0)
    contribution_cpf = fields.Float('Contribution', digits=(16, 2), default=0.0)

    profit_pf = fields.Float('Profit', digits=(16, 2), default=0.0)
    profit_cpf = fields.Float('Profit', digits=(16, 2), default=0.0)

    contribution_eligible_pf = fields.Float('Eligible Contribution', digits=(16, 2), default=0.0)
    contribution_eligible_cpf = fields.Float('Eligible Contribution', digits=(16, 2), default=0.0)

    profit_eligible_pf = fields.Float('Eligible Profit', digits=(16, 2), default=0.0)
    profit_eligible_cpf = fields.Float('Eligible Profit', digits=(16, 2), default=0.0)

    current_loan = fields.Float('Remaining Loan', digits=(16, 2), default=0.0)
    other_deduction = fields.Float('Other Deduction', digits=(16, 2), default=0.0)
    other_deduct_note = fields.Char('Other Deduction Note', default='')
    total_contribution = fields.Float('Total Contribution', digits=(16, 2), default=0.0)
    total_eligible = fields.Float('Total Eligible', digits=(16, 2), default=0.0)
    reserve_amount = fields.Float('Reserve Amount', digits=(16, 2), default=0.0)

    total_amount = fields.Float('Total Amount', digits=(16, 2), default=0.0)

    #  accounts
    journal_id_settlement = fields.Many2one('account.journal', string='Settlement Journal')

    payable_acc_id = fields.Many2one('account.account', 'Payable Account (DR)')
    loan_acc_id = fields.Many2one('account.account', 'Loan Receivable Account (CR)')
    reserve_acc_id = fields.Many2one('account.account', 'Reserve Account (CR)')
    other_acc_id = fields.Many2one('account.account', 'Other Account (CR)')
    payable_emp_acc_id = fields.Many2one('account.account', 'Employee Payable Account (CR)')
    settlement_move_id = fields.Many2one('account.move', 'Journal Entries Ref.')
    date_settlement = fields.Date(string='Settlement Date')

    journal_id_payment = fields.Many2one('account.journal', string='Settlement Payment Journal')
    payment_acc_id = fields.Many2one('account.account', 'Payment Account (CR)')
    payment_move_id = fields.Many2one('account.move', 'Journal Entries Ref.')
    date_payment = fields.Date(string='Payment Date')

    _sql_constraints = [
        ('unique_employee_name', 'unique (name)', 'Name should not be same!')]

    @staticmethod
    def get_service_length(date_from, date_to):
        service_length_str = '0'
        if date_from and date_to:
            date_diff = relativedelta(date_from, date_to)
            service_length1 = "{y} years, {m} months, {d} days".format(y=date_diff.years, m=date_diff.months,
                                                                       d=date_diff.days)
            service_length2 = date_diff.months + (12 * date_diff.years)  # months
            service_length_str = str(service_length1) + ' [' + str(service_length2) + ' months]'

        return str(service_length_str)

    @api.onchange('pf_profile_id', 'last_day_of_work')
    def _onchange_pf_profile_id(self):
        if self.pf_profile_id and self.last_day_of_work:
            self.name = 'PF Settlement of ' + self.pf_profile_id.employee_id.name or None
            self.employee_id = self.pf_profile_id.employee_id or None
            self.length_of_service = self.get_service_length(self.last_day_of_work, self.initial_employment_date)
            self.membership_period = self.get_service_length(self.last_day_of_work, self.membership_date)


    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        resig_obj = self.env['hr.resignation']

        resig_row = resig_obj.sudo().search(
            [('employee_id', '=', self.employee_id.id), ('state', '=', 'approved')],
            order='resign_confirm_date desc', limit=1)
        if resig_row:
            self.last_day_of_work = resig_row[0].expected_revealing_date
            self.notice_period = 'yes'
            self.notice_period_days = resig_row[0].notice_period
            self.deduction_value = resig_row[0].deduction
            self.ref_id = resig_row[0].id
        else:
            self.last_day_of_work = fields.Date.today()

    @api.onchange('employee_id', 'pf_policy_id', 'other_deduction', 'last_day_of_work')
    def _onchange_employee_id_policy_date(self):
        pf_obj = self.env['hr.employee.pf']
        loan_obj = self.env['employee.loan']
        resig_obj = self.env['hr.resignation']
        if self.pf_policy_id:
            self.journal_id_settlement = self.pf_policy_id.journal_id_settlement or None
            self.payable_acc_id = self.pf_policy_id.payable_acc_id or None
            self.payable_emp_acc_id = self.pf_policy_id.payable_emp_acc_id or None
            self.reserve_acc_id = self.pf_policy_id.reserve_acc_id or None
            self.loan_acc_id = self.pf_policy_id.loan_acc_id or None
            self.other_acc_id = self.pf_policy_id.other_acc_id or None

            self.journal_id_payment = self.pf_policy_id.journal_id_payment or None
            self.payment_acc_id = self.pf_policy_id.payment_acc_id or None


        for rec in self:
            date = rec.last_day_of_work

            if rec.employee_id and date:
                rec.user_work_location_id = rec.employee_id.user_work_location_id.id
                rec.company_id = rec.employee_id.company_id.id
                rec.department_id = rec.employee_id.department_id.id
                rec.old_empid = rec.employee_id.id_card_no
                rec.job_position = rec.employee_id.job_id.id
                rec.initial_employment_date = rec.employee_id.initial_employment_date

                # rec.gross_salary = rec.employee_id.contract_id.gross_salary
                # rec.emp_id_email = rec.employee_id.work_email
                # rec.emp_id_passport = rec.employee_id.passport_id
                # rec.emp_id_nid = rec.employee_id.nid
                # rec.emp_id_mobile = rec.employee_id.contact_no
                # rec.outgoing_emp_id = rec.employee_id.id


                balance_data = pf_obj._get_pf_emp_balance(date, rec.employee_id)
                if balance_data:
                    rec.contribution_pf = balance_data['salary_pf']
                    rec.contribution_cpf = balance_data['salary_cpf']

                    rec.profit_pf = balance_data['profit_pf']
                    rec.profit_cpf = balance_data['profit_cpf']

                if rec.pf_policy_id:
                    eligible_data = pf_obj._get_eligible_emp_pf_settlement_amount(date,rec.employee_id, rec.pf_policy_id)
                    if eligible_data:
                        rec.contribution_eligible_pf = eligible_data['salary_pf']
                        rec.contribution_eligible_cpf = eligible_data['salary_cpf']

                        rec.profit_eligible_pf = eligible_data['profit_pf']
                        rec.profit_eligible_cpf = eligible_data['profit_cpf']

                    else:
                        rec.contribution_eligible_pf = 0
                        rec.contribution_eligible_cpf = 0

                        rec.profit_eligible_pf = 0
                        rec.profit_eligible_cpf = 0
                else:
                    raise UserError('PF settlement policy not available!')

                loan_data = loan_obj._get_emp_pf_loan_balance(date, rec.employee_id)
                if loan_data:
                    rec.current_loan = round(loan_data['remaining_amount'], 0)
                else:
                    rec.current_loan = 0

                rec.total_contribution = round((rec.contribution_pf + rec.contribution_cpf + rec.profit_pf + rec.profit_cpf), 0)
                rec.total_eligible = round((rec.contribution_eligible_pf + rec.contribution_eligible_cpf + rec.profit_eligible_pf + rec.profit_eligible_cpf), 0)
                rec.reserve_amount = round(rec.total_contribution - rec.total_eligible, 0)
                rec.total_amount = round((rec.total_eligible) - rec.current_loan - rec.other_deduction, 0)


    def _compute_amount_in_word(self,grand_total):
        for rec in self:
            amount_in_words = "".join(num2words(grand_total, lang='en_IN').title().replace("-", " ")).replace(",", "") + " Taka Only"
            return amount_in_words

    def _convertnumber_in_month(self,month):
        month = dict(self._fields['month'].selection).get(month)
        return month

    def unlink(self):
        for loan in self:
            if loan.state not in ('draft'):
                raise UserError(
                    'You cannot delete a settlement which is confirmed')
        return super(EmployeePFSettlement, self).unlink()

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def action_cancel(self):
        for records in self:
            if self.state == 'done':
                raise UserError('Payment record can not be cancelled!')

            else:
                records.sudo().write({'state': 'cancel'})

    def action_draft(self):
        for record in self:
            contrib_rows = self.env['hr.employee.pf'].search([('employee_id', '=', record.employee_id.id),('state', '=', 'close')])
            for rec in contrib_rows:
                rec.state = 'done'
            record.state='draft'
            record.pf_profile_id.is_active = True

    def action_submit(self):
        for records in self:
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            user_emp_id = employee_id and employee_id.id or False
            records.sudo().write({'state': 'confirm', 'submitted_by_id': user_emp_id, 'submitted_date': fields.Datetime.now()})

    def action_hr_approve(self):
        for record in self:
            if record.pf_policy_id:
                record.journal_id_settlement = record.pf_policy_id.journal_id_settlement or None
                record.payable_acc_id = record.pf_policy_id.payable_acc_id or None
                record.payable_emp_acc_id = record.pf_policy_id.payable_emp_acc_id or None
                record.reserve_acc_id = record.pf_policy_id.reserve_acc_id or None
                record.loan_acc_id = record.pf_policy_id.loan_acc_id or None
                record.other_acc_id = record.pf_policy_id.other_acc_id or None

                record.journal_id_payment = record.pf_policy_id.journal_id_payment or None
                record.payment_acc_id = record.pf_policy_id.payment_acc_id or None

            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            user_emp_id = employee_id and employee_id.id or False

            record.sudo().write({'state': 'hr', 'hr_approver_id': user_emp_id, 'hr_approved_date': fields.Datetime.now()})



    def action_admin_approve(self):
        for record in self:
            if record.pf_policy_id:
                record.journal_id_settlement = record.pf_policy_id.journal_id_settlement or None
                record.payable_acc_id = record.pf_policy_id.payable_acc_id or None
                record.payable_emp_acc_id = record.pf_policy_id.payable_emp_acc_id or None
                record.reserve_acc_id = record.pf_policy_id.reserve_acc_id or None
                record.loan_acc_id = record.pf_policy_id.loan_acc_id or None
                record.other_acc_id = record.pf_policy_id.other_acc_id or None

                record.journal_id_payment = record.pf_policy_id.journal_id_payment or None
                record.payment_acc_id = record.pf_policy_id.payment_acc_id or None

            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            user_emp_id = employee_id and employee_id.id or False

            record.sudo().write({'state': 'admin', 'admin_approver_id': user_emp_id, 'admin_approved_date': fields.Datetime.now()})


    def action_accounts_approve(self):
        #pf_obj = self.env['hr.employee.pf']
        for record in self:


            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            user_emp_id = employee_id and employee_id.id or False

            record.sudo().write({'state': 'account', 'acc_approver_id': user_emp_id, 'acc_approved_date': fields.Datetime.now()})


    def action_print(self):
        data = {
            'model': "employee.pf.settlement",
            'form': self.read()[0],
            'id': self.id,
        }
        return self.env.ref('hr_final_settlement.pf_final_settlement_report_id').with_context(
            landscape=False).report_action(self, data=data)

    def action_settlement_done(self):
        #  settlement journal
        pf_obj = self.env['hr.employee.pf']
        for record in self:
            partner_id = record.employee_id.address_home_id.id or False
            user_work_location_id = record.user_work_location_id.id or False

            if record.journal_id_settlement and record.journal_id_settlement.is_pf_display:
                fs_dept = 'pf'
            else:
                fs_dept = 'accounts'
            vals = {
                'date': record.date_settlement,
                'journal_id': record.journal_id_settlement and record.journal_id_settlement.id,
                'company_id': record.env.user.company_id.id,
                'partner_id': partner_id,
                'location_id': user_work_location_id,
                'ref': 'Ref: PF Settlement ' + str(record.name),
                'fs_dept': fs_dept
            }
            acc_move_id = self.env['account.move'].create(vals)

            lst = []
            payable_acc_id = record.payable_acc_id.id or False
            payable_emp_acc_id = record.payable_emp_acc_id.id or False
            reserve_acc_id = record.reserve_acc_id.id or False
            loan_acc_id = record.loan_acc_id.id or False
            other_acc_id = record.other_acc_id.id or False
            ref = 'PF settlement: ' + str(record.name)

            total_contribution = record.total_contribution
            current_loan = record.current_loan
            reserve_amt = record.reserve_amount
            other_deduction = record.other_deduction
            other_deduct_note = record.other_deduct_note
            payable_emp_amt = record.total_amount

            #  debit journal entry
            lst.append((0, 0, {
                'account_id': payable_acc_id,
                'partner_id': partner_id,
                'name': ref,
                'debit': total_contribution or 0.0,
            }))

            #  Credit journal entry
            if current_loan > 0:
                lst.append((0, 0, {
                    'account_id': loan_acc_id,
                    'partner_id': partner_id,
                    'name': ref,
                    'credit': current_loan or 0.0,
                }))
            if reserve_amt > 0:
                lst.append((0, 0, {
                    'account_id': reserve_acc_id,
                    'partner_id': partner_id,
                    'name': ref,
                    'credit': reserve_amt or 0.0,
                }))

            if other_deduction > 0:
                lst.append((0, 0, {
                    'account_id': other_acc_id,
                    'partner_id': partner_id,
                    'name': ref +'; '+ other_deduct_note,
                    'credit': other_deduction or 0.0,
                }))

            lst.append((0, 0, {
                'account_id': payable_emp_acc_id,
                'partner_id': False,
                'name': ref,
                'credit': payable_emp_amt or 0.0,
            }))

            acc_move_id.line_ids = lst
            acc_move_id.action_post()

            date = record.last_day_of_work
            #  Loan Closed
            loan_rows = self.env['employee.loan'].sudo().search(
                [('employee_id', '=', record.employee_id.id),('type_id_type', '=', 'pf_loan'), ('date', '<=', date), ('state', '=', 'done'),
                 ('is_close', '=', False)])
            for loan_rec in loan_rows:
                line_rows = self.env['installment.line'].sudo().search(
                    [('loan_id', '=', loan_rec.id), ('is_paid', '=', False)])
                for line_rec in line_rows:
                    line_rec.is_paid = True
                    line_rec.is_early_settlement = True
                    line_rec.paid_date = record.date_settlement
                    line_rec.move_id = acc_move_id.id or False

                loan_rec.get_paid_amount()

            #  PF close
            pf_obj._close_emp_pf(date, record.employee_id)

            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            user_emp_id = employee_id and employee_id.id or False

            record.sudo().write({'state': 'settlement', 'settlement_move_id': acc_move_id.id or False, 'settlement_by_id': user_emp_id})

            record.employee_id.pf_settlement_status = True
            record.pf_profile_id.is_active = False
            record.pf_profile_id.closed_date = fields.Date.today()

    def action_done(self):
        #  settlement journal
        pf_obj = self.env['hr.employee.pf']
        for record in self:
            partner_id = record.employee_id.address_home_id.id or False
            user_work_location_id = record.user_work_location_id.id or False

            # payment journal
            if record.journal_id_payment and record.journal_id_payment.is_pf_display:
                fs_dept = 'pf'
            else:
                fs_dept = 'accounts'
            vals2 = {
                'date': record.date_payment,
                'journal_id': record.journal_id_payment and record.journal_id_payment.id,
                'company_id': self.env.user.company_id.id,
                'partner_id': partner_id,
                'location_id': user_work_location_id,
                'ref': 'Ref: Settlement Payment ' + str(record.name),
                'fs_dept': fs_dept
            }
            acc_move_id2 = self.env['account.move'].create(vals2)

            lst = []
            payable_emp_acc_id = record.payable_emp_acc_id.id or False
            payment_acc_id = record.payment_acc_id.id or False
            ref = 'PF settlement payment: ' + str(record.name)

            total_amount = record.total_amount

            #  debit journal entry
            lst.append((0, 0, {
                'account_id': payable_emp_acc_id,
                'partner_id': partner_id,
                'name': ref,
                'debit': total_amount if total_amount >= 0 else 0,
                'credit': total_amount * (-1) if total_amount < 0 else 0
            }))

            # Credit journal entry
            lst.append((0, 0, {
                'account_id': payment_acc_id,
                'partner_id': partner_id,
                'name': ref,
                'credit': total_amount if total_amount >= 0 else 0,
                'debit': total_amount * (-1) if total_amount < 0 else 0
            }))

            acc_move_id2.line_ids = lst
            acc_move_id2.action_post()

            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            user_emp_id = employee_id and employee_id.id or False

            record.sudo().write({'state': 'done', 'payment_move_id': acc_move_id2.id or False, 'done_by_id': user_emp_id})


    def _compute_employee_pf(self):
        for records in self:
            records.pf_count = self.env['hr.employee.pf'].search_count([('employee_id', '=', records.employee_id.id)])

    pf_count = fields.Integer(string="Loan Count", compute='_compute_employee_pf')

    def act_current_employee_pf(self):
        return {
            'name': "PF Details",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.pf',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_id': False,
            'context': False,
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id)],
        }

    def act_current_employee_loan(self):
        tree_view_id = self.env.ref('dev_hr_loan.view_employee_loan_tree').id
        form_view_id = self.env.ref('dev_hr_loan.view_employee_loan_form_request').id
        report_display_views = []
        report_display_views.append((tree_view_id, 'tree'))
        report_display_views.append((form_view_id, 'form'))
        return {
            'name': "Loan Details",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.loan',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': report_display_views,
            'res_id': False,
            'context': False,
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id), ('type_id_type', '=', 'pf_loan')],
        }


class EmployeeSattlementReport(models.AbstractModel):
    _name = 'report.hr_final_settlement.final_pf_settlement_sheet_view'
    _description = 'Employee Settlement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        pf_settle_object = self.env['employee.pf.settlement'].browse(docids)

        employee_id = pf_settle_object.employee_id

        data_sql = """
                    select hep.year,hep.month,hep.pf_amount,he.id, he.name,hc.gross_salary from hr_employee_pf hep 
                    JOIN hr_employee he ON he.id = hep.employee_id
                    left join hr_contract hc on hc.name=he.name
                    where he.id={0}
                    order by hep.month asc
                    """.format(employee_id.id)
        self.env.cr.execute(data_sql)
        data_list = self.env.cr.dictfetchall()

        # define a fuction for key
        def key_func(k):
            return k['year']

        data_list = sorted(data_list, key=key_func)

        final_data_list = []

        for key, value in groupby(data_list, key_func):

            vals = {
                key: list(value)
            }
            final_data_list.append(vals)

        pf_obj = self.env['hr.employee.pf']

        emp_pf_obj = pf_obj.search([('employee_id', '=', employee_id.id)], order='year asc', limit=1)

        tpf_membership = ''

        if emp_pf_obj:
            tpf_membership = "{0}-{1}".format(dict(emp_pf_obj._fields['month'].selection).get(emp_pf_obj.month), emp_pf_obj.year)

        return {
            'doc_ids': docids,
            'doc_model': 'employee.pf.settlement',
            'docs': pf_settle_object,
            'data': data,
            'csr': final_data_list,
            'tpf_membership': tpf_membership,
            'pf_obj': pf_obj,
        }



