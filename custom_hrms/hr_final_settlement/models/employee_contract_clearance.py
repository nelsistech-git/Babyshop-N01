# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from num2words import num2words


class EmployeeClearance(models.Model):
    _name = 'employee.contract.clearance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Clearance"
    _order = "id desc"
    _inherit = 'mail.thread'
    _rec_name = 'doc_ref'

    name = fields.Char(string='Name', copy=False, tracking=True)
    doc_ref = fields.Char(string='Doc Ref.')
    date_requested = fields.Datetime(string="Creation Date", default=fields.Datetime.now)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    company_id = fields.Many2one('res.company', string='Company')
    department_id = fields.Many2one('hr.department', string="Department")
    old_empid = fields.Char(string="Employee ID")
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    job_position = fields.Many2one('hr.job', string="Designation")
    initial_employment_date = fields.Date(string='Date of Joining')
    length_of_service = fields.Char(string='Length of Service')
    separation_type_id = fields.Char(string='Separation Type') #will delete later
    last_day_of_work = fields.Date(string="Last Working Day", tracking=True)
    gross_salary = fields.Float(string='Gross Salary')
    daily_allowance = fields.Float(string='Daily Allowance')
    per_day_salary = fields.Float(string='Per Day Salary')
    total_attendance_salary = fields.Float(string='Total Attendance Salary')
    lunch_allowance = fields.Float(string='Lunch Allowance')
    leave_encashment = fields.Float(string='Leave Encashment')
    no_overtime = fields.Integer(string="No. of Overtimes", readonly=True)
    ot_day_count = fields.Float(string="Actual Overtime(Hour)")
    no_of_present_day = fields.Integer(string='No. of Present Day')
    advance_salary = fields.Float(string='Advance')
    loan = fields.Float(string='Loan')
    lunch_bill = fields.Float(string='Lunch Bill')
    penalty = fields.Float(string='Penalty')
    excess_leave = fields.Float(string='Excess Leave')
    other_dues = fields.Float(string='Other Dues')
    total_deduct = fields.Float(string='Total Deduct')

    outgoing_emp_id = fields.Many2one('hr.employee', string='Employee')
    mailing_address = fields.Char(string='Mailing Address')
    emp_id_phone = fields.Char(string='Contact Phone')
    emp_id_mobile = fields.Char(string='Mobile')
    emp_id_email = fields.Char(string='Email')
    emp_id_nid = fields.Char(string='National ID')
    emp_id_passport = fields.Char(string='Passport')
    remarks = fields.Text(string='Remarks, (if any)')
    emp_contract = fields.Many2one('hr.contract', string='Employee', store=True)
    note = fields.Html(string='')
    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Submitted'),
        ('concerned_dept', 'Concerned Dept. Clearance'),
        ('account', 'Accounts Clearance'),
        ('admin', 'Admin Clearance'),
        ('it', 'IT Clearance'),
        ('hr', 'HR Clearance'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string="State", default='draft', tracking=True, copy=False)
    facility_lines = fields.One2many('employee.contract.fringe.benefits', 'contract_clearance_id')
    section_a_lines = fields.One2many('employee.contract.clearance.section.a.lines', 'contract_clearance_id')
    section_b_lines = fields.One2many('employee.contract.clearance.section.b.lines', 'contract_clearance_id')
    section_c_lines = fields.One2many('employee.contract.clearance.section.c.lines', 'contract_clearance_id')
    section_d_lines = fields.One2many('employee.contract.clearance.section.d.lines', 'contract_clearance_id')
    section_e_lines = fields.One2many('employee.contract.clearance.section.e.lines', 'contract_clearance_id')

    a_remarks = fields.Text(string="Remarks, (if any)")
    b_remarks = fields.Text(string="Remarks, (if any)")
    c_remarks = fields.Text(string="Remarks, (if any)")
    d_remarks = fields.Text(string="Remarks, (if any)")
    e_remarks = fields.Text(string="Remarks, (if any)")

    ref_id = fields.Many2one('hr.resignation', string='Separation Reference')
    resignation_type_id = fields.Many2one('hr.separation.type.settings', string='Separation Type', related='ref_id.resignation_type_id')
    date_of_separation = fields.Date(string="Separation Approved Date", tracking=True, related='ref_id.resign_approve_date')
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
    gross_salary = fields.Float(string="Gross Salary")
    deduction_of_gross = fields.Float(string="Deduction of Notice Period")
    total_daily_allowance = fields.Integer(compute='_compute_total_daily_allowance')

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.doc_ref = 'Final Settlement of ' + rec.employee_id.name or None

                rec.user_work_location_id = rec.employee_id.user_work_location_id.id
                rec.company_id = rec.employee_id.company_id.id
                rec.department_id = rec.employee_id.department_id.id
                rec.old_empid = rec.employee_id.id_card_no
                rec.job_position = rec.employee_id.job_id.id
                rec.initial_employment_date = rec.employee_id.initial_employment_date
                rec.length_of_service = rec.employee_id.length_of_service
                rec.emp_id_email = rec.employee_id.work_email
                rec.emp_id_passport = rec.employee_id.passport_id
                rec.emp_id_nid = rec.employee_id.nid
                rec.emp_id_mobile = rec.employee_id.contact_no
                rec.outgoing_emp_id = rec.employee_id.id

                rec.gross_salary = rec.employee_id.contract_id.gross_salary
                rec.daily_allowance = rec.employee_id.contract_id.daily_allowance
                rec.lunch_allowance = rec.employee_id.contract_id.meal_allowance


                resig_obj = self.env['hr.resignation'].sudo().search([('employee_id', '=', rec.employee_id.id), ('state', '=', 'approved')], limit=1)
                for resig in resig_obj:
                    rec.ref_id = resig.id
                    rec.last_day_of_work = resig.expected_revealing_date
                    rec.notice_period = 'yes'
                    rec.notice_period_days = resig.notice_period
                    rec.deduction_value = resig.deduction
                    rec.gross_salary = resig.gross_salary
                    rec.deduction_of_gross = resig.deduction_of_gross


                facility_obj = self.env['hr.facilities'].search([('employee_id', '=', rec.employee_id.id)])
                facility_list = []
                for data in facility_obj:
                    vals = {
                        'contract_clearance_id': rec.id,
                        'dept_name': data.dept_name,
                        'value': data.value,
                        'qty': data.qty,
                        'particular_id': data.particular_id,
                    }
                    facility_list.append((0, 0, vals))
                rec.facility_lines = facility_list


    @api.onchange('employee_id', 'last_day_of_work', 'lunch_bill', 'penalty', 'excess_leave', 'other_dues', 'deduction_of_gross')
    def _onchange_employee_id_last_day_of_work(self):
        for rec in self:
            if rec.employee_id and rec.last_day_of_work:
                att_obj = self.env['attendance.sheet'].search(
                    [('employee_id', '=', rec.employee_id.id), ('date_from', '<=', rec.last_day_of_work),
                     ('date_to', '>=', rec.last_day_of_work), ('state', '=', 'done')], limit=1)
                if att_obj:
                    rec.per_day_salary = att_obj.per_day_salary
                    rec.no_of_present_day = att_obj.no_presence
                    rec.no_overtime = att_obj.no_overtime
                    rec.ot_day_count = att_obj.ot_day_count
                    rec.total_attendance_salary = att_obj.per_day_salary * att_obj.no_presence
                else:
                    raise UserError('Warning! Please generate attendance sheet of %s-%s for "%s".' % (
                    rec.last_day_of_work.strftime("%B"), rec.last_day_of_work.year, rec.employee_id.name))

                adv_obj = self.env['salary.advance'].search(
                    [('employee_id', '=', rec.employee_id.id), ('is_deducted', '=', False), ('state', '=', 'approve')])
                advance_salary = 0
                for advs in adv_obj:
                    advance_salary += advs.advance
                rec.advance_salary = advance_salary

                loan_obj = self.env['employee.loan'].search([('employee_id', '=', rec.employee_id.id), ('state', '=', 'done'), ('is_close', '=', False)])
                total_remaing_amount = 0
                for loan in loan_obj:
                    total_remaing_amount += loan.remaing_amount
                rec.loan = total_remaing_amount

                rec.total_deduct = rec.advance_salary + rec.loan + rec.lunch_bill + rec.penalty + rec.excess_leave + rec.other_dues + rec.deduction_of_gross


    def unlink(self):
        for loan in self:
            if loan.state not in ('draft'):
                raise UserError(
                    'You cannot delete a settelment which is confirmed')
        return super(EmployeeClearance, self).unlink()

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    def _compute_employee_loans(self):
        for records in self:
            records.loan_count = self.env['employee.loan'].search_count([('employee_id', '=', records.employee_id.id),('state', '=', 'done'), ('is_close', '=', False)])

    @api.depends("daily_allowance", "no_of_present_day")
    def _compute_total_daily_allowance(self):
        for rec in self:
            rec.total_daily_allowance = round(rec.daily_allowance * rec.no_of_present_day,0)

    loan_count = fields.Integer(string="Loan Count", compute='_compute_employee_loans')

    def act_current_employee_loan(self):
        tree_view_id = self.env.ref('dev_hr_loan.view_employee_loan_tree').id
        return {
            'name': "Loan Lines",
            'type': 'ir.actions.act_window',
            'res_model': 'employee.loan',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': False,
            'context': False,
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id)],
        }

    def _compute_employee_payslips_ids(self):
        for records in self:
            records.payslips_count = self.env['hr.payslip'].search_count([('employee_id', '=', records.employee_id.id)])

    payslips_count = fields.Integer(string="Payslip Count", compute='_compute_employee_payslips_ids')

    def act_current_payslips_count(self):
        tree_view_id = self.env.ref('hr_payroll.view_hr_payslip_tree').id
        return {
            'name': "Payslip",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': False,
            'context': False,
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id)],
        }

    def _compute_employee_advance_count(self):
        for records in self:
            records.advance_count = self.env['salary.advance'].search_count(
                [('employee_id', '=', records.employee_id.id), ('state', '!=', 'draft')])

    advance_count = fields.Integer(compute='_compute_employee_advance_count')

    def act_current_advance_count(self):
        tree_view_id = self.env.ref('hr_salary_advance.view_salary_advance_tree').id
        return {
            'name': "Salary Advances",
            'type': 'ir.actions.act_window',
            'res_model': 'salary.advance',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_id': False,
            'context': False,
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id)],
        }

    def act_disciplinary_count(self):
        for records in self:
            disciplinarycount = self.env['hr.punishments'].search_count(
                [('employee_id', '=', records.employee_id.id), ('state', '!=', 'draft')])
            records.disciplinary_count = disciplinarycount

    disciplinary_count = fields.Integer(compute='act_disciplinary_count')

    def act_current_disciplinary_action(self):
        tree_view_id = self.env.ref('custom_hr_employee.hr_punishments_view_tree').id
        return {
            'name': "Disciplinary Action",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.punishments',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_id': False,
            'context': False,
            'target': 'current',
            'domain': [('employee_id', '=', self.employee_id.id)],
        }

    def action_cancel(self):
        for records in self:
            if self.state == 'done':
                records.employee_id.contract_id.state = 'open'
                records.employee_id.final_settlement_status = False
                records.employee_id.active = True
                records.sudo().write({'state': 'cancel'})
            else:
                records.sudo().write({'state': 'cancel'})

    def action_it_approve(self):
        for records in self:
            records.sudo().write({'state': 'it'})

    def action_submit(self):
        for records in self:
            records.name = self.env['ir.sequence'].get('hr_settelement_code')
            records.sudo().write({'state': 'confirm'})

    def action_hr_approve(self):
        for records in self:
            records.sudo().write({'state': 'hr'})

    def action_concerned_dept_approve(self):
        for records in self:
            records.sudo().write({'state': 'concerned_dept'})

    def action_accounts_approve(self):
        for records in self:
            records.sudo().write({'state': 'account'})

    def action_admin_approve(self):
        for records in self:
            records.sudo().write({'state': 'admin'})

    def action_done(self):
        for records in self:
            records.sudo().write({'state': 'done'})
            records.employee_id.contract_id.state = 'cancel'
            records.employee_id.final_settlement_status = True
            records.employee_id.active = False



    @api.model
    def default_get(self, fields):
        res = super(EmployeeClearance, self).default_get(fields)
        section_a_lines = []
        section_b_lines = []
        section_c_lines = []
        section_d_lines = []
        section_e_lines = []
        section_a_obj = self.env['final.settlement.settings'].search(
            [('section_type', '=', 'a')])
        section_b_obj = self.env['final.settlement.settings'].search(
            [('section_type', '=', 'b')])
        section_c_obj = self.env['final.settlement.settings'].search(
            [('section_type', '=', 'c')])
        section_d_obj = self.env['final.settlement.settings'].search(
            [('section_type', '=', 'd')])
        section_e_obj = self.env['final.settlement.settings'].search(
            [('section_type', '=', 'e')])
        if section_a_obj:
            for rec in section_a_obj:
                vals = {
                    'contract_clearance_id': self.env.context.get('active_ids'),
                    'final_settlement_settings_id': rec.id or None,
                }
                section_a_lines.append((0, 0, vals))
            res.update({'section_a_lines': section_a_lines})
        if section_b_obj:
            for rec in section_b_obj:
                vals = {
                    'contract_clearance_id': self.env.context.get('active_ids'),
                    'final_settlement_settings_id': rec.id or None,
                }
                section_b_lines.append((0, 0, vals))
            res.update({'section_b_lines': section_b_lines})
        if section_c_obj:
            for rec in section_c_obj:
                vals = {
                    'contract_clearance_id': self.env.context.get('active_ids'),
                    'final_settlement_settings_id': rec.id or None,
                }
                section_c_lines.append((0, 0, vals))
            res.update({'section_c_lines': section_c_lines})
        if section_d_obj:
            for rec in section_d_obj:
                vals = {
                    'contract_clearance_id': self.env.context.get('active_ids'),
                    'final_settlement_settings_id': rec.id or None,
                }
                section_d_lines.append((0, 0, vals))
            res.update({'section_d_lines': section_d_lines})
        if section_e_obj:
            for rec in section_e_obj:
                vals = {
                    'contract_clearance_id': self.env.context.get('active_ids'),
                    'final_settlement_settings_id': rec.id or None,
                }
                section_e_lines.append((0, 0, vals))
            res.update({'section_e_lines': section_e_lines})

        return res

    def amount_in_words(self, amount):
        amount_in_words = "".join(num2words(amount, lang='en_IN').title().replace("-", " ")).replace(",","") + " Only."
        return amount_in_words


