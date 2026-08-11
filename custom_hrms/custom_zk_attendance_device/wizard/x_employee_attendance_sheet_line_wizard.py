from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta, time


class EmployeeAttSheetLineWizard(models.TransientModel):
    _name = "employee.attendance.sheet.line.wizard"
    _description = "Employee Attendance Sheet Line Wizard"
    
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location', domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    
    @api.onchange('user_work_location_id', 'department_id')
    def _onchange_employees(self):
        domain = []

        if self.user_work_location_id:
            domain += [('user_work_location_id', '=', self.user_work_location_id.id)]

        if self.department_id:
            domain += [('department_id', '=', self.department_id.id)]

        return {'domain': {
            'employee_id': domain,
        }}

    @api.constrains('start_date', 'end_date')
    def date_constrains(self):
        if self.end_date < self.start_date:
            raise ValidationError(_('Start date cannot be greater than the end date.'))
            
    def generate_attendance(self):
        start_date1 = self.start_date
        end_date1 = self.end_date
        company_id = self.company_id
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id
        
        att_obj = self.env["hr.attendance"].sudo()
        
        domain = []
        if self.user_work_location_id:
            domain.append(('user_work_location_id', '=', user_work_location_id.id))

        if self.department_id:
            domain.append(('department_id', '=', department_id.id))
        
        if self.employee_id:
            domain.append(('id', '=', employee_id.id))

        domain.append(('initial_employment_date', '<=', end_date1))

        emp_rows = self.env['hr.employee'].sudo().search(domain, order='id')
        for emp in emp_rows:
            start_date = start_date1
            end_date = end_date1

            #---------chk joining date
            initial_employment_date = emp.initial_employment_date
            if not initial_employment_date:
                continue
            elif initial_employment_date > end_date:
                continue
            elif initial_employment_date > start_date:
                start_date = initial_employment_date
            #-------------chk separtion date
            if emp.is_separated:
                separation_date = emp.separation_date
                if separation_date and separation_date < start_date:
                    continue
                elif separation_date < end_date:
                    end_date = separation_date

            if start_date > end_date:
                continue

            att_obj.employee_attendance_data_process(emp, start_date, end_date, hr_att=None)

    def delete_attendance(self):
        start_date1 = self.start_date
        end_date1 = self.end_date
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        att_line_obj = self.env["employee.attendance.sheet.line"].sudo()
        domain = []
        domain.append(('date', '>=', start_date1))
        domain.append(('date', '<=', end_date1))
        if self.user_work_location_id:
            domain.append(('employee_id.user_work_location_id', '=', user_work_location_id.id))
        if self.department_id:
            domain.append(('employee_id.department_id', '=', department_id.id))
        if self.employee_id:
            domain.append(('employee_id.id', '=', employee_id.id))

        att_line_rows = att_line_obj.search(domain)
        for line in att_line_rows:
            line.sudo().unlink()


class EmployeeAttProcessWizard(models.TransientModel):
    _name = "employee.attendance.process.wizard"
    _description = "Employee Attendance Process Wizard"

    date = fields.Date(string='Date', default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')])
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Employee')

    @api.onchange('user_work_location_id', 'department_id')
    def _onchange_employees(self):
        domain = []

        if self.user_work_location_id:
            domain += [('user_work_location_id', '=', self.user_work_location_id.id)]

        if self.department_id:
            domain += [('department_id', '=', self.department_id.id)]

        return {'domain': {
            'employee_id': domain,
        }}


    def process_attendance(self):
        date = self.date
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id
        att_obj = self.env["hr.attendance"].sudo()

        invalid_data = self.env['user.attendance'].sudo().search([
            ('valid', '=', False),
            ('employee_id', '=', False),
            ('process_flag', '=', 0),
            ('timestamp', '>=', datetime.combine(date, time(0, 0, 0))),
            ('timestamp', '<=', datetime.combine(date, time(23, 59, 59)))
        ], order='timestamp ASC')
        for rec in invalid_data:
            rec.sudo().unlink()

        #attendance download
        att_wizard_obj = self.env['attendance.wizard']
        att_wizard_obj.cron_download_device_attendance()
        self.env.cr.commit()

        # sync attendance
        att_wizard_obj.cron_sync_attendance()
        self.env.cr.commit()

        # employee with att policy
        domain = []
        domain.append(('initial_employment_date', '<=', date))
        if self.user_work_location_id:
            domain.append(('user_work_location_id', '=', user_work_location_id.id))
        if self.department_id:
            domain.append(('department_id', '=', department_id.id))
        if self.employee_id:
            domain.append(('id', '=', employee_id.id))

        emp_rows = self.env['hr.employee'].sudo().search(domain, order='id')
        for emp in emp_rows:
            # ---------chk joining date
            initial_employment_date = emp.initial_employment_date
            if not initial_employment_date:
                continue

            # -------------chk separtion date
            if emp.is_separated:
                separation_date = emp.separation_date
                if separation_date and separation_date < date:
                    continue

            att_obj.employee_attendance_data_process(emp, date, date, hr_att=None)

    def delete_extra_attendance(self):
        date = self.date
        user_work_location_id = self.user_work_location_id
        department_id = self.department_id
        employee_id = self.employee_id

        att_line_obj = self.env["employee.attendance.sheet.line"].sudo()
        domain = []
        domain.append(('date', '=', date))
        domain.append(('employee_id.active', '=', False))
        if self.user_work_location_id:
            domain.append(('employee_id.user_work_location_id', '=', user_work_location_id.id))
        if self.department_id:
            domain.append(('employee_id.department_id', '=', department_id.id))
        if self.employee_id:
            domain.append(('employee_id.id', '=', employee_id.id))

        att_line_rows = att_line_obj.search(domain)
        for rec in att_line_rows:
            rec.sudo().unlink()