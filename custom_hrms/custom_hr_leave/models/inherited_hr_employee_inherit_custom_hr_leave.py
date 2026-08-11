from datetime import datetime, date
from odoo import fields, models

class HrEmployeeBaseCustomHrLeave(models.AbstractModel):
    _inherit = "hr.employee.base"

    current_leave_state = fields.Selection(selection_add=[
            ('confirm2', 'Department approved'),
            ('confirm3', 'HR approved'),
        ])

class InheritedHrEmployeeInheritCustomHrLeave(models.Model):
    _inherit = 'hr.employee'

    def auto_leave_allocation(self, employee_id=None, yearly_allocation=False):
        leave_types = self.env['hr.leave.type'].sudo().search([('is_auto_allocate', '=', True), ('year', '=', str(date.today().year))])
        if not leave_types:
            return False

        leave_allocation_obj = self.env['hr.leave.allocation'].sudo()

        domain = []

        if employee_id:
            domain = domain + [('id', '=', employee_id)]
        else:
            domain = domain + ['|', ('employee_type_id.is_probation', '=', True), ('employee_type_id.is_permanent', '=', True)]

        emp_obj = self.env['hr.employee'].sudo().search(domain)

        if yearly_allocation:
            for emp in emp_obj:
                for lt in leave_types:
                    if lt.is_allow_probation == False:
                        if emp.employee_type_id.is_probation:
                            continue
                    if lt.is_female_only == True:
                        if emp.gender != 'female':
                            continue

                    #-----------
                    auto_allocate_days = int(lt.auto_allocate_days)
                    today_year_firstday = date(date.today().year, 1, 1)
                    today_year_last = date(date.today().year, 12, 31)
                    if lt.auto_allocate_based_on == 'join_date':
                        emp_date = emp.initial_employment_date
                    else:
                        if emp.date_of_confirmation:
                            emp_date = emp.date_of_confirmation
                        else:
                            continue

                    if emp_date <= today_year_firstday:
                        allocate_count = auto_allocate_days
                    elif emp_date > today_year_last:
                        continue
                    else:
                        day_count = (date(date.today().year, 12, 31) - emp_date).days + 1
                        allocate_count = (auto_allocate_days * day_count) / 365

                    leave_alloc_check = leave_allocation_obj.search([('employee_id', '=', emp.id), ('holiday_status_id', '=', lt.id), ('state', '=', 'validate')], limit=1)
                    if not leave_alloc_check:
                        vals = {
                            'name': lt.display_name,
                            'holiday_type': 'employee',
                            'holiday_status_id': lt.id,
                            'allocation_type': 'regular',
                            'employee_id': emp.id,
                            'number_of_days': int(allocate_count)
                        }
                        leave_alloc = leave_allocation_obj.create(vals)
                        leave_alloc.sudo().action_validate()
                    else:
                        continue
        else:
            for emp in emp_obj:
                for lt in leave_types:
                    if lt.is_allow_probation == False:
                        if emp.employee_type_id.is_probation:
                            continue
                    if lt.is_female_only == True:
                        if emp.gender != 'female':
                            continue
                    #--------------------

                    leave_alloc_check = leave_allocation_obj.search([('employee_id', '=', emp.id), ('holiday_status_id', '=', lt.id), ('state', '=', 'validate')], limit=1)
                    if not leave_alloc_check:
                        auto_allocate_days = int(lt.auto_allocate_days)

                        today_year_firstday = date(date.today().year, 1, 1)
                        today_year_last = date(date.today().year, 12, 31)
                        if lt.auto_allocate_based_on == 'join_date':
                            emp_date = emp.initial_employment_date
                            #allocate_count = ((auto_allocate_days * (date(date.today().year, 12, 31) - emp.initial_employment_date).days) + 1) / 365
                        else:
                            if emp.date_of_confirmation:
                                emp_date = emp.date_of_confirmation
                            else:
                                continue
                            #allocate_count = ((auto_allocate_days * (date(date.today().year, 12, 31) - emp.date_of_confirmation).days) + 1) / 365

                        if emp_date <= today_year_firstday:
                            allocate_count = auto_allocate_days
                        elif emp_date > today_year_last:
                            continue
                        else:
                            day_count = (date(date.today().year, 12, 31) - emp_date).days + 1
                            allocate_count = (auto_allocate_days * day_count)/365

                        #----------
                        vals = {
                            'name': lt.display_name,
                            'holiday_status_id': lt.id,
                            'holiday_type': 'employee',
                            'allocation_type': 'regular',
                            'employee_id': emp.id,
                            'number_of_days': int(allocate_count)
                        }
                        leave_alloc = leave_allocation_obj.create(vals)
                        leave_alloc.sudo().action_validate()
                    else:
                        continue
    def cron_sync_probation_to_permanent(self):
        search_rslt = self.env['hr.employee'].sudo().search(
            [('date_of_confirmation', '<=', datetime.now().date()), ('employee_type_id.is_probation', '=', True)])
        employee_type = self.env['hr.employee.type'].sudo().search([('is_permanent', '=', True)], limit=1)
        users = self.env.ref('hr.group_hr_manager').users

        if users:
            notification_ids = [(0, 0, {
                'res_partner_id': user.partner_id.id,
                'notification_type': 'inbox'
            }) for user in users if users]
        else:
            notification_ids = []

        for rec in search_rslt:
            rec.employee_type_id = employee_type.id

            self.env['mail.message'].sudo().create({
                'message_type': "notification",
                'body': "'%s' has become a permanent employee on %s" % (rec.name, rec.date_of_confirmation),
                'subject': "Permanent Employee Notification",
                'partner_ids': [(4, rec.address_home_id.id)],
                'notification_ids': notification_ids,
                'author_id': self.env.user.partner_id and self.env.user.partner_id.id
            })
            rec.auto_leave_allocation(employee_id=rec.id)

    def action_leave_allocate(self):
        self.auto_leave_allocation(employee_id=self.id)