class ConcernedDepartmentDivision(models.Model):
    _name = 'employee.contract.clearance.section.a.lines'
    _description = "Employee Clearance Section A Lines"

    contract_clearance_id = fields.Many2one('employee.contract.clearance')
    final_settlement_settings_id = fields.Many2one('final.settlement.settings', string="Particulars",
                                                   domain="[('section_type', '=', 'a')]")
    observation_type = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A'),
    ], string="Type", default='yes', copy=False)
    note = fields.Text()


class AccountsDepartment(models.Model):
    _name = 'employee.contract.clearance.section.b.lines'
    _description = "Employee Clearance Section B Lines"

    contract_clearance_id = fields.Many2one('employee.contract.clearance')
    final_settlement_settings_id = fields.Many2one('final.settlement.settings', string="Particulars",
                                                   domain="[('section_type', '=', 'b')]")
    observation_type = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A'),
    ], string="Type", default='yes', copy=False)
    note = fields.Text()


class AdminDepartment(models.Model):
    _name = 'employee.contract.clearance.section.c.lines'
    _description = "Employee Clearance Section C Lines"

    contract_clearance_id = fields.Many2one('employee.contract.clearance')
    final_settlement_settings_id = fields.Many2one('final.settlement.settings', string="Particulars",
                                                   domain="[('section_type', '=', 'c')]")
    observation_type = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A'),
    ], string="Type", default='yes', copy=False)
    note = fields.Text()


