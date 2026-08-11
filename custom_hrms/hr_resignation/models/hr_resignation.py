# -*- coding: utf-8 -*-
import datetime
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


date_format = "%Y-%m-%d"
RESIGNATION_TYPE = [('resigned', 'Normal Resignation'),
                    ('fired', 'Fired by the company')]


class HrResignation(models.Model):
    _name = 'hr.resignation'
    _description = 'HR Resignation'
    _inherit = 'mail.thread'
    _rec_name = 'employee_id'

    @api.model
    def _set_domain_employee(self):
        if not self.env.user.has_group('hr.group_hr_user'):
            return [('id', '=', self.env.user.employee_id.id)]
        else:
            return []

    @api.model
    def _get_default_employee(self):
        if self.env.user.employee_id:
            return self.env.user.employee_id.id

    name = fields.Char(string='Separation Reference', copy=False, readonly=True, index=True,
                       default=lambda self: _('New'))
    # employee_id = fields.Many2one('hr.employee', string="Employee", default=lambda self: self.env.user.employee_id.id,
    #                               help='Name of the employee for whom the request is creating')
    employee_id = fields.Many2one('hr.employee', string="Employee", default=lambda self: self._get_default_employee(), domain=_set_domain_employee,
                                  help='Name of the employee for whom the request is creating')

    id_card_no = fields.Char(string="Employee ID")
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id',
                                    help='Department of the employee')
    job_id = fields.Many2one('hr.job', string="Designation")
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    resign_confirm_date = fields.Date(string="Confirmed Date",
                                      help='Date on which the request is confirmed by the employee.',
                                      tracking=True)
    resign_approve_date = fields.Date(string="Approved Date",
                                      help='Date on which the request is confirmed by the manager.',
                                      tracking=True)
    approved_revealing_date = fields.Date(string="Expected Last Day",
                                          help='Date on which the request is confirmed by the manager.',
                                          tracking=True)
    expected_notice_period = fields.Integer(string="Expected Notice Period (days)", default=0)

    joined_date = fields.Date(string="Date of Joining", required=False, readonly=True,
                              related="employee_id.initial_employment_date",
                              help='Joining date of the employee.i.e Start date of the first contract')

    expected_revealing_date = fields.Date(string="Last Working Day",
                                          help='Employee requested date on which he is revealing from the company.')
    reason = fields.Text(string="Reason", help='Specify reason for leaving the company')
    notice_period = fields.Integer(string="Notice Period (days)")
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'), ('approved', 'Approved'), ('cancel', 'Cancelled')],
        string='Status', default='draft', tracking=True)
    resignation_type = fields.Selection(selection=RESIGNATION_TYPE, help="Select the type of resignation: normal "
                                                                         "resignation or fired by the company")
    resignation_type_id = fields.Many2one('hr.separation.type.settings', string='Resignation Type')
    read_only = fields.Boolean(string="check field") #not used
    employee_contract = fields.Char(string="Contract")
    submit_date = fields.Date(string='Submission Date', default=fields.Date.context_today)
    deduction = fields.Integer(string="Deduction (%)")
    gross_salary = fields.Float(string="Gross Salary")
    deduction_of_gross = fields.Float(string="Deduction of Gross Salary")
    attachment_ids = fields.Many2many('ir.attachment', 'separation_attachment_id', string="Document Attachment", help="Attach files here")

    def name_get(self):
        return [(rec.id, "%s: %s" % (rec.name, rec.employee_id.name)) for rec in self]

    @api.onchange('days', 'submit_date', 'expected_revealing_date')
    @api.depends('days')
    def _get_number_of_days(self):
        if self.submit_date and self.expected_revealing_date:
            start_date = self.submit_date
            end_date = self.expected_revealing_date
            d1 = datetime.strptime(str(start_date), "%Y-%m-%d")
            d2 = datetime.strptime(str(end_date), "%Y-%m-%d")
            date_difference = d2 - d1
            self.notice_period = date_difference.days

        for rec in self:
            if rec.notice_period:
                no_of_notice_period = self.env['hr.resignation.notice.period.setting'].sudo().search([('days', '=', self.notice_period)], limit=1)
                for notice in no_of_notice_period:
                    self.deduction = notice.particular
                    #self._onchange_gross_salary()
    @api.onchange('employee_id', 'gross_salary', 'deduction')
    def _onchange_gross_salary(self):
        if self.employee_id:
            self.deduction_of_gross = (self.gross_salary * self.deduction) / 100
        # else:
        #     self.deduction_of_gross = 0

    #@api.onchange('employee_id')
    # @api.depends('employee_id')
    # def _compute_read_only(self):
    #     """ Use this function to check weather the user has the permission to change the employee"""
    #     res_user = self.env['res.users'].search([('id', '=', self._uid)], limit=1)
    #     if res_user.has_group('hr.group_hr_user'):
    #         self.read_only = False
    #     else:
    #         self.read_only = True

    # @api.onchange('employee_id')
    # def set_join_date(self):
    #     self.joined_date = self.employee_id.joining_date if self.employee_id.joining_date else ''

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.user_work_location_id = self.employee_id.user_work_location_id.id if self.employee_id.user_work_location_id else False
            self.department_id = self.employee_id.department_id and self.employee_id.department_id.id or False
            self.id_card_no = self.employee_id.id_card_no
            self.job_id = self.employee_id.job_id.id or False
            self.joined_date = self.employee_id.initial_employment_date or False

    @api.model_create_multi
    def create(self, vals):
        # assigning the sequence for the record
        for val in vals:
            if val.get('name', _('New')) == _('New'):
                val['name'] = self.env['ir.sequence'].next_by_code('hr.resignation') or _('New')
        res = super(HrResignation, self).create(vals)
        return res

    # @api.constrains('employee_id')
    # def check_employee(self):
    #     # Checking whether the user is creating leave request of his/her own
    #     for rec in self:
    #         if not self.env.user.has_group('hr.group_hr_user'):
    #             if rec.employee_id.user_id.id and rec.employee_id.user_id.id != self.env.uid:
    #                 raise ValidationError(_('You cannot create request for other employees'))

    @api.onchange('employee_id')
    def check_request_existence(self):
        # Check whether any resignation request already exists
        for rec in self:
            if rec.employee_id:
                resignation_request = self.env['hr.resignation'].sudo().search([('employee_id', '=', rec.employee_id.id),
                                                                         ('state', 'in', ['confirm', 'approved'])], limit=1)
                if resignation_request:
                    raise ValidationError(_('Already available request in confirmed or approved state for this employee!'))

                contract = self.employee_id.contract_id
                if contract:
                    if contract.state == 'open':
                        rec.employee_contract = contract.name
                        rec.gross_salary = contract.gross_salary
                        rec.notice_period = contract.notice_days
                    else:
                        rec.employee_contract = ''
                        rec.gross_salary = 0
                        rec.notice_period = 0
                else:
                    rec.employee_contract = ''
                    rec.gross_salary = 0
                    rec.notice_period = 0

                # no_of_contract = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)])
                # for contracts in no_of_contract:
                #     if contracts.state == 'open':
                #         rec.employee_contract = contracts.name
                #         rec.gross_salary = contracts.gross_salary
                #         rec.notice_period = contracts.notice_days

    @api.constrains('joined_date')
    def _check_dates(self):
        # validating the entered dates
        for rec in self:
            resignation_request = self.env['hr.resignation'].sudo().search([('employee_id', '=', rec.employee_id.id),
                                                                     ('state', 'in', ['confirm', 'approved'])], limit=1)
            if resignation_request:
                raise ValidationError(_('Already available request in confirmed or approved state for this employee!'))


    def cancel_resignation(self):
        for rec in self:
            rec.state = 'cancel'
    def reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
    def confirm_resignation(self):
        if self.joined_date:
            if self.joined_date >= self.expected_revealing_date:
                raise ValidationError(_('Last working day must be greater than Joining date!'))
            for rec in self:
                rec.state = 'confirm'
                rec.resign_confirm_date = str(datetime.now())

                contract = rec.employee_id.contract_id
                if contract:
                    if contract.state == 'open':
                        rec.employee_contract = contract.name
                        rec.approved_revealing_date = rec.resign_confirm_date + timedelta(days=contract.notice_days)
                        rec.expected_notice_period = contract.notice_days
                    else:
                        rec.approved_revealing_date = rec.expected_revealing_date
        else:
            raise ValidationError(_('Please set joining date for employee'))
    def approve_resignation(self):
        for rec in self:
            if rec.expected_revealing_date and rec.resign_confirm_date:

                # no_of_contract = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id),('state', '=', 'open')], limit = 1)
                # for cont in no_of_contract:
                #     if cont.state == 'open':
                #         rec.employee_contract = cont.name
                #         rec.approved_revealing_date = rec.resign_confirm_date + timedelta(days=cont.notice_days)
                #     else:
                #         rec.approved_revealing_date = rec.expected_revealing_date

                if rec.resignation_type_id:
                    rec.state = 'approved'
                    rec.resign_approve_date = datetime.now().date()
                    rec.employee_id.is_separated = True
                    rec.employee_id.separation_date = rec.expected_revealing_date

                    rec.employee_id.resign_date = rec.expected_revealing_date
                    if rec.resignation_type_id.type == 'resigned':
                        rec.employee_id.resigned = True
                    elif rec.resignation_type_id.type == 'fired':
                        rec.employee_id.fired = True
                else:
                    raise UserError(_('Please enter separation type!'))
            else:
                raise ValidationError(_('Please enter valid dates.'))

    def reject_resignation(self):
        for rec in self:
            rec.state = 'cancel'
            rec.resign_confirm_date = None
            rec.approved_revealing_date = None
            rec.expected_notice_period = 0

            if rec.state == 'approved':
                if rec.employee_id.final_settlement_status:
                    raise UserError('Unable to reject. Already final settlement completed of this employee!')
                else:
                    rec.employee_id.resigned = False
                    rec.employee_id.resign_date = None
                    rec.employee_id.is_separated = False
                    rec.employee_id.separation_date = None

                    rec.employee_id.fired = False
                    rec.employee_id.active = True


    # def update_employee_status(self):
    #     resignation = self.env['hr.resignation'].sudo().search([('state', '=', 'approved')])
    #     for rec in resignation:
    #         if rec.expected_revealing_date <= fields.Date.today() and rec.employee_id.active:
    #             rec.employee_id.active = True
    #             rec.employee_id.resign_date = rec.expected_revealing_date
    #             if rec.resignation_type == 'resigned':
    #                 rec.employee_id.resigned = True
    #             else:
    #                 rec.employee_id.fired = True



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    resign_date = fields.Date('Resign Date', readonly=True, help="Date of the resignation", groups="hr.group_hr_user")
    resigned = fields.Boolean(string="Resigned?", default=False, store=True,
                              help="If checked then employee has resigned", groups="hr.group_hr_user")
    fired = fields.Boolean(string="Fired?", default=False, store=True, help="If checked then employee has fired", groups="hr.group_hr_user")
