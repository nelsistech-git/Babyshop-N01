from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    #
    # unamapped_attendance_device_ids = fields.Many2many('attendance.device', 'device_employee_rel', 'employee_id', 'device_id',
    #                                                    string='Unmapped Devices',
    #                                                    help='The devices that have not store this employee as an user yet.'
    #                                                    ' When you map employee with a user of a device, the device will disappear from this list.')
    # created_from_attendance_device = fields.Boolean(string='Created from Device', readonly=True, groups="hr.group_hr_user",
    #                                                 help='This field indicates that the employee was created from the data of an attendance device')
    # finger_templates_ids = fields.One2many('finger.template', 'employee_id', string='Finger Template', readonly=True)
    # total_finger_template_records = fields.Integer(string='Finger Templates', compute='_compute_total_finger_template_records')
    # device_user_ids = fields.One2many('attendance.device.user', 'employee_id', string='Mapped Device Users')
    #
    # device_user_id = fields.Char(string='Biometric Device ID', help='The ID Number of the user/employee in the device storage')
    
    attendance_line_ids = fields.One2many(comodel_name='employee.attendance.sheet.line',
                               string='Attendances', readonly=True,
                               inverse_name='employee_id')

    # is_rostering_employee = fields.Boolean(string='Is Rostering Employee?', default=False,
    #                                                 groups="hr.group_hr_user",
    #                                                 help='This field indicates that the employee is applicable for Shift management/Rostering!')

    # def _compute_total_finger_template_records(self):
    #     for r in self:
    #         r.total_finger_template_records = len(r.finger_templates_ids)
    #
    # #custom for employee and DeviceID
    # # def name_get(self):
    # #     result = []
    # #     for record in self:
    # #         name = record.name
    # #         device_user_id = record.device_user_id
    # #         if device_user_id:
    # #             name = "%s [%s]" % (name, device_user_id)
    # #             # name = "%s [%s]" % (name, record.job_id.name)
    # #         result.append((record.id, name))
    # #     return result
    #
    # @api.model_create_multi
    # def create(self, vals_list):
    #     employees = super(HrEmployee, self).create(vals_list)
    #     attendance_device_ids = self.env['attendance.device'].sudo().with_context(active_test=False).search([])
    #     if attendance_device_ids:
    #         employees.write({'unamapped_attendance_device_ids': [(6, 0, attendance_device_ids.ids)]})
    #     return employees
    #
    # def write(self, vals):
    #     # if 'barcode' in vals:
    #     #     DeviceUser = self.env['attendance.device.user'].sudo()
    #     #     for r in self.filtered(lambda emp: emp.barcode):
    #     #         if DeviceUser.search([('employee_id', '=', r.id)], limit=1):
    #     #             raise ValidationError(_("The employee '%s' is currently referred by an attendance device user."
    #     #                                     " Hence, you can not change the Badge ID of the employee") % (r.name,))
    #     if 'device_user_id' in vals:
    #         DeviceUser = self.env['attendance.device.user'].sudo()
    #         for r in self.filtered(lambda emp: emp.device_user_id):
    #             if DeviceUser.search([('employee_id', '=', r.id)], limit=1):
    #                 raise ValidationError(_("The employee '%s' is currently referred by an attendance device user."
    #                                         " Hence, you can not change the Biometric Device ID of the employee") % (r.name,))
    #     return super(HrEmployee, self).write(vals)
    #
    # def _get_unaccent_name(self):
    #     return self.env['to.base'].strip_accents(self.name)
    #
    # def _prepare_device_user_data(self, device):
    #     return {
    #         'uid': device.get_next_uid(),
    #         'name': self._get_unaccent_name() if device.unaccent_user_name else self.name,
    #         'password': '',
    #         'privilege': 0,
    #         'group_id': '0',
    #         'user_id': self.device_user_id,#self.barcode,
    #         'employee_id': self.id,
    #         'device_id': device.id,
    #         }
    #
    # def create_device_user_if_not_exist(self, device):
    #     data = self._prepare_device_user_data(device)
    #     domain = [('device_id', '=', device.id)]
    #     if device.unique_uid:
    #         domain += [('uid', '=', int(data['uid']))]
    #     else:
    #         domain += [('user_id', '=', str(data['user_id']))]
    #     user = self.env['attendance.device.user'].search(domain, limit=1)
    #     if not user:
    #         user = self.env['attendance.device.user'].create(data)
    #     else:
    #         update_vals = {
    #             'employee_id': self.id,
    #             }
    #         if device.unique_uid:
    #             update_vals.update({
    #                 'user_id': self.device_user_id #self.barcode
    #                 })
    #         else:
    #             update_vals.update({
    #                 'uid': int(data['uid'])
    #                 })
    #         user.write(update_vals)
    #     return user
    #
    # def upload_to_attendance_device(self, device):
    #     self.ensure_one()
    #     #if not self.barcode:
    #     if not self.device_user_id:
    #         raise ValidationError(_("Employee '%s' has no Biometric Device ID specified!"))
    #     device_user = self.create_device_user_if_not_exist(device)
    #     device_user.setUser()
    #
    # def action_view_finger_template(self):
    #     action = self.env.ref('custom_zk_attendance_device.action_finger_template')
    #     result = action.read()[0]
    #
    #     # reset context
    #     result['context'] = {}
    #     # choose the view_mode accordingly
    #     total_finger_template_records = self.total_finger_template_records
    #     if total_finger_template_records != 1:
    #         result['domain'] = "[('employee_id', 'in', " + str(self.ids) + ")]"
    #     elif total_finger_template_records == 1:
    #         res = self.env.ref('custom_zk_attendance_device.view_finger_template_form', False)
    #         result['views'] = [(res and res.id or False, 'form')]
    #         result['res_id'] = self.finger_templates_ids.id
    #     return result

