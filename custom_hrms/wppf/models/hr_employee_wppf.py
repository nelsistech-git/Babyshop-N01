from odoo import fields, models, api
from odoo.addons.helper import validator
from odoo.exceptions import ValidationError
import datetime
from datetime import datetime


class InheritedHrEmployeeWPPF(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    is_wppf_user = fields.Boolean(string='Is WPPF User?', default=False, groups="hr.group_hr_user")
    wppf_policy_id = fields.Many2one('wppf.policy', string='WPPF Policy', groups="hr.group_hr_user")
    is_wppf_restricted = fields.Boolean(string='Is WPPF Restricted?', default=False, groups="hr.group_hr_user")
    employee_wppf_ids = fields.One2many('hr.employee.wppf', 'employee_id',
                                        string="Employee WPPF", groups="hr.group_hr_user")
    wppf_settlement_status = fields.Boolean(string="WPPF Final Settlement Status", default=False,
                                            groups="hr.group_hr_user")


class HrEmployeeWPPF(models.Model):
    _name = 'hr.employee.wppf'
    _description = 'HR Employee Provident Fund'
    _order = 'year desc, month desc, employee_id asc'
    _rec_name = 'employee_id'

    def get_years(self):
        """ Get company start year and display_year from res_company """
        year_list = []
        company = self.env.company
        if company.start_date:
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
                                  domain=[('active', '=', True), ('is_wppf_user', '=', True)])
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

    pf_amount = fields.Float(string='WPPF Amount', default=0.0)
    cpf_amount = fields.Float(string='CPF Amount', default=0.0)
    profit_amount = fields.Float(string='Profit Amount', default=0.0)
    total_pf_amount = fields.Float(string='Total WPPF Amount', default=0.0, compute="get_total_pf_amount")
    contribution_type = fields.Selection([('wppf', 'WPPF'), ('profit', 'Profit'), ('forfeiture', 'Forfeiture')],
                                         string='Contribution Type', default='wppf')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('close', 'Closed')
    ], string='State', default='draft')

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
            envobj = self.env['hr.employee.wppf']
            conditionlist = [('employee_id', '=', rec.employee_id.id), ('year', '=', rec.year),
                             ('month', '=', rec.month), ('contribution_type', '=', rec.contribution_type)]
            validator.check_duplicate_value(rec, envobj, conditionlist, msg)

    @api.constrains('pf_amount')
    def _check_pf_amt_constrains(self):
        for rec in self:
            month = dict(self._fields['month'].selection).get(rec.month)
            if rec.pf_amount < 0:
                raise ValidationError('PF Amount must be greater than zero for %s - %s.' % (month, rec.year))

    def _get_wppf_emp_balance(self, date, emp):
        year_month = date.strftime("%Y-%m")
        data_sql1 = """
                SELECT employee_id,
                SUM(CASE WHEN contribution_type = 'wppf' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS wppf_pf,
                SUM(CASE WHEN contribution_type = 'wppf' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS wppf_cpf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS profit_pf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS profit_cpf
                from hr_employee_wppf
                WHERE CONCAT(year,'-',month) <= '{0}' AND employee_id={1} AND state='done'
                GROUP BY employee_id;
            """.format(year_month, emp.id)

        self.env.cr.execute(data_sql1)
        query_res1 = self.env.cr.dictfetchall()

        dict_data = {
            'wppf_pf': 0,
            'wppf_cpf': 0,
            'profit_pf': 0,
            'profit_cpf': 0
        }
        if query_res1:
            dict_data['wppf_pf'] = query_res1[0]['wppf_pf']
            dict_data['wppf_cpf'] = query_res1[0]['wppf_cpf']
            dict_data['profit_pf'] = query_res1[0]['profit_pf']
            dict_data['profit_cpf'] = query_res1[0]['profit_cpf']
        return dict_data

    def _get_wppf_emp_balance_opening(self, date, emp):
        year_month = date.strftime("%Y-%m")
        data_sql1 = """
                SELECT employee_id,
                SUM(CASE WHEN contribution_type = 'wppf' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS wppf_pf,
                SUM(CASE WHEN contribution_type = 'wppf' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS wppf_cpf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(pf_amount, 0) ELSE 0 END) AS profit_pf,
                SUM(CASE WHEN contribution_type = 'profit' THEN COALESCE(cpf_amount, 0) ELSE 0 END) AS profit_cpf
                from hr_employee_wppf
                WHERE CONCAT(year,'-',month) < '{0}' AND employee_id={1}
                GROUP BY employee_id;
            """.format(year_month, emp.id)

        self.env.cr.execute(data_sql1)
        query_res1 = self.env.cr.dictfetchall()

        dict_data = {
            'wppf_pf': 0,
            'wppf_cpf': 0,
            'profit_pf': 0,
            'profit_cpf': 0
        }
        if query_res1:
            dict_data['wppf_pf'] = query_res1[0]['wppf_pf']
            dict_data['wppf_cpf'] = query_res1[0]['wppf_cpf']
            dict_data['profit_pf'] = query_res1[0]['profit_pf']
            dict_data['profit_cpf'] = query_res1[0]['profit_cpf']
        return dict_data

    def _close_emp_wppf(self, date, emp):
        year_month = date.strftime("%Y-%m")
        data_sql1 = """
                UPDATE hr_employee_wppf SET state='close'
                WHERE CONCAT(year,'-',month) <= '{0}' AND employee_id={1};
            """.format(year_month, emp.id)

        self.env.cr.execute(data_sql1)