class ITDepartment(models.Model):
    _name = 'employee.contract.clearance.section.d.lines'
    _description = "Employee Clearance Section D Lines"

    contract_clearance_id = fields.Many2one('employee.contract.clearance')
    final_settlement_settings_id = fields.Many2one('final.settlement.settings', string="Particulars",
                                                   domain="[('section_type', '=', 'd')]")
    observation_type = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A'),
    ], string="Type", default='yes', copy=False)
    note = fields.Text()


class HRDepartment(models.Model):
    _name = 'employee.contract.clearance.section.e.lines'
    _description = "Employee Clearance Section E Lines"

    contract_clearance_id = fields.Many2one('employee.contract.clearance')
    final_settlement_settings_id = fields.Many2one('final.settlement.settings', string="Particulars",
                                                   domain="[('section_type', '=', 'e')]")
    observation_type = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A'),
    ], string="Type", default='yes', copy=False)
    note = fields.Text()

class FringeBenfits(models.Model):
    _name = 'employee.contract.fringe.benefits'
    _description = "Employee Clearance Fringe Benfits"

    contract_clearance_id = fields.Many2one('employee.contract.clearance')
    observation_type = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'N/A'),
    ], string="Type", default='yes', copy=False)
    note = fields.Text()
    value = fields.Float(string="Value", help="Put any type of value here")
    qty = fields.Integer(string="Qty", help="Put qty of particulars")
    employee_id = fields.Many2one('hr.employee', string='Employee')
    dept_name = fields.Selection([('it', 'IT'),
                                  ('admin', 'Admin'), ('hr', 'HR'), ], string='Department')
    particular_id = fields.Many2one('hr.particulars', string="Particular", domain="[('dept_name', '=', dept_name)]")
