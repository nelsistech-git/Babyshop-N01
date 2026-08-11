from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError
from datetime import date

_logger = logging.getLogger(__name__)


class EmployeeRedesignation(models.Model):
    _name = 'update.employee.designation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Update Employee Promotion Demotion Re-designation"
    _order = "id desc"
    _rec_name = "employee_id"

    def _default_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    type = fields.Selection([
        ('promotion', 'Promotion'),
        ('demotion', 'Demotion'),
        ('re_designation', 'Re-designation')
    ], string="Type", default='')
    employee_id = fields.Many2one('hr.employee', string='Employee Name', store=True)
    id_card_no = fields.Char(string="Employee ID")
    company_id = fields.Many2one('res.company', string='Company', store=True)
    location_id = fields.Many2one('stock.location', string='Work/Job Location', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True, string="Previous Department")
    job_position = fields.Many2one('hr.job', string="Previous Designation", store=True)
    to_department_id = fields.Many2one('hr.department', string='New Department', required=True)
    to_designation = fields.Many2one('hr.job', string='New Designation', required=True)
    date_exec = fields.Date(string="Effective Date", required=True, readonly=True)
    initial_employment_date = fields.Date(string='Date of Joining')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string="State", default='draft', tracking=True, copy=False)

    # name = fields.Char(string='Name', copy=False, tracking=True, default=lambda self: _('New'))
    # date_requested = fields.Datetime(string="Requested Date", default=fields.Datetime.now)

    date = fields.Date(string="Date", default=fields.Date.today(), readonly=True)

    @api.onchange('employee_id', 'date_exec')
    def _onchange_field_employee_id(self):
        for record in self:
            if record.employee_id:
                record.company_id = record.employee_id.company_id
                record.id_card_no = record.employee_id.id_card_no
                record.location_id = record.employee_id.user_work_location_id.id
                record.department_id = record.employee_id.department_id.id
                record.job_position = record.employee_id.job_id.id
                record.initial_employment_date = record.employee_id.initial_employment_date

    @api.onchange('to_department_id')
    def _onchange_department(self):
        if self.to_department_id:
            self.to_designation = ""

    def action_confirm(self):
        for records in self:
            # records.name = self.env['ir.sequence'].get('hr_transfer_code')
            records.sudo().write({'state': 'confirm'})

    def action_approved(self):
        for rec in self:
            if rec.date_exec > date.today():
                raise UserError("Update can not be done before effective date")
            update_status = True
            if rec.type == 'promotion':
                rec.employee_id.department_id = rec.to_department_id.id
                rec.employee_id.job_id = rec.to_designation.id
                rec.employee_id.contract_id.department_id = rec.to_department_id.id
                rec.employee_id.contract_id.job_id = rec.to_designation.id

            if rec.type == 'demotion':
                rec.employee_id.department_id = rec.to_department_id.id
                rec.employee_id.job_id = rec.to_designation.id
                rec.employee_id.contract_id.department_id = rec.to_department_id.id
                rec.employee_id.contract_id.job_id = rec.to_designation.id

            if rec.type == 're_designation':
                rec.employee_id.department_id = rec.to_department_id.id
                rec.employee_id.job_id = rec.to_designation.id
                rec.employee_id.contract_id.department_id = rec.to_department_id.id
                rec.employee_id.contract_id.job_id = rec.to_designation.id

            # ------- status update
            # comment-for-upgrade
            # if update_status == True:
            #     self.env['hr.employee.promotion.demotion.history'].create({
            #         'head_id': rec.employee_id.id,
            #         'employee_id': rec.employee_id.id,
            #         'type': rec.type,
            #         'department_id': rec.department_id.id,
            #         'job_position': rec.job_position.id,
            #         'to_department_id': rec.to_department_id.id,
            #         'to_designation': rec.to_designation.id,
            #         'effective_date': rec.date_exec,
            #     })
            #     rec.sudo().write({'state': 'approved'})
            # else:
            #     raise UserError('Update failed!')

    def action_cancel(self):
        for records in self:
            records.sudo().write({'state': 'cancel'})
