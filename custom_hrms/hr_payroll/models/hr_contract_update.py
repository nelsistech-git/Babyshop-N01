from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class EmployeeContractUpdate(models.Model):
    _name = 'hr.contract.update'
    _description = "Employee Contract Update"
    _order = "id desc"

    name = fields.Char(string='Name', copy=False)
    type = fields.Selection(
        [('increment', 'Increment'), ('decrement', 'Decrement')],
        string='Type', default='increment')
    confirm_date = fields.Datetime(string="Confirmed Date")
    confirm_uid = fields.Many2one("res.users", string="Confirmed User")
    approve_date = fields.Datetime(string="Approved Date")
    approve_uid = fields.Many2one("res.users", string="Approved User")
    applied_date = fields.Datetime(string="Applied Date")
    applied_uid = fields.Many2one("res.users", string="Applied User")

    effective_date = fields.Date(string="Effective Date")
    state = fields.Selection(
        [('draft', 'Draft'),
         ('confirm', 'Confirm'),
         ('approved', 'Approved'),
         ('applied', 'Applied in Contract'),
         ('cancel', 'Rejected')],
        string='Status', default='draft')
    hr_contract_update_line_ids = fields.One2many('hr.contract.update.line', 'hr_contract_update_id')
    total_gross_salary = fields.Float(string='Total Current Gross Salary', compute='_compute_total_amt')
    total_amount = fields.Float(string='Total Increment/Decrement Amount', compute='_compute_total_amt')
    total_new_gross_salary = fields.Float(string='Total New Gross Salary', compute='_compute_total_amt')
    next_increment_date = fields.Date(string='Next Increment Date')
    yearly_increment = fields.Boolean(string='Yearly Increment?', default=False)
    is_salary_review = fields.Boolean(string='Salary Review?', default=False)

    calculation_based_on = fields.Selection(
        [('gross', 'Gross'),
         ('basic', 'Basic')],
        string='Calculation Based on', default='gross', required=True)

    _sql_constraints = [
        ('unique_employee_name', 'unique (name)', 'Name should not be same!')]

    def action_confirmation(self):
        for rec in self:
            rec.state = 'confirm'
            rec.confirm_date = datetime.now()
            rec.confirm_uid = self.env.uid

    def reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            rec.approve_date = datetime.now()
            rec.approve_uid = self.env.uid

    def apply_contract_update(self):
        for rec in self.hr_contract_update_line_ids:
            rec.employee_id.contract_id.state = 'cancel'
            new_contract = rec.employee_id.contract_id.copy()
            new_contract.date_start = self.effective_date
            new_contract.gross_salary = rec.new_gross_salary
            basic_value = 0
            hra_value = 0
            da_value = 0
            travel_value = 0
            meal_value = 0
            medical_value = 0
            pf_value = 0
            company_pf_value = 0
            festival_bonus_value = 0

            basic_row = self.env['hr.contract.particular.settings'].search([])
            for rec2 in basic_row:
                if rec2.name == 'basic' and (rec2.value > 0 and rec2.value <= 100):
                    basic_value = rec2.value
                elif rec2.name == 'hra' and (rec2.value > 0 and rec2.value <= 100):
                    hra_value = rec2.value
                elif rec2.name == 'da' and (rec2.value > 0 and rec2.value <= 100):
                    da_value = rec2.value
                elif rec2.name == 'travel' and (rec2.value > 0 and rec2.value <= 100):
                    travel_value = rec2.value
                elif rec2.name == 'meal' and (rec2.value > 0 and rec2.value <= 100):
                    meal_value = rec2.value
                elif rec2.name == 'medical' and (rec2.value > 0 and rec2.value <= 100):
                    medical_value = rec2.value
                elif rec2.name == 'pf' and (rec2.value > 0 and rec2.value <= 100):
                    pf_value = rec2.value
                elif rec2.name == 'company_pf' and (rec2.value > 0 and rec2.value <= 100):
                    company_pf_value = rec2.value
                elif rec2.name == 'festival_bonus' and (rec2.value > 0 and rec2.value <= 100):
                    festival_bonus_value = rec2.value

            if basic_value:
                new_contract.wage = round(new_contract.gross_salary * (basic_value / 100))
            if hra_value:
                new_contract.hra = round(new_contract.gross_salary * (hra_value / 100))
            if da_value:
                new_contract.da = round(new_contract.gross_salary * (da_value / 100))
            if travel_value:
                new_contract.travel_allowance = round(new_contract.gross_salary * (travel_value / 100))
            if meal_value:
                new_contract.meal_allowance = round(new_contract.gross_salary * (meal_value / 100))
            if medical_value:
                new_contract.medical_allowance = round(new_contract.gross_salary * (medical_value / 100))
            if pf_value:
                new_contract.pf_deduction = round(new_contract.gross_salary * (pf_value / 100))
            if company_pf_value:
                new_contract.company_pf_contribution = round(new_contract.pf_deduction * (company_pf_value / 100))
            if festival_bonus_value:
                new_contract.festival_bonus = round(new_contract.gross_salary * (festival_bonus_value / 100))

            new_contract.other_allowance = new_contract.gross_salary - (
                    new_contract.wage + new_contract.hra + new_contract.da + new_contract.travel_allowance + new_contract.meal_allowance + new_contract.medical_allowance)

            rec.employee_id.contract_id = new_contract.id
            rec.employee_id.contract_id.state = 'open'

            vals = {
                'employee_id': rec.employee_id.id,
                'type': rec.hr_contract_update_id.type,
                'effective_date': rec.hr_contract_update_id.effective_date,
                'gross_salary': rec.gross_salary,
                'amount': rec.amount,
                'new_gross_salary': rec.new_gross_salary,
                'is_salary_review': self.is_salary_review
            }
            rec.employee_id.increment_decrement_ids = [(0, 0, vals)]

        self.state = 'applied'
        self.applied_date = datetime.now()
        self.applied_uid = self.env.uid

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def _compute_total_amt(self):
        for rec in self:
            total_gross_salary = 0
            total_amount = 0
            total_new_gross_salary = 0
            for line in self.hr_contract_update_line_ids:
                if line.gross_salary:
                    total_gross_salary += line.gross_salary
                if line.amount:
                    total_amount += line.amount
                if line.new_gross_salary:
                    total_new_gross_salary += line.new_gross_salary
            self.total_gross_salary = total_gross_salary
            self.total_amount = total_amount
            self.total_new_gross_salary = total_new_gross_salary

    def action_print(self):
        if self:

            data = {
                'id': self.id,
                'model': 'hr.contract.update',
                'form': self.read()[0],
                'type': self.type
            }
            return self.env.ref('hr_payroll.report_contract_update_list_tmpl').with_context(landscape=True).report_action(
                self, data=data)


