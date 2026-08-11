from odoo import models, fields, api, _
from datetime import datetime


class ReportingManagerUpdate(models.Model):
    _name = 'hr.reporting.manager'
    _description = "Reporting Manager Update"
    _order = "id desc"
    _rec_name = "user_work_location_id"

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                            domain=[('is_work_loc', '=', True), ('state', '=', 'done')])

    def _default_user(self):
        return self.env['res.users'].search([('id', '=', self.env.user.id)], limit=1)

    requester_id = fields.Many2one('res.users', string='Requester', default=_default_user)
    requested_date = fields.Date(string="Requested Date", default=datetime.now().date(), required=True)

    current_reporting_manager_id = fields.Many2one('hr.employee', 'Current Reporting Manager')
    crm_work_location_id = fields.Many2one('stock.location', 'Work/Job Location',
                                           domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    crm_id_card_no = fields.Char(string="ID Card No")
    crm_department_id = fields.Many2one('hr.department', 'Department')
    crm_designation_id = fields.Many2one('hr.job', 'Designation')
    crm_reporting_manager_id = fields.Many2one('hr.employee', 'Reporting Manager')

    new_reporting_manager_id = fields.Many2one('hr.employee', 'New Reporting Manager')
    nrm_work_location_id = fields.Many2one('stock.location', 'Work/Job Location',
                                           domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    nrm_id_card_no = fields.Char(string="ID Card No")
    nrm_department_id = fields.Many2one('hr.department', 'Department')
    nrm_designation_id = fields.Many2one('hr.job', 'Designation')
    nrm_reporting_manager_id = fields.Many2one('hr.employee', 'Reporting Manager')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm')
    ], string="State", default='draft', copy=False)

    @api.onchange('user_work_location_id')
    def _onchange_user_work_location_id(self):
        if self.user_work_location_id:
            employee_id = self.env['hr.employee'].search(
                [('user_id', '=', self.user_work_location_id.store_manager_id.id)],
                limit=1)
            self.current_reporting_manager_id = employee_id.id
            self.crm_work_location_id = employee_id.user_work_location_id.id
            self.crm_id_card_no = employee_id.id_card_no
            self.crm_department_id = employee_id.department_id.id
            self.crm_designation_id = employee_id.job_id.id
            self.crm_reporting_manager_id = employee_id.parent_id.id

    @api.onchange('new_reporting_manager_id')
    def _onchange_new_reporting_manager_id(self):
        for rec in self:
            if rec.new_reporting_manager_id:
                rec.nrm_work_location_id = rec.new_reporting_manager_id.user_work_location_id.id
                rec.nrm_id_card_no = rec.new_reporting_manager_id.id_card_no
                rec.nrm_department_id = rec.new_reporting_manager_id.department_id.id
                rec.nrm_designation_id = rec.new_reporting_manager_id.job_id.id
                rec.nrm_reporting_manager_id = rec.new_reporting_manager_id.parent_id.id

    def action_confirm(self):
        for rec in self:
            employee_ids = self.env['hr.employee'].search(
                [('user_work_location_id', '=', rec.user_work_location_id.id),
                 ('id', '!=', rec.new_reporting_manager_id.id)])
            rec.user_work_location_id.store_manager_id = rec.new_reporting_manager_id.user_id.id
            for data in employee_ids:
                data.parent_id = rec.new_reporting_manager_id.id
                data.reporting_body = rec.nrm_designation_id.id
            rec.sudo().write({'state': 'confirm'})
