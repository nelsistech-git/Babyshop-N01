from odoo import fields, models, api
from odoo.addons.helper import validator
from odoo.exceptions import ValidationError
import datetime
from datetime import datetime
from dateutil.relativedelta import relativedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    is_pf_user = fields.Boolean(string='Is PF User?', default=False, groups="hr.group_hr_user")
    pf_start_date = fields.Date(string="PF Start Date", groups="hr.group_hr_user")

    employee_pf_ids = fields.One2many('hr.employee.pf', 'employee_id',
                                      string="Employee Provident Fund", tracking=True)
    pf_settlement_status = fields.Boolean(string="PF Final Settlement Status", default=False, store=True,
                                          groups="hr.group_hr_user")


class HrEmployeeProvidentFund(models.Model):
    _name = 'hr.employee.pf'
    _description = 'HR Employee Provident Fund'
    _order = 'year desc, month desc, employee_id asc'
    _rec_name = 'employee_id'

    def get_years(self):
        """ Get company start year and display_year from res_company """
        year_list = []
        company = self.env.company
        if company.start_date:
            # start_year = int(str(company.start_date).split("-")[0])
            start_year = company.start_date.year
            if company.display_year:
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
        else:
            if company.display_year:
                start_year = datetime.today().year
                display_years = company.display_year
                for i in range(start_year, start_year + display_years, 1):
                    list_format = '%s' % i, i
                    year_list.append(list_format)
            else:
                list_format = '%s' % datetime.today().year, datetime.today().year
                year_list.append(list_format)
        return year_list

    employee_id = fields.Many2one('hr.employee', string='Employee',
                                  domain=[('active', '=', True), ('is_pf_user', '=', True)])
    partner_id = fields.Many2one('res.partner', string='Private Address', related='employee_id.address_home_id')

    year = fields.Selection(get_years, default=str(datetime.today().year), string='Year', required=True)

    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', required=True)

    pf_amount = fields.Float(string='PF Amount', default=0.0)
    cpf_amount = fields.Float(string='CPF Amount', default=0.0)
    profit_amount = fields.Float(string='Profit Amount', default=0.0)  # not used
    total_pf_amount = fields.Float(string='Total PF Amount', default=0.0, compute="get_total_pf_amount")
    contribution_type = fields.Selection([('salary', 'Salary'), ('profit', 'Profit'), ('forfeiture', 'Forfeiture')],
                                         string='Contribution Type', default='salary')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('close', 'Closed')
    ], string='State', default='draft')

    @api.onchange('employee_id', 'pf_amount')
    def onchange_pf_amount(self):
        if self.employee_id and self.pf_amount > 0:
            cpf_type = self.env.company.cpf_type
            cpf_percentage = self.env.company.cpf_percentage
            cpf_amt = 0
            if cpf_type == 'cpf_pf':
                cpf_amt = round((self.pf_amount * cpf_percentage) / 100, 2)
            elif cpf_type == 'cpf_basic':
                basic = self.employee_id.contract_id.wage
                cpf_amt = round((basic * cpf_percentage) / 100, 2)
            elif cpf_type == 'cpf_gross':
                gross_salary = self.employee_id.contract_id.gross_salary
                cpf_amt = round((gross_salary * cpf_percentage) / 100, 2)

            self.cpf_amount = cpf_amt

        else:
            self.cpf_amount = 0

    def get_total_pf_amount(self):
        for rec in self:
            rec.total_pf_amount = round(rec.pf_amount + rec.cpf_amount + rec.profit_amount, 2)

    def name_get(self):
        res = []
        for record in self:
            res.append((record.id, "%s (%s-%s)" % (
            record.employee_id.name, dict(self._fields['month'].selection).get(record.month), record.year)))
        return res

    @api.constrains('employee_id', 'year', 'month')
    def _check_duplicate_pf(self):
        for rec in self:
            month = dict(self._fields['month'].selection).get(rec.month)
            msg = 'In same period (%s - %s) of %s Type, Employee "%s" PF' % (
            month, rec.year, rec.contribution_type, rec.employee_id.name)
            envobj = self.env['hr.employee.pf']
            conditionlist = [('employee_id', '=', rec.employee_id.id), ('year', '=', rec.year),
                             ('month', '=', rec.month), ('contribution_type', '=', rec.contribution_type)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.constrains('pf_amount')
    def _check_pf_amt_constrains(self):
        for rec in self:
            month = dict(self._fields['month'].selection).get(rec.month)
            if rec.pf_amount < 0:
                raise ValidationError('PF Amount must be greater than zero for %s - %s.' % (month, rec.year))

    def _get_pf_emp_balance(self, date, emp):
        year_month = date.strftime("%Y-%m")
        data_sql1 = """
                SELECT employee_id,
                SUM(CASE WHEN contribution_type = 'salary' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS salary_pf,
                SUM(CASE WHEN contribution_type = 'salary' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS salary_cpf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS profit_pf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS profit_cpf
                from hr_employee_pf
                WHERE CONCAT(year,'-',month) <= '{0}' AND employee_id={1} AND state='done'
                GROUP BY employee_id;
            """.format(year_month, emp.id)

        self.env.cr.execute(data_sql1)
        query_res1 = self.env.cr.dictfetchall()

        dict_data = {
            'salary_pf': 0,
            'salary_cpf': 0,
            'profit_pf': 0,
            'profit_cpf': 0
        }
        if query_res1:
            dict_data['salary_pf'] = query_res1[0]['salary_pf']
            dict_data['salary_cpf'] = query_res1[0]['salary_cpf']
            dict_data['profit_pf'] = query_res1[0]['profit_pf']
            dict_data['profit_cpf'] = query_res1[0]['profit_cpf']
        return dict_data

    def _get_pf_emp_balance_opening(self, date, emp):
        year_month = date.strftime("%Y-%m")
        data_sql1 = """
                SELECT employee_id,
                SUM(CASE WHEN contribution_type = 'salary' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS salary_pf,
                SUM(CASE WHEN contribution_type = 'salary' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS salary_cpf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS profit_pf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS profit_cpf
                from hr_employee_pf
                WHERE CONCAT(year,'-',month) < '{0}' AND employee_id={1}
                GROUP BY employee_id;
            """.format(year_month, emp.id)

        self.env.cr.execute(data_sql1)
        query_res1 = self.env.cr.dictfetchall()

        dict_data = {
            'salary_pf': 0,
            'salary_cpf': 0,
            'profit_pf': 0,
            'profit_cpf': 0
        }
        if query_res1:
            dict_data['salary_pf'] = query_res1[0]['salary_pf']
            dict_data['salary_cpf'] = query_res1[0]['salary_cpf']
            dict_data['profit_pf'] = query_res1[0]['profit_pf']
            dict_data['profit_cpf'] = query_res1[0]['profit_cpf']
        return dict_data

    def _get_eligible_emp_loan_amount(self, date, emp, policy):
        year_month = date.strftime("%Y-%m")
        data_sql1 = """
                SELECT employee_id,
                SUM(CASE WHEN contribution_type = 'salary' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS salary_pf,
                SUM(CASE WHEN contribution_type = 'salary' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS salary_cpf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS profit_pf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS profit_cpf
                from hr_employee_pf
                WHERE CONCAT(year,'-',month) <= '{0}' AND employee_id={1} AND state='done'
                GROUP BY employee_id;
            """.format(year_month, emp.id)

        self.env.cr.execute(data_sql1)
        query_res1 = self.env.cr.dictfetchall()

        dict_data = {
            'salary_pf': 0,
            'salary_cpf': 0,
            'profit_pf': 0,
            'profit_cpf': 0
        }

        salary_pf = 0
        salary_cpf = 0
        profit_pf = 0
        profit_cpf = 0
        if query_res1:
            salary_pf = query_res1[0]['salary_pf']
            salary_cpf = query_res1[0]['salary_cpf']
            profit_pf = query_res1[0]['profit_pf']
            profit_cpf = query_res1[0]['profit_cpf']

        policy_obj = policy
        if policy_obj:
            eligibility_based_on = policy_obj.eligibility_based_on
            service_month = 0
            if eligibility_based_on == 'joining_date':
                if emp.initial_employment_date:
                    start = emp.initial_employment_date
                    end = date
                    difference = relativedelta(end, start)
                    months = difference.months + (12 * difference.years)
                    service_month = months

            elif eligibility_based_on == 'confirmation_date':
                if emp.confirmation_date:
                    start = emp.confirmation_date
                    end = date
                    difference = relativedelta(end, start)
                    months = difference.months + (12 * difference.years)
                    service_month = months
            elif eligibility_based_on == 'pf_membership_date':
                if emp.pf_start_date:
                    start = emp.pf_start_date
                    end = date
                    difference = relativedelta(end, start)
                    months = difference.months + (12 * difference.years)
                    service_month = months

            sal_pf_percentage = 0
            sal_cpf_percentage = 0
            profit_pf_percentage = 0
            profit_cpf_percentage = 0
            policy_line = self.env['pf.configuration.line'].sudo().search(
                [('pf_conf_id', '=', policy_obj.id), ('from_month', '<=', service_month),
                 ('to_month', '>=', service_month)], limit=1)
            if policy_line:
                sal_pf_percentage = policy_line.pf_percentage
                sal_cpf_percentage = policy_line.cpf_percentage
                profit_pf_percentage = policy_line.pf_profit_percentage
                profit_cpf_percentage = policy_line.cpf_profit_percentage

            dict_data['salary_pf'] = round((salary_pf * sal_pf_percentage) / 100, 2)
            dict_data['salary_cpf'] = round((salary_cpf * sal_cpf_percentage) / 100, 2)
            dict_data['profit_pf'] = round((profit_pf * profit_pf_percentage) / 100, 2)
            dict_data['profit_cpf'] = round((profit_cpf * profit_cpf_percentage) / 100, 2)

        return dict_data

    def _get_eligible_emp_pf_settlement_amount(self, date, emp, policy):
        year_month = date.strftime("%Y-%m")
        data_sql1 = """
                SELECT employee_id,
                SUM(CASE WHEN contribution_type = 'salary' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS salary_pf,
                SUM(CASE WHEN contribution_type = 'salary' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS salary_cpf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS profit_pf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS profit_cpf
                from hr_employee_pf
                WHERE CONCAT(year,'-',month) <= '{0}' AND employee_id={1} AND state='done'
                GROUP BY employee_id;
            """.format(year_month, emp.id)

        self.env.cr.execute(data_sql1)
        query_res1 = self.env.cr.dictfetchall()

        dict_data = {
            'salary_pf': 0,
            'salary_cpf': 0,
            'profit_pf': 0,
            'profit_cpf': 0
        }

        salary_pf = 0
        salary_cpf = 0
        profit_pf = 0
        profit_cpf = 0
        if query_res1:
            salary_pf = query_res1[0]['salary_pf']
            salary_cpf = query_res1[0]['salary_cpf']
            profit_pf = query_res1[0]['profit_pf']
            profit_cpf = query_res1[0]['profit_cpf']

        policy_obj = policy
        if policy_obj:
            eligibility_based_on = policy_obj.eligibility_based_on
            service_month = 0
            if eligibility_based_on == 'joining_date':
                if emp.initial_employment_date:
                    start = emp.initial_employment_date
                    end = date
                    difference = relativedelta(end, start)
                    months = difference.months + (12 * difference.years)
                    service_month = months

            elif eligibility_based_on == 'confirmation_date':
                if emp.confirmation_date:
                    start = emp.confirmation_date
                    end = date
                    difference = relativedelta(end, start)
                    months = difference.months + (12 * difference.years)
                    service_month = months

            elif eligibility_based_on == 'pf_membership_date':
                if emp.pf_start_date:
                    start = emp.pf_start_date
                    end = date
                    difference = relativedelta(end, start)
                    months = difference.months + (12 * difference.years)
                    service_month = months

            sal_pf_percentage = 0
            sal_cpf_percentage = 0
            profit_pf_percentage = 0
            profit_cpf_percentage = 0
            policy_line = self.env['pf.configuration.line'].sudo().search(
                [('pf_conf_id', '=', policy_obj.id), ('from_month', '<=', service_month),
                 ('to_month', '>=', service_month)], limit=1)
            if policy_line:
                sal_pf_percentage = policy_line.pf_percentage
                sal_cpf_percentage = policy_line.cpf_percentage
                profit_pf_percentage = policy_line.pf_profit_percentage
                profit_cpf_percentage = policy_line.cpf_profit_percentage

            dict_data['salary_pf'] = round((salary_pf * sal_pf_percentage) / 100, 2)
            dict_data['salary_cpf'] = round((salary_cpf * sal_cpf_percentage) / 100, 2)
            dict_data['profit_pf'] = round((profit_pf * profit_pf_percentage) / 100, 2)
            dict_data['profit_cpf'] = round((profit_cpf * profit_cpf_percentage) / 100, 2)

        return dict_data

    def _close_emp_pf(self, date, emp):
        year_month = date.strftime("%Y-%m")
        data_sql1 = """
                UPDATE hr_employee_pf SET state='close'
                WHERE CONCAT(year,'-',month) <= '{0}' AND employee_id={1};
            """.format(year_month, emp.id)

        self.env.cr.execute(data_sql1)
