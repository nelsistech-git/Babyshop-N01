from datetime import timedelta, date
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError
from datetime import datetime


class InheritedHRLeaveInheritCustomHRLeave(models.Model):
    _inherit = "hr.leave"
    _description = "Inherited HR Leave"

    user_work_location_id = fields.Many2one('stock.location', string='Work/Job Location')
    id_card_no = fields.Char(string="Employee ID Card No", related='employee_id.id_card_no')
    device_user_id = fields.Char(string='Biometric Device ID', related='employee_id.device_user_id')
    leaves_count = fields.Float('Number of Time Off', compute='_compute_allocated_leaves')
    allocation_count = fields.Float('Total number of days allocated.', compute='_compute_allocated_leaves')
    job_id = fields.Many2one('hr.job', string="Designation")

    state = fields.Selection(selection_add=[
        ('cancel', 'Cancelled'),  # YTI This state seems to be unused. To remove
        ('confirm2', 'Department approved'),
        ('confirm3', 'HR approved'),
    ])

    # -------mobile app using
    first_approve_reject = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('pending', 'Pending')
    ], string='1st Approval Status', copy=False, default='pending', help="Pending/Approve/Decline")
    first_approve_reject_id = fields.Many2one('hr.employee', string="1st Approver/Rejecter")

    second_approve_reject = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
        ('pending', 'Pending')
    ], string='2nd Approval Status', copy=False, default='pending', help="Pending/Approve/Decline")
    second_approve_reject_id = fields.Many2one('hr.employee', string="2nd Approver/Rejecter")

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env.user.employee_id

    def _employee_id_domain(self):
        domain = []
        #
        # if not self.employee_id.employee_type_id.is_probation:
        #     domain += [('employee_type_id.is_probation', '!=', True)]

        # if self.holiday_status_id.is_allow_probation == False:
        #     # if self.employee_id.employee_type_id.is_probation:
        #     domain += [('employee_type_id.is_probation', '=', False)]

        if self.env.user.user_work_location_id:
            domain += [('user_work_location_id', '=', self.env.user.user_work_location_id.id)]

        if self.user_has_groups('hr_holidays.group_hr_holidays_user') or self.user_has_groups(
                'hr_holidays.group_hr_holidays_manager') or self.user_has_groups(
            'custom_hr_leave.group_leave_requester'):
            return domain

        if self.user_has_groups('hr_holidays.group_hr_holidays_responsible'):
            return domain + [('leave_manager_id', '=', self.env.user.id)]

        return domain + [('user_id', '=', self.env.user.id)]

    @api.onchange('holiday_status_id')
    def _holiday_status_id(self):
        if self.employee_id and self.holiday_status_id:
            if self.holiday_status_id.is_allow_probation == False:
                if self.employee_id.employee_type_id.is_probation == True:
                    raise UserError(
                        _("Warning! This Employee is not Allowed For This Time Off. ")
                    )

    def _compute_allocated_leaves(self):
        y = datetime.today().year
        start_date = date(y, 1, 1)
        end_date = date(y, 12, 31)
        employee_id = self.employee_id.id
        holiday_status_id = self.holiday_status_id.id

        # leave info sql - allocate, leave
        leave_sql = """
                    SELECT tbl1.emp_id, COALESCE(tbl1.alloc_count, 0) AS alloc_count, COALESCE(tbl2.leave_count, 0) AS leave_count
                    FROM(
                        SELECT hla.employee_id AS emp_id, COALESCE(SUM(hla.number_of_days), 0) AS alloc_count
                        FROM hr_leave_type hlt
                        LEFT JOIN hr_leave_allocation hla ON hla.holiday_status_id = hlt.id
                        WHERE hla.state='validate' AND hlt.active='True' AND hlt.year = '{0}' AND employee_id = {3}
                        AND hlt.id = {4}
                        GROUP BY hla.employee_id
                        ORDER BY hla.employee_id
                        ) tbl1
                    LEFT JOIN (
                        SELECT leave_tbl.emp_id, COALESCE(SUM(hld.leave_no), 0) AS leave_count
                        FROM (
                            SELECT hl.id AS leave_id, hl.employee_id AS emp_id
                            FROM hr_leave hl
                            LEFT JOIN hr_leave_type hlt ON hlt.id = hl.holiday_status_id
                            WHERE hl.state='validate' AND employee_id = {3}
                            AND DATE(hl.request_date_to) BETWEEN '{1}' AND '{2}'
                            AND hlt.id = {4}
                            GROUP BY hl.id, hl.employee_id
                        ) leave_tbl
                        LEFT JOIN hr_leave_details hld ON hld.leave_id = leave_tbl.leave_id
                        WHERE DATE(hld.leave_date) BETWEEN '{1}' AND '{2}'
                        GROUP BY leave_tbl.emp_id
                        ORDER BY leave_tbl.emp_id
                        ) tbl2 ON (tbl2.emp_id = tbl1.emp_id)
                    ORDER BY tbl1.emp_id
                    """.format(y, start_date, end_date, employee_id, holiday_status_id)
        self.env.cr.execute(leave_sql)
        leave_res = self.env.cr.dictfetchall()

        if leave_res:
            self.allocation_count = leave_res[0]['alloc_count']
            self.leaves_count = leave_res[0]['leave_count']
        else:
            self.allocation_count = 0
            self.leaves_count = 0

    def act_hr_employee_holiday_request(self):
        domain = [('holiday_type', '=', 'employee')]

        # holiday_type_obj = self.env['hr.leave.type'].search([('year', '=', datetime.today().year), ('active', '=', True)])

        if self.employee_id:
            domain += [('employee_id', '=', self.employee_id.id), ('holiday_status_id', '=', self.holiday_status_id.id)]

        return {
            'name': _('Time Off Analysis'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.report',
            'view_mode': 'tree,form,pivot',
            'search_view_id': self.env.ref('hr_holidays.view_hr_holidays_filter_report').id,
            'domain': domain,
            'context': {
                'search_default_group_type': True,
                'search_default_year': True,
                'search_default_employee_id': self.employee_id.id
            }
        }

    # @api.onchange('holiday_status_id')
    # def _holiday_status_id(self):
    #     if self.holiday_status_id.is_allow_probation:
    #         # domain += [('employee_type_id.is_probation', '=', True)]
    #         return {'domain': {'employee_id': [('employee_type_id.is_probation', '=', True)]}}
    #     else:
    #         return {'domain': {'employee_id': [('employee_type_id.is_probation', '=', False)]}}

    # @api.onchange('holiday_status_id')
    # def _holiday_status_id(self):
    #     if self.employee_id:
    #         if self.holiday_status_id.is_allow_probation:
    #             return {'domain': {'employee_id': [('employee_type_id.is_probation', '=', True)]}}
    #         else:
    #             return {
    #                 'warning': {
    #                     'title': "Something Went Wrong",
    #                     'message': "This Employee is not Allowed For This Time Off Type",
    #                 }
    #             }

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', index=True, readonly=True, ondelete="restrict", default=_default_employee,
        tracking=True, domain=_employee_id_domain)
    requested_employee_ids = fields.One2many('hr.leave.requested', 'leave_id', string='Requisition Line')

    @api.onchange('holiday_type', 'employee_id')
    def _onchange_emp_id(self):
        if self.holiday_type == 'employee':
            self.user_work_location_id = self.employee_id.user_work_location_id.id
            self.id_card_no = self.employee_id.id_card_no
            self.job_id = self.employee_id.job_id.id

    def _compute_leave_details(self):
        for records in self:
            records.leave_details = self.env['hr.leave.details'].search_count([('leave_id', '=', records.id)])

    leave_details = fields.Integer(string="Leave Details", compute='_compute_leave_details')

    def act_leave_details(self):
        tree_view_id = self.env.ref('custom_hr_leave.view_hr_leave_details_tree').id
        return {
            'name': "Leave Details",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.details',
            'view_mode': 'tree',
            'res_id': False,
            'context': False,
            'target': 'current',
            'domain': [('leave_id', '=', self.id)],
        }

    # @api.onchange('start_date', 'end_date')
    # def _onchange_set_employees(self):
    #     if self.start_date and self.end_date:
    #         emp_ids = self.env['hr.employee'].search(
    #             [('date_of_confirmation', '>=', self.start_date), ('date_of_confirmation', '<=', self.end_date),
    #              ('employee_type', '=', 'probation')])
    #
    #         self.employee_ids = [(6, 0, emp_ids.ids)]

    # @api.onchange('request_date_from_period', 'request_hour_from', 'request_hour_to',
    #               'request_date_from', 'request_date_to',
    #               'employee_id')
    # def _onchange_request_parameters(self):
    #     res = super(InheritedHRLeaveInheritCustomHRLeave, self)._onchange_request_parameters()
    #     self._onchange_emp_id()
    #     self._onchange_requested_employee_ids()
    #     print("--------_onchange_request_parameters-----")
    @api.onchange('request_date_from', 'request_date_to', 'employee_id', 'user_work_location_id', 'department_id')
    def _onchange_requested_employee_ids(self):
        # self._onchange_emp_id()

        self.requested_employee_ids = None
        domain = [('state', 'in', ('validate', 'confirm', 'confirm2', 'confirm3'))]
        # domain = []
        if self.holiday_type == 'employee':
            if self.employee_id:
                domain += [('employee_id', '=', self.employee_id.id), ('department_id', '=', self.department_id.id),
                           ('user_work_location_id', '=', self.user_work_location_id.id)]
            if self.request_date_from:
                domain += ['|', ('date_from', '>=', self.request_date_from), ('date_to', '>=', self.request_date_from)]
            if self.request_date_to:
                domain += ['|', ('date_from', '<=', self.request_date_to), ('date_to', '<=', self.request_date_to)]

            emp_requested = self.env['hr.leave'].sudo().search(domain)

            req_leave_ids = []
            if emp_requested:
                for rec in emp_requested:
                    vals = {
                        'leave_id': self.id,
                        'employee_id': rec.employee_id.id,
                        'request_date_from': rec.request_date_from,
                        'request_date_to': rec.request_date_to,
                    }
                    req_leave_ids.append((0, 0, vals))
                self.requested_employee_ids = req_leave_ids

    @api.model_create_multi
    def create(self, vals):
        rec = super(InheritedHRLeaveInheritCustomHRLeave, self).create(vals)
        for res in rec:
            if res:
                res['user_work_location_id'] = res['employee_id'].user_work_location_id.id or None
                res['id_card_no'] = res['employee_id'].id_card_no or None
                res['job_id'] = res['employee_id'].job_id.id or None

        return rec

    # @api.model_create_multi
    # def create(self, vals_list):
    #     """ Override to avoid automatic logging of creation """
    #     print('--------action_create--------1a---', datetime.now())
    #     if not self._context.get('leave_fast_create'):
    #         leave_types = self.env['hr.leave.type'].browse(
    #             [values.get('holiday_status_id') for values in vals_list if values.get('holiday_status_id')])
    #         mapped_validation_type = {leave_type.id: leave_type.validation_type for leave_type in leave_types}
    #         print('--------action_create--------1b---', datetime.now())
    #
    #         print('--------action_create--------2a---', datetime.now())
    #         for values in vals_list:
    #             employee_id = values.get('employee_id', False)
    #             leave_type_id = values.get('holiday_status_id')
    #             # Handle automatic department_id
    #             print('--------action_create--------2b---', datetime.now())
    #             if not values.get('department_id'):
    #                 values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})
    #
    #             # Handle no_validation
    #             print('--------action_create--------2c---', datetime.now())
    #             if mapped_validation_type[leave_type_id] == 'no_validation':
    #                 values.update({'state': 'confirm'})
    #
    #             # Handle double validation
    #             print('--------action_create--------2d---', datetime.now())
    #             if mapped_validation_type[leave_type_id] == 'both':
    #                 self._check_double_validation_rules(employee_id, values.get('state', False))
    #
    #     holidays = super(HolidaysRequest, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
    #
    #     print('--------action_create--------3a---', datetime.now())
    #     for holiday in holidays:
    #         print('--------action_create--------3b---', datetime.now())
    #         if self._context.get('import_file'):
    #             holiday._onchange_leave_dates()
    #         print('--------action_create--------3c---', datetime.now())
    #         if not self._context.get('leave_fast_create'):
    #             # FIXME remove these, as they should not be needed
    #             print('--------action_create--------3d---', datetime.now())
    #             if employee_id:
    #                 holiday.with_user(SUPERUSER_ID)._sync_employee_details()
    #             print('--------action_create--------3e---', datetime.now())
    #             if 'number_of_days' not in values and ('date_from' in values or 'date_to' in values):
    #                 holiday.with_user(SUPERUSER_ID)._onchange_leave_dates()
    #
    #             # Everything that is done here must be done using sudo because we might
    #             # have different create and write rights
    #             # eg : holidays_user can create a leave request with validation_type = 'manager' for someone else
    #             # but they can only write on it if they are leave_manager_id
    #             holiday_sudo = holiday.sudo()
    #             holiday_sudo.add_follower(employee_id)
    #             print('--------action_create--------3f---', datetime.now())
    #             if holiday.validation_type == 'manager':
    #                 holiday_sudo.message_subscribe(partner_ids=holiday.employee_id.leave_manager_id.partner_id.ids)
    #             print('--------action_create--------3g---', datetime.now())
    #             if holiday.holiday_status_id.validation_type == 'no_validation':
    #                 # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
    #                 holiday_sudo.action_validate()
    #                 holiday_sudo.message_subscribe(
    #                     partner_ids=[holiday_sudo._get_responsible_for_approval().partner_id.id])
    #                 holiday_sudo.message_post(body=_("The time off has been automatically approved"),
    #                                           subtype="mt_comment")  # Message from OdooBot (sudo)
    #                 print('--------action_create--------3h---', datetime.now())
    #             elif not self._context.get('import_file'):
    #                 print('--------action_create--------3i---', datetime.now())
    #                 holiday_sudo.activity_update()
    #     return holidays

    def action_refresh_request(self):
        if not self.user_work_location_id:
            if self.employee_id.user_work_location_id:
                self.user_work_location_id = self.employee_id.user_work_location_id.id
        if not self.job_id:
            if self.employee_id.job_id:
                self.job_id = self.employee_id.job_id.id

        self._onchange_requested_employee_ids()

    def action_approve_dept(self):
        if any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Time off request must be confirmed ("To Approve") in order to approve it.'))

        is_approvar = False
        user_id = self.env.user.id
        super_user = self.env['res.users'].browse(SUPERUSER_ID)
        if self.validation_type == 'no_validation':
            is_approvar = True

        if user_id == super_user.id:
            is_approvar = True
        else:
            responsible = self._get_responsible_for_approval()
            if user_id == responsible.id:
                is_approvar = True
            else:
                responsible_officers = self.holiday_status_id.responsible_ids
                if user_id in responsible_officers.ids:
                    is_approvar = True
                else:
                    if self.user_has_groups('base.group_system') or self.user_has_groups(
                            'hr_holidays.group_hr_holidays_manager'):
                        is_approvar = True

        # is_dept_approval = self.holiday_status_id.is_dept_approval
        # if is_dept_approval:
        #     user_id = self.env.user.id
        #     leave_approval_id = self.employee_id.leave_manager_id and self.employee_id.leave_manager_id.id
        #     emp_parent_id = self.employee_id.parent_id and self.employee_id.parent_id.user_id and self.employee_id.parent_id.user_id.id
        #     if user_id != leave_approval_id:
        #         if user_id != emp_parent_id:
        #             is_approvar = False

        if is_approvar:
            self.state = 'confirm2'
            self.first_approve_reject = 'approve'
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            self.first_approve_reject_id = employee_id and employee_id.id or False
        else:
            raise UserError(_('Invalid Approver of the employee `%s`!') % (self.employee_id.name))

    def action_approve_hr(self):
        if any(holiday.state != 'confirm2' for holiday in self):
            raise UserError(_('Time off request must be confirmed ("Department Approve") in order to approve it.'))

        self.state = 'confirm3'
        self.second_approve_reject = 'approve'
        employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        self.second_approve_reject_id = employee_id and employee_id.id or False

    def action_approve(self):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below
        if any(holiday.state != 'confirm3' for holiday in self):
            raise UserError(_('Time off request must be confirmed ("HR Approve") in order to approve it.'))

        current_employee = self.env.user.employee_id
        self.filtered(lambda hol: hol.validation_type == 'both').write(
            {'state': 'validate1', 'first_approver_id': current_employee.id})

        # Post a second message, more verbose than the tracking message
        # for holiday in self.filtered(lambda holiday: holiday.employee_id.user_id):
        #     holiday.message_post(
        #         body=_('Your %s planned on %s has been accepted') % (holiday.holiday_status_id.display_name, holiday.date_from),
        #         partner_ids=holiday.employee_id.user_id.partner_id.ids)

        # self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
        self.action_validate()
        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        return True

    def action_validate(self):
        res = super(InheritedHRLeaveInheritCustomHRLeave, self).action_validate()
        if res:
            # if self.state=='validate1':
            #     self.action_validate()

            if self.holiday_status_id.exclude_weekends or self.holiday_status_id.exclude_ph:
                start_date = self.request_date_from
                end_date = self.request_date_to
                delta = end_date - start_date

                if self.number_of_days >= 1:
                    leave_no = 1
                else:
                    leave_no = self.number_of_days

                work_days = self.employee_id.contract_id.resource_calendar_id.attendance_ids.mapped('dayofweek')
                if not work_days:
                    raise UserError(_('Required work schedule in employee contract.'))
                else:
                    pass

                emp = self.employee_id
                # -------------
                for i in range(delta.days + 1):
                    day = start_date + timedelta(days=i)

                    exist_data_obj = self.env['hr.leave.details'].sudo().search(
                        [('leave_id', '=', self.id), ('leave_date', '=', day)], limit=1)
                    if not exist_data_obj:
                        is_valid = True
                        if self.holiday_status_id.exclude_weekends:
                            if str(day.weekday()) not in work_days:
                                is_valid = False

                        # --------check ph
                        if is_valid and self.holiday_status_id.exclude_ph:
                            ph_details = self.env['hr.public.holiday.details'].sudo().search(
                                [('holiday_date', '=', day), ('holiday_id.state', '=', 'active')])
                            for rec in ph_details:
                                if not rec.holiday_id.emp_ids:
                                    continue
                                if emp.id in rec.holiday_id.emp_ids.ids:
                                    is_valid = False
                                    break
                        # ---------- create leave
                        if is_valid:
                            self.env['hr.leave.details'].sudo().create({
                                'leave_id': self.id,
                                'leave_date': day,
                                'leave_no': leave_no,
                            })

                    # -------- for attendance process again
                    if day <= date.today():
                        self.env['attendance.reprocess.dates'].sudo().create({
                            'type': 'leave',
                            'employee_id': self.employee_id.id,
                            'date': day,
                        })

            else:
                start_date = self.request_date_from
                end_date = self.request_date_to

                delta = end_date - start_date

                if self.number_of_days >= 1:
                    leave_no = 1
                else:
                    leave_no = self.number_of_days
                for i in range(delta.days + 1):
                    day = start_date + timedelta(days=i)

                    exist_data_obj = self.env['hr.leave.details'].sudo().search(
                        [('leave_id', '=', self.id), ('leave_date', '=', day)], limit=1)
                    if not exist_data_obj:
                        self.env['hr.leave.details'].sudo().create({
                            'leave_id': self.id,
                            'leave_date': day,
                            'leave_no': leave_no,
                        })
                    # att_reprocess_obj = self.env['attendance.reprocess.dates'].search(
                    #     [('employee_id', '=', self.employee_id.id), ('date', '=', day)], limit=1)
                    # if not att_reprocess_obj:
                    if day <= date.today():
                        self.env['attendance.reprocess.dates'].sudo().create({
                            'type': 'leave',
                            'employee_id': self.employee_id.id,
                            'date': day,
                        })
        return res

    # def action_refuse(self):
    #     current_employee = self.env.user.employee_id
    #     if any(holiday.state not in ['draft', 'confirm', 'validate', 'validate1'] for holiday in self):
    #         raise UserError(_('Time off request must be confirmed or validated in order to refuse it.'))
    #
    #     validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
    #     validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
    #     (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
    #     # Delete the meeting
    #     self.mapped('meeting_id').unlink()
    #     # If a category that created several holidays, cancel all related
    #     linked_requests = self.mapped('linked_request_ids')
    #     if linked_requests:
    #         linked_requests.action_refuse()
    #
    #     # Post a second message, more verbose than the tracking message
    #     # for holiday in self:
    #     #     if holiday.employee_id.user_id:
    #     #         holiday.message_post(
    #     #             body=_('Your %s planned on %s has been refused') % (
    #     #             holiday.holiday_status_id.display_name, holiday.date_from),
    #     #             partner_ids=holiday.employee_id.user_id.partner_id.ids)
    #
    #     self._remove_resource_leave()
    #     self.activity_update()
    #     return True

    def action_missing_generate(self):
        if self.holiday_status_id.exclude_weekends:
            start_date = self.request_date_from
            end_date = self.request_date_to

            delta = end_date - start_date

            if self.number_of_days >= 1:
                leave_no = 1
            else:
                leave_no = self.number_of_days

            for i in range(delta.days + 1):
                day = start_date + timedelta(days=i)

                exist_data_obj = self.env['hr.leave.details'].sudo().search(
                    [('leave_id', '=', self.id), ('leave_date', '=', day)], limit=1)
                if not exist_data_obj:
                    work_days = self.employee_id.contract_id.resource_calendar_id.attendance_ids.mapped('dayofweek')
                    if not work_days:
                        raise UserError(_('Required work schedule in employee contract.'))
                    else:
                        if str(day.weekday()) in work_days:
                            self.env['hr.leave.details'].sudo().create({
                                'leave_id': self.id,
                                'leave_date': day,
                                'leave_no': leave_no,
                            })
                # att_reprocess_obj = self.env['attendance.reprocess.dates'].search(
                #         [('employee_id', '=', self.employee_id.id), ('date', '=', day)], limit=1)
                # if not att_reprocess_obj:
                if day <= date.today():
                    self.env['attendance.reprocess.dates'].create({
                        'type': 'leave',
                        'employee_id': self.employee_id.id,
                        'date': day,
                    })

        else:
            start_date = self.request_date_from
            end_date = self.request_date_to

            delta = end_date - start_date

            if self.number_of_days >= 1:
                leave_no = 1
            else:
                leave_no = self.number_of_days

            for i in range(delta.days + 1):
                day = start_date + timedelta(days=i)

                exist_data_obj = self.env['hr.leave.details'].sudo().search(
                    [('leave_id', '=', self.id), ('leave_date', '=', day)], limit=1)
                if not exist_data_obj:
                    self.env['hr.leave.details'].sudo().create({
                        'leave_id': self.id,
                        'leave_date': day,
                        'leave_no': leave_no,
                    })

                # att_reprocess_obj = self.env['attendance.reprocess.dates'].search(
                #     [('employee_id', '=', self.employee_id.id), ('date', '=', day)], limit=1)
                # if not att_reprocess_obj:
                if day <= date.today():
                    self.env['attendance.reprocess.dates'].sudo().create({
                        'type': 'leave',
                        'employee_id': self.employee_id.id,
                        'date': day,
                    })

    def action_refuse(self):
        if self.state == 'confirm2':
            self.first_approve_reject = 'reject'
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            self.first_approve_reject_id = employee_id and employee_id.id or False

        elif self.state == 'confirm3':
            self.second_approve_reject = 'reject'
            employee_id = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            self.second_approve_reject_id = employee_id and employee_id.id or False

        # ----------- Super func
        # res = super(InheritedHRLeaveInheritCustomHRLeave, self).action_refuse()
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['draft', 'confirm', 'confirm2', 'confirm3', 'validate', 'validate1'] for holiday in
               self):
            raise UserError(_('Time off request must be confirmed or validated in order to refuse it.'))

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # Delete the meeting
        self.mapped('meeting_id').unlink()
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()

        # Post a second message, more verbose than the tracking message
        for holiday in self:
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_('Your %s planned on %s has been refused') % (
                        holiday.holiday_status_id.display_name, holiday.date_from),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids)

        self._remove_resource_leave()
        self.activity_update()
        # if res:
        # ----------------------------------- custom func
        start_date = self.date_from.date()
        end_date = self.date_to.date()
        delta = end_date - start_date

        for i in range(delta.days + 1):
            day = start_date + timedelta(days=i)
            exist_data_obj = self.env['hr.leave.details'].sudo().search(
                [('leave_id', '=', self.id), ('leave_date', '=', day)],
                limit=1)
            exist_data_obj.unlink()

            # att_reprocess_obj = self.env['attendance.reprocess.dates'].search(
            #     [('employee_id', '=', self.employee_id.id), ('date', '=', day)], limit=1)
            # if not att_reprocess_obj:
            if day <= date.today():
                self.env['attendance.reprocess.dates'].sudo().create({
                    'type': 'leave',
                    'employee_id': self.employee_id.id,
                    'date': day,
                })
        return True
        # return res

    # ------------ from exclude module
    # def _get_number_of_days_include_weekends(self, date_from, date_to, employee_id):
    #     """ Returns a float equals to the timedelta between two dates given as string."""
    #     if employee_id:
    #         if self.request_unit_half or self.request_unit_hours:
    #             return 0
    #         else:
    #             return abs((date_from - date_to).days)
    #
    # @api.onchange('date_from', 'date_to', 'employee_id', 'holiday_status_id.exclude_weekends')
    # def _onchange_leave_dates(self):
    #     if self.date_from and self.date_to:
    #         if self.holiday_status_id.exclude_weekends:
    #             number_of_days = self._get_number_of_days(self.date_from, self.date_to, self.employee_id.id)['days']
    #             if number_of_days > 0:
    #                 if self.employee_id and self.holiday_status_id.exclude_ph:
    #                     ph_count = self.get_public_holiday_count(self.date_from, self.date_to, self.employee_id,
    #                                                              exclude_weekends=True)
    #                     number_of_days = number_of_days - ph_count
    #                     if number_of_days < 0:
    #                         number_of_days = 0
    #
    #             self.number_of_days = number_of_days
    #         else:
    #             number_of_days = self._get_number_of_days_include_weekends(self.date_from, self.date_to,
    #                                                                        self.employee_id.id)
    #             if number_of_days > 0:
    #                 if self.employee_id and self.holiday_status_id.exclude_ph:
    #                     ph_count = self.get_public_holiday_count(self.date_from, self.date_to, self.employee_id,
    #                                                              exclude_weekends=False)
    #                     number_of_days = number_of_days - ph_count
    #                     if number_of_days < 0:
    #                         number_of_days = 0
    #
    #             self.number_of_days = number_of_days
    #     else:
    #         self.number_of_days = 0
    #
    #
    # @api.depends('number_of_days')
    # def _compute_number_of_hours_display(self):
    #     for holiday in self:
    #         # ----------- for weekend exclude or not
    #         context_data = {'from_leave_request': True,
    #                         'exclude_weekends': False}
    #         if (holiday.holiday_status_id.exclude_weekends or
    #                 not holiday.holiday_status_id):
    #             context_data['exclude_weekends'] = True
    #             # instance = self.with_context(context_data)
    #         # ---------------------------------------------------
    #
    #         calendar = holiday._get_calendar()
    #         if holiday.date_from and holiday.date_to:
    #             # Take attendances into account, in case the leave validated
    #             # Otherwise, this will result into number_of_hours = 0
    #             # and number_of_hours_display = 0 or (#day * calendar.hours_per_day),
    #             # which could be wrong if the employee doesn't work the same number
    #             # hours each day
    #             if holiday.state == 'validate':
    #                 start_dt = holiday.date_from
    #                 end_dt = holiday.date_to
    #                 if not start_dt.tzinfo:
    #                     start_dt = start_dt.replace(tzinfo=UTC)
    #                 if not end_dt.tzinfo:
    #                     end_dt = end_dt.replace(tzinfo=UTC)
    #
    #                 try:
    #                     intervals = calendar.with_context(context_data)._attendance_intervals(start_dt, end_dt,
    #                                                                                           holiday.employee_id.resource_id) \
    #                                 - calendar._leave_intervals(start_dt, end_dt, None)  # Substract Global Leaves
    #                 except:
    #                     intervals = []
    #
    #                 number_of_hours = sum((stop - start).total_seconds() / 3600 for start, stop, dummy in intervals)
    #             else:
    #                 number_of_hours = \
    #                 holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)['hours']
    #             holiday.number_of_hours_display = number_of_hours or (
    #                         holiday.number_of_days * (calendar.hours_per_day or HOURS_PER_DAY))
    #         else:
    #             holiday.number_of_hours_display = 0
    #
    # def get_public_holiday_count(self, date_from, date_to, emp, exclude_weekends):
    #     holiday_count = 0
    #     work_days = emp.contract_id.resource_calendar_id.attendance_ids.mapped('dayofweek')
    #
    #     ph_details = self.env['hr.public.holiday.details'].sudo().search(
    #         [('holiday_date', '>=', date_from), ('holiday_date', '<=', date_to), ('holiday_id.state', '=', 'active')])
    #     for rec in ph_details:
    #         if not rec.holiday_id.emp_ids:
    #             continue
    #         if emp.id in rec.holiday_id.emp_ids.ids:
    #             if exclude_weekends:
    #                 holiday_date = rec.holiday_date
    #                 is_weekend = True
    #                 if str(holiday_date.weekday()) in work_days:
    #                     is_weekend = False
    #
    #                 if is_weekend:
    #                     continue
    #                 else:
    #                     holiday_count += 1
    #             else:
    #                 holiday_count += 1
    #     return holiday_count


class HrLeaveDetails(models.Model):
    _name = "hr.leave.details"
    _description = "HR Leave Details"
    _order = 'leave_id, leave_date'

    leave_id = fields.Many2one('hr.leave', string="Time Off", ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete='cascade', related='leave_id.employee_id')
    leave_date = fields.Date(string='Leave Date')
    leave_no = fields.Float(string='Number of Leave(s)')


class RequestedEmployee(models.Model):
    _name = "hr.leave.requested"
    _description = "HR Leave Requested"

    leave_id = fields.Many2one('hr.leave')
    employee_id = fields.Many2one('hr.employee')
    request_date_from = fields.Date(string='From Date')
    request_date_to = fields.Date(string='To Date')
