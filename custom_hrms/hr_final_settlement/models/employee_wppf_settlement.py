# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from num2words import num2words
from itertools import groupby


class EmployeeWPPFSettlement(models.Model):
    _name = 'employee.wppf.settlement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee WPPF Settlement"
    _rec_name = "employee_id"
    _order = "id desc"

    name = fields.Char(string='Doc Ref.', copy=False, tracking=True)
    date_requested = fields.Datetime(string="Submission Date", default=fields.Datetime.now())

    pf_profile_id = fields.Many2one('wppf.profile', string='WPPF Profile', domain="[('is_active','=',True)]")
    pf_board_id = fields.Many2one(comodel_name="pf.provident.board", string="WPPF Board", related="pf_profile_id.pf_board_id")

    employee_id = fields.Many2one('hr.employee', string='Employee')
    company_id = fields.Many2one('res.company', string='Company')
    department_id = fields.Many2one('hr.department', string="Department")
    old_empid = fields.Char(string="Employee ID")
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    job_position = fields.Many2one('hr.job', string="Designation")
    initial_employment_date = fields.Date(string='Date of Joining')

    length_of_service = fields.Char(string='Length of Service')
    membership_period = fields.Char(string="Membership Period", related="pf_profile_id.membership_period")

    separation_type_id = fields.Char(string='Separation Type') #will delete late
    last_day_of_work = fields.Date(string="Last Day of Work", tracking=True)
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
    deduction_value = fields.Integer(string="Deduction(%)")
    date_of_notice = fields.Date(string="Date of Notice", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Submitted'),
        ('hr', 'HR Approved'),
        ('account', 'Accounts Approved'),
        ('admin', 'Trusty Approved'),
        ('done', 'Payment'),
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
    done_by_id = fields.Many2one('hr.employee', string='Payment By')


    pf_policy_id = fields.Many2one('wppf.policy', string='Settlement Policy')

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
    total_contribution = fields.Float('Total Contribution', digits=(16, 2), default=0.0)
    total_eligible = fields.Float('Total Eligible', digits=(16, 2), default=0.0)
    reserve_amount = fields.Float('Reserve Amount', digits=(16, 2), default=0.0)

    total_amount = fields.Float('Total Amount', digits=(16, 2), default=0.0)

    #  accounts
    journal_id_settlement = fields.Many2one('account.journal', string='Settlement Journal')
    payable_acc_id = fields.Many2one('account.account', 'Payable Account (DR)')
    reserve_acc_id = fields.Many2one('account.account', 'Reserve Account (CR)')
    loan_acc_id = fields.Many2one('account.account', 'Loan Receivable Account (CR)')
    other_acc_id = fields.Many2one('account.account', 'Other Account (CR)')
    settlement_move_id = fields.Many2one('account.move', 'Journal Entries Ref.')
    date_settlement = fields.Date(string='Settlement Date', readonly=True, tracking=True)

    journal_id_payment = fields.Many2one('account.journal', string='Settlement Payment Journal')
    payment_acc_id = fields.Many2one('account.account', 'Payment Account (CR)')
    payment_move_id = fields.Many2one('account.move', 'Journal Entries Ref.')
    date_payment = fields.Date(string='Payment Date', readonly=True, tracking=True)

    _sql_constraints = [
        ('unique_employee_name', 'unique (name)', 'Name should not be same!')]

    @api.onchange('pf_profile_id')
    def _onchange_pf_profile_id(self):
        if self.pf_profile_id:
            self.employee_id = self.pf_profile_id.employee_id or None
            self.length_of_service = self.pf_profile_id.service_period

    @api.onchange('employee_id', 'pf_policy_id', 'other_deduction')
    def _onchange_employee_id(self):
        pf_obj = self.env['hr.employee.wppf']
        loan_obj = self.env['employee.loan']
        resig_obj = self.env['hr.resignation']
        if self.pf_policy_id:
            self.journal_id_settlement = self.pf_policy_id.journal_id_settlement or None
            self.payable_acc_id = self.pf_policy_id.payable_acc_id or None
            self.reserve_acc_id = self.pf_policy_id.reserve_acc_id or None
            self.loan_acc_id = self.pf_policy_id.loan_acc_id or None
            self.other_acc_id = self.pf_policy_id.other_acc_id or None

            self.journal_id_payment = self.pf_policy_id.journal_id_payment or None
            self.payment_acc_id = self.pf_policy_id.payment_acc_id or None

        date = fields.Date.today()
        for rec in self:
            if rec.employee_id:
                rec.user_work_location_id = rec.employee_id.user_work_location_id.id
                rec.company_id = rec.employee_id.company_id.id
                rec.department_id = rec.employee_id.department_id.id
                rec.old_empid = rec.employee_id.id_card_no
                rec.job_position = rec.employee_id.job_id.id
                rec.initial_employment_date = rec.employee_id.initial_employment_date

                rec.gross_salary = rec.employee_id.contract_id.gross_salary
                rec.emp_id_email = rec.employee_id.work_email
                rec.emp_id_passport = rec.employee_id.passport_id
                rec.emp_id_nid = rec.employee_id.nid
                rec.emp_id_mobile = rec.employee_id.contact_no
                rec.outgoing_emp_id = rec.employee_id.id


                balance_data = pf_obj._get_wppf_emp_balance(date, self.employee_id)
                if balance_data:
                    self.contribution_pf = balance_data['wppf_pf']
                    self.contribution_cpf = balance_data['wppf_cpf']

                    self.profit_pf = balance_data['profit_pf']
                    self.profit_cpf = balance_data['profit_cpf']

                    self.contribution_eligible_pf = self.contribution_pf
                    self.contribution_eligible_cpf = self.contribution_cpf
                    self.profit_eligible_pf = self.profit_pf
                    self.profit_eligible_cpf = self.profit_cpf

                self.total_contribution = (self.contribution_pf + self.contribution_cpf + self.profit_pf + self.profit_cpf)
                self.total_eligible = (self.contribution_eligible_pf + self.contribution_eligible_cpf + self.profit_eligible_pf + self.profit_eligible_cpf)
                self.reserve_amount = self.total_contribution - self.total_eligible
                self.total_amount = (self.contribution_eligible_pf + self.contribution_eligible_cpf + self.profit_eligible_pf + self.profit_eligible_cpf) - self.current_loan - self.other_deduction

                resig_row = resig_obj.sudo().search([('employee_id', '=', self.employee_id.id), ('state', '=', 'approved')], order='resign_confirm_date desc', limit = 1)
                if resig_row:
                    self.last_day_of_work = resig_row[0].expected_revealing_date
                    self.notice_period = 'yes'
                    self.notice_period_days = resig_row[0].notice_period
                    self.deduction_value = resig_row[0].deduction
                    self.ref_id = resig_row[0].id

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
        return super(EmployeeWPPFSettlement, self).unlink()

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def action_cancel(self):
        for record in self:
            if record.state == 'done':
                raise UserError('Payment record can not be cancelled!')
            else:
                record.sudo().write({'state': 'cancel'})

    def action_draft(self):
        for record in self:
            record.sudo().write({'state': 'draft'})
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
                record.reserve_acc_id = record.pf_policy_id.reserve_acc_id or None
                record.loan_acc_id = record.pf_policy_id.loan_acc_id or None
                record.other_acc_id = record.pf_policy_id.other_acc_id or None

                record.journal_id_payment = record.pf_policy_id.journal_id_payment or None
                record.payment_acc_id = record.pf_policy_id.payment_acc_id or None

            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            user_emp_id = employee_id and employee_id.id or False

            record.sudo().write({'state': 'admin', 'admin_approver_id': user_emp_id, 'admin_approved_date': fields.Datetime.now()})

    def action_accounts_approve(self):
        for record in self:


            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            user_emp_id = employee_id and employee_id.id or False

            record.sudo().write({'state': 'account', 'acc_approver_id': user_emp_id, 'acc_approved_date': fields.Datetime.now()})

    def action_print(self):
        data = {
            'model': "employee.wppf.settlement",
            'form': self.read()[0],
            'id': self.id,
        }
        return self.env.ref('hr_final_settlement.wppf_final_settlement_report_id').with_context(
            landscape=False).report_action(self, data=data)

    def action_done(self):
        # --------- settlement journal
        pf_obj = self.env['hr.employee.wppf']
        for record in self:



            date = record.date_requested


            #  WPPF close
            pf_obj._close_emp_wppf(date, record.employee_id)



            # payment journal

            if record.journal_id_payment and record.journal_id_payment.is_pf_display:
                fs_dept = 'pf'
            else:
                fs_dept = 'accounts'
            vals2 = {
                'date': fields.Date.today(),
                'journal_id': record.journal_id_payment and record.journal_id_payment.id,
                'company_id': record.env.user.company_id.id,
                'partner_id': False,
                'location_id': False,
                'ref': 'Ref: WPPF Settlement Payment ' + str(record.name),
                'fs_dept': fs_dept
            }
            acc_move_id2 = self.env['account.move'].create(vals2)

            lst = []
            payable_acc_id = record.payable_acc_id.id or False
            payment_acc_id = record.payment_acc_id.id or False
            ref = 'WPPF settlement payment: ' + str(record.name)

            total_amount = record.total_amount

            partner_id = record.employee_id.address_home_id.id or False

            #  debit journal entry
            lst.append((0, 0, {
                'account_id': payable_acc_id,
                'partner_id': partner_id,
                'name': ref,
                'debit': total_amount if total_amount >= 0 else 0,
                'credit': total_amount * (-1) if total_amount < 0 else 0
            }))

            #  Credit journal entry
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

            record.sudo().write({'state': 'done', 'date_payment': fields.Date.today(),
                                 'payment_move_id': acc_move_id2.id or False, 'done_by_id': user_emp_id})

            record.employee_id.wppf_settlement_status = True
            record.pf_profile_id.is_active = False
            record.pf_profile_id.closed_date = fields.Date.today()

    def _compute_employee_pf(self):
        for records in self:
            records.pf_count = self.env['hr.employee.wppf'].search_count([('employee_id', '=', records.employee_id.id)])

    pf_count = fields.Integer(string="Loan Count", compute='_compute_employee_pf')

    def act_current_employee_wppf(self):
        return {
            'name': "WPPF Details",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.wppf',
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
            'domain': [('employee_id', '=', self.employee_id.id)],
        }


class EmployeeSattlementReport(models.AbstractModel):
    _name = 'report.hr_final_settlement.final_wppf_settlement_sheet_view'
    _description = 'Employee Settlement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        pf_settle_object = self.env['employee.wppf.settlement'].browse(docids)

        employee_id = pf_settle_object.employee_id

        data_sql = """
                    select hep.year,hep.month,hep.pf_amount,he.id, he.name,hc.gross_salary from hr_employee_wppf hep 
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

        pf_obj = self.env['hr.employee.wppf']

        emp_pf_obj = pf_obj.search([('employee_id', '=', employee_id.id)], order='year asc', limit=1)

        tpf_membership = ''

        if emp_pf_obj:
            tpf_membership = "{0}-{1}".format(dict(emp_pf_obj._fields['month'].selection).get(emp_pf_obj.month), emp_pf_obj.year)

        return {
            'doc_ids': docids,
            'doc_model': 'employee.wppf.settlement',
            'docs': pf_settle_object,
            'data': data,
            'csr': final_data_list,
            'tpf_membership': tpf_membership,
            'pf_obj': pf_obj,
        }



