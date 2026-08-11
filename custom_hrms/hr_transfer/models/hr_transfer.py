import requests

from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta
from odoo.http import request
import json


_logger = logging.getLogger(__name__)


class EmployeeTransfer(models.Model):
    _name = 'hr.transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Transfer"
    _order = "id desc"

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char(string='Name', copy=False, tracking=True, default=lambda self: _('New'))
    date_requested = fields.Datetime(string="Requested Date", default=fields.Datetime.now)
    employee_id = fields.Many2one('hr.employee', string='Employee Name', store=True)
    company_id = fields.Many2one('res.company', string='Company', store=True)
    old_empid = fields.Char(string="Employee ID", store=True)
    device_user_id = fields.Char(string='Biometric Device ID',
                                 help='The ID Number of the user/employee in the device storage')
    identification_id = fields.Char(string='Master ID')
    id_card_no = fields.Char(string="Employee ID")
    door_card_no = fields.Char(string="Door Card No")
    work_email = fields.Char(string='Work Email')
    contact_no = fields.Char(string="Mobile (Personal)")
    initial_employment_date = fields.Date(string='Date of Joining')

    location_id = fields.Many2one('stock.location', string='Work/Job Location', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True, string="Department")
    job_position = fields.Many2one('hr.job', string="Designation", store=True)

    date_exec = fields.Date(string="Effective Date", default=datetime.now().date(), required=True, readonly=True)
    transfer_company = fields.Selection([
        ('0', 'Same Company'),
        ('1', 'Other Company')
    ], string="Transfer To(Company)", default='0', tracking=True, copy=False)
    manager_id = fields.Many2one('hr.employee', string='Reporting Manager', readonly=True)
    from_emp_contract = fields.Many2one(string='Existing Contract', comodel_name='hr.contract',
                                        required=True, store=True)  # compute='_compute_field_employee_id',
    gross_salary = fields.Float(string='Gross Salary')
    resource_calendar = fields.Many2one('resource.calendar', string='Working Schedule')
    emp_private_address_id = fields.Many2one(related='employee_id.address_home_id', string='Private Address')

    requester_id = fields.Many2one('hr.employee', required=True, string='Requester', default=_default_employee)

    emp_contract = fields.Many2one('hr.contract', string='Employee', store=True)
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('supervisor_existing', 'Supervisor(Existing) Approved'),
        ('hr_approved', 'HR Approved'),
        ('supervisor_new', 'Supervisor(To) Approved'),
        ('md_approved', 'MD Approved'),
        ('accounting_approved', 'Accounting Approved'),
        ('transfer', 'Transferred'),
        ('cancel', 'Cancelled'),
    ], string="State", default='draft', tracking=True, copy=False)

    to_company_id = fields.Many2one('res.company', string='Company')
    to_wh_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                        domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    to_department_id = fields.Many2one('hr.department', string='Department')
    to_position = fields.Many2one('hr.job', string='Designation', required=False)
    to_manager_id = fields.Many2one('hr.employee', string='Reporting Manager')
    to_contract = fields.Many2one(string='Contract', comodel_name='hr.contract', store=True, copy=False)
    other_company_name = fields.Many2one('company.api.settings', string='Company Name')
    other_company_job_location = fields.Char(string='Work/Job Location')
    other_company_department = fields.Char(string='Department')
    other_company_job_position = fields.Char(string='Designation')

    other_company_job_location_id = fields.Many2one('company.api.settings.other.location', string='Work/Job Location')
    other_company_department_id = fields.Many2one('company.api.settings.other.department', string='Department')
    other_company_job_position_id = fields.Many2one('company.api.settings.other.designation', string='Designation')
    other_company_work_schedule_id = fields.Many2one('company.api.settings.other.work_schedule',
                                                     string='Working Schedule')
    other_company_att_policy_id = fields.Many2one('company.api.settings.other.att_policy', string='Attendance Policy')

    other_company_manager = fields.Char(string='Reporting Manager')
    note = fields.Char(string='Note')

    total_residual_loan = fields.Float(string='Loan Amount', default=0)  # not used
    advance_salary = fields.Float(string='Salary Advance', default=0)  # not used
    residual_Salary = fields.Float(string='Salary Payables', default=0)  # not used

    total_amount = fields.Float(string='Total Amount', default=0)
    to_resource_calendar = fields.Many2one('resource.calendar', string='Working Schedule')
    to_att_policy_id = fields.Many2one('hr.attendance.policy', string='Attendance Policy')

    # loan_summary
    def _get_loan_dr_acc(self):
        loan_acc_sett_obj = self.env['hr.account.settings'].search(
            [('type', '=', 'loan'), ('is_transfer_dr', '=', True)])
        loan_dr_acc = loan_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', loan_dr_acc.ids)]

    def _get_loan_cr_acc(self):
        loan_acc_sett_obj = self.env['hr.account.settings'].search(
            [('type', '=', 'loan'), ('is_transfer_cr', '=', True)])
        loan_cr_acc = loan_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', loan_cr_acc.ids)]

    loan_dr_acc = fields.Many2one('account.account', string='Debit Account', domain=_get_loan_dr_acc)
    loan_cr_acc = fields.Many2one('account.account', string='Credit Account', domain=_get_loan_cr_acc)
    loan_balance = fields.Float(string='Balance', default=0)

    # loan_interest_summary
    def _get_loan_inst_dr_acc(self):
        loan_inst_acc_sett_obj = self.env['hr.account.settings'].search(
            [('type', '=', 'loan_interest'), ('is_transfer_dr', '=', True)])
        loan_interest_dr_acc = loan_inst_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', loan_interest_dr_acc.ids)]

    def _get_loan_inst_cr_acc(self):
        loan_inst_acc_sett_obj = self.env['hr.account.settings'].search(
            [('type', '=', 'loan_interest'), ('is_transfer_cr', '=', True)])
        loan_interest_cr_acc = loan_inst_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', loan_interest_cr_acc.ids)]

    loan_interest_dr_acc = fields.Many2one('account.account', string='Debit Account(Interest)', domain=_get_loan_inst_dr_acc)
    loan_interest_cr_acc = fields.Many2one('account.account', string='Credit Account(Interest)', domain=_get_loan_inst_cr_acc)
    loan_interest_balance = fields.Float(string='Balance(Interest)', default=0)

    # salary_advance_summary
    def _get_sal_adv_dr_acc(self):
        salary_adb_acc_sett_obj = self.env['hr.account.settings'].search(
            [('type', '=', 'salary_advance'), ('is_transfer_dr', '=', True)])
        salary_adv_dr_acc = salary_adb_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', salary_adv_dr_acc.ids)]

    def _get_sal_adv_cr_acc(self):
        salary_adb_acc_sett_obj = self.env['hr.account.settings'].search(
            [('type', '=', 'salary_advance'), ('is_transfer_cr', '=', True)])
        salary_adv_cr_acc = salary_adb_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', salary_adv_cr_acc.ids)]

    salary_adv_dr_acc = fields.Many2one('account.account', string='Debit Account(ADV)', domain=_get_sal_adv_dr_acc)
    salary_adv_cr_acc = fields.Many2one('account.account', string='Credit Account(ADV)', domain=_get_sal_adv_cr_acc)
    salary_adv_balance = fields.Float(string='Balance(ADV)', default=0)

    # tds_summary
    def _get_tds_dr_acc(self):
        tds_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'tds'), ('is_transfer_dr', '=', True)])
        tds_dr_acc = tds_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', tds_dr_acc.ids)]

    def _get_tds_cr_acc(self):
        tds_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'tds'), ('is_transfer_cr', '=', True)])
        tds_cr_acc = tds_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', tds_cr_acc.ids)]

    tds_dr_acc = fields.Many2one('account.account', string='Debit Account(TDS)', domain=_get_tds_dr_acc)
    tds_cr_acc = fields.Many2one('account.account', string='Credit Account(TDS)', domain=_get_tds_cr_acc)
    tds_balance = fields.Float(string='Balance TDS', default=0)

    # pf_summary
    def _get_pf_dr_acc(self):
        pf_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'pf'), ('is_transfer_dr', '=', True)])
        pf_dr_acc = pf_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', pf_dr_acc.ids)]

    def _get_pf_cr_acc(self):
        pf_acc_sett_obj = self.env['hr.account.settings'].search([('type', '=', 'pf'), ('is_transfer_cr', '=', True)])
        pf_cr_acc = pf_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', pf_cr_acc.ids)]

    pf_dr_acc = fields.Many2one('account.account', string='Debit Account(PF)', domain=_get_pf_dr_acc)
    pf_cr_acc = fields.Many2one('account.account', string='Credit Account(PF)', domain=_get_pf_cr_acc)
    pf_balance = fields.Float(string='Balance(PF)', default=0)

    # salary_payable_summary
    def _get_sal_pay_dr_acc(self):
        salary_pay_acc_sett_obj = self.env['hr.account.settings'].search(
            [('type', '=', 'salary_payable'), ('is_transfer_dr', '=', True)])
        salary_payable_dr_acc = salary_pay_acc_sett_obj.mapped('dr_acc')
        return [('id', 'in', salary_payable_dr_acc.ids)]

    def _get_sal_pay_cr_acc(self):
        salary_pay_acc_sett_obj = self.env['hr.account.settings'].search(
            [('type', '=', 'salary_payable'), ('is_transfer_cr', '=', True)])
        salary_payable_cr_acc = salary_pay_acc_sett_obj.mapped('cr_acc')
        return [('id', 'in', salary_payable_cr_acc.ids)]

    salary_payable_dr_acc = fields.Many2one('account.account', string='Debit Account(Payable)', domain=_get_sal_pay_dr_acc)
    salary_payable_cr_acc = fields.Many2one('account.account', string='Credit Account(Payable)', domain=_get_sal_pay_cr_acc)
    salary_payable_balance = fields.Float(string='Balance(Payable)', default=0)

    leave_casual_balance = fields.Integer(string='Casual Leave Balance', default=0)
    leave_sick_balance = fields.Integer(string='Sick Leave Balance', default=0)
    leave_marriage_balance = fields.Integer(string='Marriage Leave Balance', default=0)

    @api.onchange('to_department_id')
    def _onchange_department(self):
        if self.to_department_id:
            self.to_position = ""

    def set_balance(self):
        for rec in self:
            if rec.loan_cr_acc:
                loan_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.loan_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                loan_balance = 0
            if rec.loan_interest_cr_acc:
                loan_interest_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.loan_interest_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                loan_interest_balance = 0
            if rec.salary_adv_cr_acc:
                salary_adv_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.salary_adv_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                salary_adv_balance = 0
            if rec.tds_cr_acc:
                tds_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.tds_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                tds_balance = 0
            if rec.pf_cr_acc:
                pf_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.pf_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                pf_balance = 0
            if rec.salary_payable_cr_acc:
                salary_payable_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.salary_payable_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                salary_payable_balance = 0

            # -----------
            leave_casual_balance = 0
            leave_sick_balance = 0
            leave_marriage_balance = 0

            y = int(self.date_exec.year)
            start_date = date(y, 1, 1)
            end_date = date(y, 12, 31)

            self.env.cr.execute(
                """
            SELECT tbl1.emp_id, tbl1.type_name, tbl1.type_code, (COALESCE(tbl1.alloc_count, 0) - COALESCE(tbl2.leave_count, 0)) AS leave_bal
            FROM(
                SELECT hlt.name AS type_name, hlt.type_code AS type_code, hla.employee_id AS emp_id, COALESCE(hla.number_of_days, 0) AS alloc_count
                FROM hr_leave_type hlt
                LEFT JOIN hr_leave_allocation hla ON hla.holiday_status_id = hlt.id
                WHERE hla.state='validate' AND hlt.active='True' AND EXTRACT(YEAR FROM (hlt.validity_stop)) = {0}
                GROUP BY hlt.id, hlt.name, hlt.type_code, hla.id, hla.number_of_days
                ORDER BY hlt.type_code
                ) tbl1
            LEFT JOIN (
                SELECT leave_tbl.leave_id, leave_tbl.type_code, leave_tbl.emp_id, COALESCE(SUM(hld.leave_no), 0) AS leave_count
                FROM (
                        SELECT hl.id AS leave_id, hlt.type_code AS type_code, hl.employee_id AS emp_id
                        FROM hr_leave hl
                        LEFT JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                        WHERE hl.state='validate'
                        AND DATE(hl.request_date_to) BETWEEN '{1}' AND '{2}'
                        GROUP BY hl.id, hlt.type_code, hl.employee_id
                    ) leave_tbl
                LEFT JOIN hr_leave_details hld ON hld.leave_id = leave_tbl.leave_id
                WHERE DATE(hld.leave_date) BETWEEN '{1}' AND '{2}'
                GROUP BY leave_tbl.leave_id, leave_tbl.type_code, leave_tbl.emp_id
                ORDER BY leave_tbl.type_code
                ) tbl2 ON (tbl2.emp_id = tbl1.emp_id AND tbl2.type_code = tbl1.type_code)
            WHERE tbl1.emp_id = {3}
            ORDER BY tbl1.emp_id, tbl1.type_code
            """.format(y, start_date, end_date, rec.employee_id.id))
            leave_rows = self.env.cr.dictfetchall()
            for row in leave_rows:
                type_code = row['type_code']
                leave_bal = row['leave_bal']
                if type_code == 'CL':  # casual leave
                    leave_casual_balance = leave_bal
                elif type_code == 'SL':  # Sick Leave
                    leave_sick_balance = leave_bal
                elif type_code == 'ML':  # Marriage Leave
                    leave_marriage_balance = leave_bal

            # ------------
            rec.sudo().write({
                'loan_balance': loan_balance,
                'loan_interest_balance': loan_interest_balance,
                'salary_adv_balance': salary_adv_balance,
                'tds_balance': tds_balance,
                'pf_balance': pf_balance,
                'salary_payable_balance': salary_payable_balance,
                'leave_casual_balance': leave_casual_balance,
                'leave_sick_balance': leave_sick_balance,
                'leave_marriage_balance': leave_marriage_balance
            })

    def action_confirm(self):
        for records in self:
            if not records.emp_private_address_id:
                raise UserError(_('Private Address not mapped for employee: %s') % records.employee_id.name)

            records.name = self.env['ir.sequence'].get('hr_transfer_code')
            records.sudo().write({'state': 'confirm'})

    def action_supervisor_existing(self):
        for records in self:
            records.sudo().write({'state': 'supervisor_existing'})

    def action_hr_approved(self):
        for records in self:
            records.sudo().write({'state': 'hr_approved'})

    def action_supervisor_new(self):
        for records in self:
            records.sudo().write({'state': 'supervisor_new'})

    def action_md_approved(self):
        for records in self:
            records.sudo().write({'state': 'md_approved'})

    def action_accounting_approved(self):
        for records in self:
            if records.transfer_company == '1':
                records.set_balance()
            records.sudo().write({'state': 'accounting_approved'})

    def action_transfer(self):
        for rec in self:
            if rec.date_exec > date.today():
                raise UserError("Transfer can not be done before effective date")
            transfer_status = True
            if rec.transfer_company == '0':
                rec.employee_id.department_id = rec.to_department_id.id
                rec.employee_id.user_work_location_id = rec.to_wh_location_id.id
                rec.employee_id.job_id = rec.to_position.id
                rec.employee_id.parent_id = rec.to_manager_id.id
                rec.employee_id.contract_id.resource_calendar_id = rec.to_resource_calendar.id
                rec.employee_id.contract_id.att_policy_id = rec.to_att_policy_id.id
                rec.employee_id.contract_id.department_id = rec.to_department_id.id
                rec.employee_id.contract_id.job_id = rec.to_position.id

            if rec.transfer_company == '1':
                api_status = self.get_employee_transfer()
                if api_status == True:
                    other_company_job_location = ''
                    if rec.other_company_job_location_id:
                        other_company_job_location = rec.other_company_job_location_id.name
                    other_company_department = ''
                    if rec.other_company_department_id:
                        other_company_department = rec.other_company_department_id.name
                    other_company_job_position = ''
                    if rec.other_company_job_position_id:
                        other_company_job_position = rec.other_company_job_position_id.name
                    other_company_work_schedule = ''
                    if rec.other_company_work_schedule_id:
                        other_company_work_schedule = rec.other_company_work_schedule_id.name
                    other_company_att_policy = ''
                    if rec.other_company_att_policy_id:
                        other_company_att_policy = rec.other_company_att_policy_id.name

                    # ----------- Account Balance
                    loan_balance = rec.loan_balance
                    loan_interest_balance = rec.loan_interest_balance
                    salary_adv_balance = rec.salary_adv_balance
                    tds_balance = rec.tds_balance
                    pf_balance = rec.pf_balance
                    salary_payable_balance = rec.salary_payable_balance

                    leave_casual_balance = rec.leave_casual_balance
                    leave_sick_balance = rec.leave_sick_balance
                    leave_marriage_balance = rec.leave_marriage_balance

                    self.env['inter.company.transfer.history'].create({
                        'transfer_type': 'out',
                        'transfer_reference': rec.id,
                        'employee_name': rec.employee_id.name,
                        'from_job_location': rec.location_id.name,
                        'from_company': rec.company_id.name,
                        'from_designation': rec.job_position.name,
                        'from_department': rec.department_id.name,
                        'to_company': rec.other_company_name.id,
                        'device_user_id': rec.device_user_id,
                        'identification_id': rec.employee_id.identification_id,
                        'id_card_no': rec.employee_id.id_card_no,
                        'door_card_no': rec.employee_id.door_card_no,
                        'work_email': rec.employee_id.work_email,
                        'contact_no': rec.employee_id.contact_no,

                        'to_job_location': other_company_job_location,
                        'to_department': other_company_department,
                        'to_designation': other_company_job_position,
                        'to_resource_calendar': other_company_work_schedule,
                        'to_att_policy': other_company_att_policy,

                        'requested_date': rec.date_requested,
                        'effected_date': rec.date_exec,
                        'initial_employment_date': rec.initial_employment_date,
                        'note': rec.note,
                        'gross_salary': rec.gross_salary,
                        'total_residual_loan': rec.total_residual_loan,
                        'advance_salary': rec.advance_salary,
                        'residual_Salary': rec.residual_Salary,

                        'loan_balance': loan_balance,
                        'loan_interest_balance': loan_interest_balance,
                        'salary_adv_balance': salary_adv_balance,
                        'tds_balance': tds_balance,
                        'pf_balance': pf_balance,
                        'salary_payable_balance': salary_payable_balance,

                        'leave_casual_balance': leave_casual_balance,
                        'leave_sick_balance': leave_sick_balance,
                        'leave_marriage_balance': leave_marriage_balance
                    })
                    rec.employee_id.active = False
                else:
                    transfer_status = False

            # ------------------  journal Entry for other company
            if rec.transfer_company == '1' and transfer_status == True:
                move_line = []

                if rec.emp_private_address_id:
                    partner_id = rec.emp_private_address_id.id

                journal_id = self.env['account.journal'].search([('code', '=', 'JRV')], limit=1)

                if not journal_id:
                    journal_id = self.env['account.journal'].search([('type', '=', 'general')], limit=1)

                # loan debit & credit account and balance
                if rec.loan_balance != 0:
                    loan_debit_val = {
                        'account_id': rec.loan_dr_acc.id,
                        'debit': rec.loan_balance,
                        'credit': 0.0,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, loan_debit_val))

                    loan_credit_val = {
                        'account_id': rec.loan_cr_acc.id,
                        'debit': 0.0,
                        'credit': rec.loan_balance,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, loan_credit_val))

                # loan interest debit & credit account and balance
                if rec.loan_interest_balance != 0:
                    loan_inst_debit_val = {
                        'account_id': rec.loan_interest_dr_acc.id,
                        'debit': rec.loan_interest_balance,
                        'credit': 0.0,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, loan_inst_debit_val))

                    loan_inst_credit_val = {
                        'account_id': rec.loan_interest_cr_acc.id,
                        'debit': 0.0,
                        'credit': rec.loan_interest_balance,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, loan_inst_credit_val))

                # salary advance debit & credit account and balance
                if rec.salary_adv_balance != 0:
                    sal_adv_debit_val = {
                        'account_id': rec.salary_adv_dr_acc.id,
                        'debit': rec.salary_adv_balance,
                        'credit': 0.0,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, sal_adv_debit_val))

                    sal_adv_credit_val = {
                        'account_id': rec.salary_adv_cr_acc.id,
                        'debit': 0.0,
                        'credit': rec.salary_adv_balance,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, sal_adv_credit_val))

                # tds debit & credit account and balance
                if rec.tds_balance != 0:
                    tds_debit_val = {
                        'account_id': rec.tds_dr_acc.id,
                        'debit': rec.tds_balance,
                        'credit': 0.0,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, tds_debit_val))

                    tds_credit_val = {
                        'account_id': rec.tds_cr_acc.id,
                        'debit': 0.0,
                        'credit': rec.tds_balance,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, tds_credit_val))

                # pf debit & credit account and balance
                if rec.pf_balance != 0:
                    pf_debit_val = {
                        'account_id': rec.pf_dr_acc.id,
                        'debit': rec.pf_balance,
                        'credit': 0.0,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, pf_debit_val))

                    pf_credit_val = {
                        'account_id': rec.pf_cr_acc.id,
                        'debit': 0.0,
                        'credit': rec.pf_balance,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, pf_credit_val))

                # salary payable debit & credit account and balance
                if rec.salary_payable_balance != 0:
                    sal_pay_debit_val = {
                        'account_id': rec.salary_payable_dr_acc.id,
                        'debit': rec.salary_payable_balance,
                        'credit': 0.0,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, sal_pay_debit_val))

                    sal_pay_credit_val = {
                        'account_id': rec.salary_payable_cr_acc.id,
                        'debit': 0.0,
                        'credit': rec.salary_payable_balance,
                        'partner_id': partner_id,
                        'name': rec.name,
                        #'exclude_from_invoice_tab': False,
                    }
                    move_line.append((0, 0, sal_pay_credit_val))
                if rec.loan_balance != 0 or rec.loan_interest_balance != 0 or rec.salary_adv_balance != 0 or rec.tds_balance != 0 or rec.pf_balance != 0 or rec.salary_payable_balance != 0:
                    # journal creation
                    self.env['account.move'].create({
                        'ref': rec.name,
                        'name': '/',
                        'partner_id': partner_id,
                        'journal_id': journal_id.id,
                        'line_ids': move_line,
                    })

            # ------- status update
            if transfer_status == True:
                last_rec=self.env['hr.employee.transfer.history'].sudo().search([('employee_id', '=', rec.employee_id.id),('effective_date', '<=', rec.date_exec)], order='effective_date desc', limit=1)
                if last_rec:
                    prev_from_date = last_rec[0].effective_date
                else:
                    prev_from_date = rec.employee_id.initial_employment_date if rec.employee_id.initial_employment_date else None

                prev_to_date = rec.date_exec - timedelta(days=1)

                self.env['hr.employee.transfer.history'].create({
                    'employee_id': rec.employee_id.id,
                    'type': rec.transfer_company,
                    'from_company': rec.company_id.name,
                    'to_company': rec.other_company_name.id,
                    'from_location': rec.location_id.name,
                    'to_location': rec.to_wh_location_id.name,
                    'from_department_id': rec.department_id.id,
                    'to_department_id': rec.to_department_id.id,
                    'effective_date': rec.date_exec,
                    'prev_from_date': prev_from_date,
                    'prev_to_date': prev_to_date
                })
                rec.sudo().write({'state': 'transfer'})
            else:
                raise UserError('Transfer failed!')

    def action_cancel(self):
        for records in self:
            records.sudo().write({'state': 'cancel'})

    def unlink(self):
        for loan in self:
            if loan.state not in ('draft'):
                raise UserError(
                    'You cannot delete a transfer which is confirmed')
        return super(EmployeeTransfer, self).unlink()

    @api.onchange('employee_id', 'date_exec')
    def _onchange_field_employee_id(self):
        for record in self:
            if record.employee_id:
                record.residual_Salary = 0
                record.from_emp_contract = self.env['hr.contract'].sudo().search(
                    [('employee_id', '=', record.employee_id.id), ('state', '=', 'open')]).id
                record.gross_salary = record.from_emp_contract.gross_salary
                record.company_id = record.employee_id.company_id
                #record.current_amount = record.from_emp_contract.wage
                record.old_empid = record.employee_id.id_card_no
                record.device_user_id = record.employee_id.device_user_id
                record.identification_id = record.employee_id.identification_id
                record.id_card_no = record.employee_id.id_card_no
                record.door_card_no = record.employee_id.door_card_no

                record.employee_id = record.employee_id.id
                record.location_id = record.employee_id.user_work_location_id.id
                record.resource_calendar = record.employee_id.resource_calendar_id.id
                record.department_id = record.employee_id.department_id.id
                record.job_position = record.employee_id.job_id.id
                record.manager_id = record.employee_id.parent_id.id
                record.work_email = record.employee_id.work_email
                record.contact_no = record.employee_id.contact_no
                record.initial_employment_date = record.employee_id.initial_employment_date

                loan_obj = self.env['employee.loan'].search(
                    [('employee_id', '=', record.employee_id.id), ('type_id_type', '=', 'general'), ('state', '=', 'done'),
                     ('is_close', '=', False)]).mapped('remaing_amount')
                record.total_residual_loan = sum(loan_obj)
                adv_obj = self.env['salary.advance'].search(
                    [('employee_id', '=', record.employee_id.id), ('state', '=', 'approve'),
                     ('payslip_id', '=', False)], order='id DESC', limit=1)
                record.advance_salary = adv_obj.advance
                salary_pay_obj = self.env['hr.payslip'].search(
                    [('employee_id', '=', record.employee_id.id), ('state', '=', 'verify')], order='id DESC', limit=1)
                if salary_pay_obj:
                    delay = """select amount from hr_payslip_line where slip_id = %s order by id desc limit 1 """
                    self._cr.execute(delay, [salary_pay_obj.id])
                    residual_salary = self.env.cr.dictfetchall()
                    record.residual_Salary = residual_salary[0]['amount']

    @api.depends('emp_private_address_id', 'loan_cr_acc', 'loan_interest_cr_acc', 'salary_adv_cr_acc', 'tds_cr_acc',
                 'pf_cr_acc', 'salary_payable_cr_acc')
    def _compute_account_balance(self):
        for rec in self:
            if rec.loan_cr_acc:
                rec.loan_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.loan_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                rec.loan_balance = 0
            if rec.loan_interest_cr_acc:
                rec.loan_interest_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.loan_interest_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                rec.loan_interest_balance = 0
            if rec.salary_adv_cr_acc:
                rec.salary_adv_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.salary_adv_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                rec.salary_adv_balance = 0
            if rec.tds_cr_acc:
                rec.tds_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.tds_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                rec.tds_balance = 0
            if rec.pf_cr_acc:
                rec.pf_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.pf_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                rec.pf_balance = 0
            if rec.salary_payable_cr_acc:
                rec.salary_payable_balance = sum(self.env['account.move.line'].search(
                    [('account_id', '=', rec.salary_payable_cr_acc.id), ('parent_state', '=', 'posted'),
                     ('partner_id', '=', rec.emp_private_address_id.id)]).mapped('balance'))
            else:
                rec.salary_payable_balance = 0

    @api.onchange('other_company_name')
    def _onchange_other_company_name(self):
        return {'value': {'other_company_job_location_id': None, 'other_company_department_id': None,
                          'other_company_job_position_id': None}}

    @api.onchange('other_company_department_id')
    def _onchange_other_company_department(self):
        return {'value': {'other_company_job_position_id': None}}

    @api.onchange('total_residual_loan', 'advance_salary', 'residual_Salary')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.total_residual_loan + rec.advance_salary + rec.residual_Salary

    def get_employee_transfer(self):
        # ----------------
        transfer_url = self.other_company_name.url
        company_code = self.other_company_name.company_code
        company_name = self.other_company_name.name
        db_name = self.other_company_name.db_name
        user_id = self.other_company_name.user_id
        password = self.other_company_name.password
        access_token = self.other_company_name.access_token
        # --------------------
        employee_name = self.employee_id.name
        from_company = self.company_id.name
        from_department = self.department_id.name
        from_designation = self.job_position.name
        from_job_location = self.location_id.name
        transfer_reference = self.name
        to_company = self.other_company_name.name
        device_user_id = self.device_user_id
        identification_id = self.identification_id
        id_card_no = self.id_card_no
        door_card_no = self.door_card_no
        work_email = self.work_email
        contact_no = self.contact_no
        # initial_employment_date = self.initial_employment_date
        to_job_location = ''
        to_job_location_id = ''
        if self.other_company_job_location_id:
            to_job_location = self.other_company_job_location_id.name
            to_job_location_id = self.other_company_job_location_id.rec_id

        to_department = ''
        to_department_id = ''
        if self.other_company_department_id:
            to_department = self.other_company_department_id.name
            to_department_id = self.other_company_department_id.rec_id

        to_designation = ''
        to_designation_id = ''
        if self.other_company_job_position_id:
            to_designation = self.other_company_job_position_id.name
            to_designation_id = self.other_company_job_position_id.rec_id

        to_resource_calendar = ''
        to_resource_calendar_id = ''
        if self.other_company_work_schedule_id:
            to_resource_calendar = self.other_company_work_schedule_id.name
            to_resource_calendar_id = self.other_company_work_schedule_id.rec_id

        to_att_policy = ''
        to_att_policy_id = ''
        if self.other_company_att_policy_id:
            to_att_policy = self.other_company_att_policy_id.name
            to_att_policy_id = self.other_company_att_policy_id.rec_id

        requested_date = str(self.date_requested)
        effected_date = str(self.date_exec)
        initial_employment_date = str(self.initial_employment_date)
        note = self.note

        gross_salary = self.gross_salary
        total_residual_loan = self.total_residual_loan
        advance_salary = self.advance_salary
        residual_Salary = self.residual_Salary

        # ----------- Account Balance
        loan_balance = self.loan_balance
        loan_interest_balance = self.loan_interest_balance
        salary_adv_balance = self.salary_adv_balance
        tds_balance = self.tds_balance
        pf_balance = self.pf_balance
        salary_payable_balance = self.salary_payable_balance
        # ----------
        leave_casual_balance = self.leave_casual_balance
        leave_sick_balance = self.leave_sick_balance
        leave_marriage_balance = self.leave_marriage_balance

        # ------------
        url_connect = transfer_url + '/web/session/authenticate'
        params = {
            'db': db_name,
            'login': user_id,
            'password': password
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
            # 'Content-Length': str(len(json.dumps(params)))
        }
        session = requests.Session()
        response = session.post(url=url_connect, data=json.dumps({'params': params}), headers=headers)
        server_response = response.json()

        session_details = server_response['result']
        if server_response['result']['uid']:
            session_id = str(response.cookies.get('session_id'))

            odoo_url = transfer_url + '/api/transfer/create'
            session.cookies['session_id'] = session_id

            # headers = {
            #     'Content-Type': 'application/json',
            #     'Accept': 'application/json',
            #     'Cookies': 'session_id= %s'%session_id
            # }
            params = {
                'company_code': company_code,
                'company_name': company_name,
                'user_id': user_id,
                'password': password,
                'db_name': db_name,
                'access_token': access_token,

                'employee_name': employee_name,
                'from_company': from_company,
                'from_department': from_department,
                'from_designation': from_designation,
                'from_job_location': from_job_location,

                'in_reference': transfer_reference,
                'to_company': to_company,
                'device_user_id': device_user_id,
                'identification_id': identification_id,
                'id_card_no': id_card_no,
                'door_card_no': door_card_no,
                'work_email': work_email,
                'contact_no': contact_no,
                'initial_employment_date': initial_employment_date,
                'to_job_location': to_job_location,
                'to_department': to_department,
                'to_designation': to_designation,
                'to_resource_calendar': to_resource_calendar,
                'to_att_policy': to_att_policy,

                'to_job_location_id': to_job_location_id,
                'to_department_id': to_department_id,
                'to_designation_id': to_designation_id,
                'to_resource_calendar_id': to_resource_calendar_id,
                'to_att_policy_id': to_att_policy_id,

                'requested_date': requested_date,
                'effected_date': effected_date,
                'note': note,
                'gross_salary': gross_salary,
                'total_residual_loan': total_residual_loan,
                'advance_salary': advance_salary,
                'residual_Salary': residual_Salary,

                'loan_balance': loan_balance,
                'loan_interest_balance': loan_interest_balance,
                'salary_adv_balance': salary_adv_balance,
                'tds_balance': tds_balance,
                'pf_balance': pf_balance,
                'salary_payable_balance': salary_payable_balance,

                'leave_casual_balance': leave_casual_balance,
                'leave_sick_balance': leave_sick_balance,
                'leave_marriage_balance': leave_marriage_balance
            }

            data = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params})
            # headers = json.dumps(headers)

            # response = requests.post(url=odoo_url, data=data, headers=headers)
            response = session.post(url=odoo_url, data=data, headers=headers)
            server_response = response.json()
            if server_response['result']['status'] == '1':
                return True
            else:
                return False

        else:
            return False