class EmployeeAttendanceSheetLine(models.Model):
    _name = 'employee.attendance.sheet.line'
    _description = "Employee Attendance Sheet Line"
    _order = 'date desc'
    
    employee_id = fields.Many2one(comodel_name='hr.employee',
                                   ondelete="cascade",
                                   string='Employee', readonly=True, required=True, index=True)
    emp_card_no = fields.Char(string="Employee ID", related='employee_id.id_card_no')
    user_work_location_id = fields.Many2one('stock.location', string="Work/Job Location", ondelete='restrict',related='employee_id.user_work_location_id', store=True, index=True)
    date = fields.Date("Date", required=True, index=True)
    day = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], 'Day of Week', required=True, index=True)
    
    pl_sign_in = fields.Float("Planned sign in", readonly=True)
    pl_sign_out = fields.Float("Planned sign out", readonly=True)
    work_hours = fields.Float("Work Hours", compute='_compute_work_hours', store=True, readonly=True)
    worked_hours = fields.Float("Worked Hours for OT", readonly=True)
    ac_sign_in = fields.Float("Actual sign in", readonly=True)
    ac_sign_out = fields.Float("Actual sign out", readonly=True)
    overtime = fields.Float("Overtime", readonly=True)
    act_overtime = fields.Float("Actual Overtime", readonly=True)
    late_in = fields.Float("Late In", readonly=True)
    late_in_abs = fields.Float("Late In Abs", default=0, readonly=True)

    diff_time = fields.Float("Diff Time", help="Diffrence between the working time and attendance time(s) ", readonly=True)
    act_late_in = fields.Float("Actual Late In", readonly=True)
    act_diff_time = fields.Float("Actual Diff Time", help="Diffrence between the working time and attendance time(s) ", readonly=True)
    status = fields.Selection(string="Status",
                              selection=[('ab', 'Absence'),
                                         ('weekend', 'Week End'),
                                         ('ph', 'Public Holiday'),
                                         ('leave', 'Leave'), ],
                              required=False, readonly=True)
    note = fields.Text("Note", readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sum', 'Summary'),
        ('confirm', 'Confirmed'),
        ('done', 'Approved')], default='draft')
    
    manual_flag = fields.Integer(string='Manual?', default = 0)
    manual_reason = fields.Text(string='Manual Reason', default='')
    punch_count = fields.Integer(string='Punch Count', default=0)
    manual_absent = fields.Boolean(string='Manual Absent?', default=False, help="Manual Absent?")
    manual_weekend = fields.Boolean(string='Weekend Alter?', default=False, help="Manual Weekend Alter?")
    ovt_flag = fields.Selection([
        ('0', 'Draft'),
        ('1', 'Approved'),
        ('2', 'Rejected'),
        ('3', 'Extra allowance'),
        ('9', 'Working Day'),
    ], string='OT Status', default='0')
    status_uid = fields.Many2one('res.users', string='Update By')
    status_date = fields.Datetime("Update Time")

    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Shift',
                                           help="Employee's working schedule.")
    is_over_ride_day = fields.Boolean(string="Over-Ride Shift", related='resource_calendar_id.is_over_ride_day')

    # def init(self):
    #     self._cr.execute("""CREATE INDEX IF NOT EXISTS lunch_order_user_product_date ON %s (user_id, product_id, date)"""
    #         % self._table)

    @api.depends('ac_sign_in', 'ac_sign_out')
    def _compute_work_hours(self):
        for attendance in self:
            if attendance.ac_sign_out and attendance.ac_sign_in and attendance.employee_id:
                date1 = attendance.date
                ac_sign_in = attendance.ac_sign_in
                ac_sign_out = attendance.ac_sign_out

                try:
                    in_time = timedelta(hours=int(ac_sign_in), minutes=(ac_sign_in * 60) % 60, seconds=00)
                    out_time = timedelta(hours=int(ac_sign_out), minutes=(ac_sign_out * 60) % 60, seconds=00)
                    in_date_time = datetime.strptime(str(date1) + ' ' + str(in_time), '%Y-%m-%d %H:%M:%S')

                    if ac_sign_out < ac_sign_in:
                        date2 = attendance.date + timedelta(days=1)
                    else:
                        date2 = attendance.date
                    out_date_time = datetime.strptime(str(date2) + ' ' + str(out_time), '%Y-%m-%d %H:%M:%S')

                    diff_time = out_date_time - in_date_time
                    worked_hours_float = diff_time.total_seconds() / 3600.0
                    attendance.work_hours = worked_hours_float
                except:
                    attendance.work_hours = False
            else:
                attendance.work_hours = False

    def action_accept_overtime(self):
        for rec in self:
            rec.ovt_flag = '1'
            rec.status_uid = self.env.uid or None
            rec.status_date = fields.Datetime.now()
            if rec.status in ('ph','weekend') and rec.overtime == 0:
                rec.overtime = rec.worked_hours
                rec.act_overtime = rec.worked_hours

    def action_reject_overtime(self):
        for rec in self:
            rec.ovt_flag = '2'
            rec.status_uid = self.env.uid or None
            rec.status_date = fields.Datetime.now()

    def action_set_draft(self):
        for rec in self:
            rec.ovt_flag = '0'

    def action_ot_auto_approve(self):
        common_rows = self.env['custom.common.settings'].sudo().search([('key', '=', 'ot_auto_approve'), ('value', '=', True)], limit=1)
        if common_rows:
            ot_rows = self.env['employee.attendance.sheet.line'].sudo().search([('ovt_flag', '=', '0'), ('overtime', '>', 0)], limit=10000)
            #ot_rows = self.env['employee.attendance.sheet.line'].sudo().search([('ovt_flag', '=', '0'), '|', '&', ('status', 'in', ('ph', 'weekend')), ('punch_count', '=', 1), ('overtime', '>', 0)], limit=1000)
            # status in ('weekend', 'ph') AND main_tbl.worked_hours > 0 AND hap.work_day_without_week_ph = True
            for rec in ot_rows:
                if rec.employee_id.contract_id.is_ot_allowed == True:
                    rec.ovt_flag = '1'
                    rec.status_uid = self.env.uid or None
                    rec.status_date = fields.Datetime.now()
                else:
                    if rec.status in ('ph','weekend'):
                        rec.ovt_flag = '3'
                        rec.status_uid = self.env.uid or None
                        rec.status_date = fields.Datetime.now()
                    else:
                        rec.ovt_flag = '9'
                        rec.status_uid = self.env.uid or None
                        rec.status_date = fields.Datetime.now()


