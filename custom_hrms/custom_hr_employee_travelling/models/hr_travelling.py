# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployeeTravelling(models.Model):
    _name = 'hr_employee_travelling'
    _description = 'Employee Travelling'

    def get_company_ids(self):
        company_ids = self.env.companies
        return [('id', 'in', company_ids.ids)]

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    designation_id = fields.Many2one('hr.job',
                                     related="employee_id.job_id",
                                     string="Designation", store=True)
    department_id = fields.Many2one('hr.department',
                                    related="employee_id.department_id",
                                    string="Department", store=True)
    company_id = fields.Many2one('res.company', required=True,
                                 # related="employee_id.company_id",
                                 default=lambda self: self.env.company,
                                 domain=get_company_ids,
                                 string="Company", store=True)
    date = fields.Date(string='Submit Date', index=True, copy=False, required=True)
    employee_travelling_line_ids = fields.One2many('hr_employee_travelling_line', 'travel_id',
                                                   string='Travel Program', copy=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('approve', 'Approve'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ], readonly=True, required=True, default='draft', help="State of this Travelling Program")

    def button_confirm(self):
        self.write({
            'state': 'confirm',
        })

    def button_approve(self):
        self.write({
            'state': 'approve',
        })

    def button_done(self):
        self.write({
            'state': 'done',
        })

    def button_cancel(self):
        self.write({
            'state': 'cancel',
        })

    def button_draft(self):
        self.write({
            'state': 'draft',
        })


class HrEmployeeTravellingLine(models.Model):
    _name = 'hr_employee_travelling_line'
    _description = 'hr_employee_travelling_line'

    travel_id = fields.Many2one('hr_employee_travelling', 'Travelling Program', ondelete="cascade")

    travel_date = fields.Date(string='Travel Date', index=True, required=True, copy=False)
    travel_time = fields.Float(string="Time", index=True, copy=False)
    location_from = fields.Char(string="From", required=True, help="From can be maximum 250 characters")
    location_to = fields.Char(string="To", required=True, help="To can be maximum 250 characters")
    purpose_of_visit = fields.Text(string="Purpose of Visit")

    travelling_expense_ids = fields.One2many('hr_employee_travelling_expense', 'travel_line_id',
                                             string='Travel Expenses', copy=True)


class HrEmployeeTravellingExpense(models.Model):
    _name = 'hr_employee_travelling_expense'
    _description = 'hr_employee_travelling_expense'

    travel_line_id = fields.Many2one('hr_employee_travelling_line', 'Travelling Program', ondelete="cascade")

    travel_expense_date = fields.Date(string='Expense Date', required=True, index=True, copy=False)
    location_from = fields.Char(string="From", required=True, help="From can be maximum 250 characters")
    location_to = fields.Char(string="To", required=True, help="To can be maximum 250 characters")

    transport_mode = fields.Char(string="Transport Mode", help="Transport mode can be maximum 100 characters")
    transport_cost = fields.Float(string="Transport Cost")

    lodge = fields.Float(string="Lodge")
    daily_allowance = fields.Float(string="Daily Allowance")
    refreshment = fields.Float(string="Refreshment")
    other_entertainment = fields.Float(string="Other")

    total = fields.Float(string="Total Amount", store=True)

    @api.onchange("transport_cost", "lodge", "daily_allowance", "refreshment", "other_entertainment")
    def _onchange_calc_total(self):
        if self.transport_cost or self.lodge or self.daily_allowance or self.refreshment or self.other_entertainment:
            self.total = (self.transport_cost +
                          self.lodge + self.daily_allowance +
                          self.refreshment + self.other_entertainment)