class EmployeeContractUpdateLine(models.Model):
    _name = 'hr.contract.update.line'
    _description = "Employee Contract Update Line"
    _rec_name = 'employee_id'

    hr_contract_update_id = fields.Many2one('hr.contract.update', string='HR Contract Update Ref.')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    id_card_no = fields.Char(string="Employee ID")
    department_id = fields.Many2one('hr.department', string="Department")
    job_id = fields.Many2one('hr.job', string="Designation")
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    gross_salary = fields.Float(string='Current Gross Salary')
    basic_salary = fields.Float(string='Current Basic Salary')
    type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage')
    ], required=True, default="fixed", string='Type')
    amount = fields.Float(string='Amount')
    percentage = fields.Float(string='Percentage')
    new_gross_salary = fields.Float(string='New Gross Salary')
    new_basic_salary = fields.Float(string='New Basic Salary')

    @api.onchange('type')
    def _onchange_type(self):
        for rec in self:
            if rec.type == 'fixed':
                rec.percentage=0
                rec.amount = 0
            else:
                rec.amount = 0
                rec._onchange_percentage()

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount:
            if self.amount <= 0:
                self.amount=0
                return {
                    'warning': {
                        'title': "Something bad happened",
                        'message': "Amount can not be zero or negative",
                    }
                }
            else:
                for rec in self:
                    new_gross_salary = 0
                    new_basic_salary = 0
                    if rec.hr_contract_update_id.type == 'increment':
                        if rec.hr_contract_update_id.calculation_based_on == 'gross':
                            if rec.type == 'fixed':
                                new_gross_salary = rec.gross_salary + rec.amount
                            else:
                                amount = (rec.gross_salary * rec.percentage) / 100
                                new_gross_salary = rec.gross_salary + amount
                        else:
                            if rec.type == 'fixed':
                                new_basic_salary = rec.basic_salary + rec.amount
                            else:
                                amount = (rec.basic_salary * rec.percentage) / 100
                                new_basic_salary = rec.basic_salary + amount

                    elif rec.hr_contract_update_id.type == 'decrement':
                        if rec.hr_contract_update_id.calculation_based_on == 'gross':
                            if rec.type == 'fixed':
                                new_gross_salary = rec.gross_salary - rec.amount
                            else:
                                amount = (rec.gross_salary * rec.percentage) / 100
                                new_gross_salary = rec.gross_salary - amount
                        else:
                            if rec.type == 'fixed':
                                new_basic_salary = rec.basic_salary - rec.amount
                            else:
                                amount = (rec.basic_salary * rec.percentage) / 100
                                new_basic_salary = rec.basic_salary - amount

                    rec.new_gross_salary = new_gross_salary
                    rec.new_basic_salary = new_basic_salary

                # for rec in self:
                #     if rec.hr_contract_update_id.type == 'increment':
                #         rec.new_gross_salary = rec.gross_salary + rec.amount
                #     elif rec.hr_contract_update_id.type == 'decrement':
                #         rec.new_gross_salary = rec.gross_salary - rec.amount
                #     else:
                #         rec.new_gross_salary = 0

    @api.onchange('percentage')
    def _onchange_percentage(self):
        if self.percentage:
            if self.percentage <= 0:
                self.amount=0
                return {
                    'warning': {
                        'title': "Something bad happened",
                        'message': "Amount can not be zero or negative",
                    }
                }
            else:
                for rec in self:
                    amount = 0
                    new_gross_salary = 0
                    new_basic_salary = 0
                    if rec.hr_contract_update_id.type == 'increment':
                        if rec.hr_contract_update_id.calculation_based_on == 'gross':
                            amount = (rec.gross_salary * rec.percentage) / 100
                            new_gross_salary = rec.gross_salary + amount
                        else:
                            amount = (rec.basic_salary * rec.percentage) / 100
                            new_basic_salary = rec.basic_salary + amount

                    elif rec.hr_contract_update_id.type == 'decrement':
                        if rec.hr_contract_update_id.calculation_based_on == 'gross':
                            amount = (rec.gross_salary * rec.percentage) / 100
                            new_gross_salary = rec.gross_salary - amount
                        else:
                            amount = (rec.basic_salary * rec.percentage) / 100
                            new_basic_salary = rec.basic_salary - amount

                    rec.amount = amount
                    rec.new_gross_salary = new_gross_salary
                    rec.new_basic_salary = new_basic_salary


    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id:
                rec.id_card_no = rec.employee_id.id_card_no
                rec.department_id = rec.employee_id.department_id.id
                rec.job_id = rec.employee_id.job_id.id
                rec.user_work_location_id = rec.employee_id.user_work_location_id.id
                rec.gross_salary = rec.employee_id.contract_id.gross_salary
                rec.basic_salary = rec.employee_id.contract_id.wage

    @api.constrains('type', 'amount', 'percentage')
    def _check_amount_percentage(self):
        for rec in self:
            if rec.type:
                if rec.type == 'fixed':
                    if rec.amount <= 0:
                        raise ValidationError("Amount must be greater then 0.00")
                else:
                    if rec.percentage <= 0:
                        raise ValidationError("Percentage must be greater then 0%")
