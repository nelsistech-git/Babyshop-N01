# -*- coding: utf-8 -*-

from odoo import models, fields, _
import logging
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class PfProfile(models.Model):
    _name = 'pf.profile'
    _rec_name = 'employee_id'
    _description = 'PF Membership profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ## SELECTION DATA ##
    SALARY_SELECTION = [('basic', 'Basic'), ('gross', 'Gross')]
    ## ENDS HERE ##

    employee_id = fields.Many2one('hr.employee', string="Employee ID", required=True,
                                  domain=[('is_pf_user', '=', False)])
    image = fields.Binary(related="employee_id.image_1920")
    employee_name = fields.Char(related="employee_id.name", string="Employee Name", readonly=True)
    is_pf_user = fields.Boolean(related="employee_id.is_pf_user", readonly=True)
    job_id = fields.Many2one(related="employee_id.job_id", string="Designation", readonly=True)
    tax_identification = fields.Char(string="TAX Identification (TIN)", readonly=True,
                                     related="employee_id.tax_id")  # related="employee_id.tax_identification",
    pf_board_id = fields.Many2one(comodel_name="pf.provident.board", string="Board", index=True, required=True,
                                  domain=[('type', '=', 'pf')])
    pf_percentage = fields.Float('PF Percentage %', related="pf_board_id.pf_percentage", required=True)
    percentage_based_on = fields.Selection(related="pf_board_id.percentage_based_on",
                                           string='Percentage Based On', required=True)
    join_date = fields.Date(related="employee_id.initial_employment_date", string="Joining Date")
    left_date = fields.Date(string="Left Date")
    membership_date = fields.Date(string="Membership Date")
    membership_approve_date = fields.Date(string="Membership Approve Date")
    service_period = fields.Char(string="Service Period", compute="_compute_period")
    membership_period = fields.Char(string="Membership Period", compute="_compute_period")

    employee_current_balance = fields.Float(string='Employee Balance', compute="_compute_pf_balance")
    company_current_balance = fields.Float(string='Company Balance', compute="_compute_pf_balance")
    balance_current = fields.Float(string='Current Balance', compute="_compute_pf_balance")

    is_active = fields.Boolean(string='Active')
    is_interest_free = fields.Boolean(string='Is Profit Free', default=False)
    closed_date = fields.Date(string="Closed Date")


    _sql_constraints = [('unique_employee_id', 'UNIQUE(employee_id)', 'This employee already has a PF Profile.')]

    @staticmethod
    def get_service_length(date):
        service_length_str = '0'
        if date:
            date_diff = relativedelta(fields.Date.today(), date)
            service_length1 = "{y} years, {m} months, {d} days".format(y=date_diff.years, m=date_diff.months,
                                                                       d=date_diff.days)
            service_length2 = date_diff.months + (12 * date_diff.years)  # months
            service_length_str = str(service_length1) + ' [' + str(service_length2) + ' months]'

        return str(service_length_str)

    def _compute_period(self):
        for record in self:
            record.service_period = record.get_service_length(record.join_date)
            record.membership_period = record.get_service_length(record.membership_date)

    def _compute_pf_balance(self):
        current_date = fields.Date.today()
        pf_obj = self.env['hr.employee.pf']
        for record in self:
            balance_data = pf_obj._get_pf_emp_balance(current_date, record.employee_id)
            pf_amt = 0
            cpf_amt = 0
            if balance_data:
                pf_amt = balance_data['salary_pf'] + balance_data['profit_pf']
                cpf_amt = balance_data['salary_cpf'] + balance_data['profit_cpf']

            record.employee_current_balance = pf_amt
            record.company_current_balance = cpf_amt
            record.balance_current = pf_amt + cpf_amt


    def toggle_active_archive(self):
        """ Inverse the value of the field ``active`` on the records in ``self``. """
        for record in self:
            record.is_active = not record.is_active


    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "PF of %s" % record.employee_id.name))
        return result

    def create(self, vals):
        res = super(PfProfile, self).create(vals)
        if res and res.employee_id:
            res.employee_id.is_pf_user = True
        return res

    def unlink(self):
        for record in self:
            if record.is_active:
                raise UserError(message="You can not delete any already submitted data.", title="Permission Error")
            record.employee_id.is_pf_user = False
            super(PfProfile, record).unlink()

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
