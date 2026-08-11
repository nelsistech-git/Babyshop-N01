from odoo import fields, models, api


class HrEmployeeInheritedHrPayroll(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    slip_ids = fields.One2many('hr.payslip', 'employee_id', string='Payslips', readonly=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count',
                                   groups="hr_payroll.group_hr_payroll_user")
    registration_number = fields.Char('Registration Number of the Employee', groups="hr.group_hr_user", copy=False)
    increment_decrement_ids = fields.One2many('employee.increment.decrement.history', 'employee_id', string="Increment/Decrement History")

    _sql_constraints = [
        ('unique_registration_number', 'UNIQUE(registration_number, company_id)',
         'No duplication of registration numbers is allowed')
    ]

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)

    def generate_work_entries(self, date_start, date_stop):
        date_start = fields.Date.to_date(date_start)
        date_stop = fields.Date.to_date(date_stop)

        if self:
            current_contracts = self._get_contracts(date_start, date_stop, states=['open', 'close'])
        else:
            current_contracts = self._get_all_contracts(date_start, date_stop, states=['open', 'close'])

        return bool(current_contracts._generate_work_entries(date_start, date_stop))
    def write(self, vals):
        result = super(HrEmployeeInheritedHrPayroll, self).write(vals)
        #print(vals)
        contract_flag = self.env.context.get("contract_flag") or False
        if contract_flag == False:
            if vals.get('disbursement_type'):
                if self.contract_id:
                    self.contract_id.with_context(emp_flag=True).write({'disbursement_type': self.disbursement_type})

        if vals.get('department_id'):
            if self.contract_id:
                self.contract_id.write({'department_id': self.department_id.id})
        if vals.get('job_id'):
            if self.contract_id:
                self.contract_id.write({'job_id': self.job_id.id})

        return result


class EmployeeIncrementDecrementHistory(models.Model):
    """ Model to keep record of employee Promotion and or demotion history """

    _name = 'employee.increment.decrement.history'
    _description = 'Employee Increment/Decrement History'

    employee_id = fields.Many2one('hr.employee', string='Employee Name', required=True)
    type = fields.Selection(
        [('increment', 'Increment'), ('decrement', 'Decrement')],
        string='Type', default='increment')
    effective_date = fields.Date(string="Effective Date")
    gross_salary = fields.Float(string='Gross Salary')
    amount = fields.Float(string='Amount')
    new_gross_salary = fields.Float(string='New Gross Salary')
    new_basic_salary = fields.Float(string='New Basic Salary')
    is_salary_review = fields.Boolean(string='Salary Review?', default=False)

