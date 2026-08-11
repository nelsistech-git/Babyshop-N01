from odoo import models, fields, api, _


class UserAttendance(models.Model):
    _name = 'user.attendance'
    _description = 'User Attendance'
    _order = 'timestamp DESC, user_id, status, attendance_state_id, device_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    device_id = fields.Many2one('attendance.device', string='Attendance Device', required=True, ondelete='restrict', index=True)
    user_id = fields.Many2one('attendance.device.user', string='Device User', required=True, ondelete='cascade', index=True)
    timestamp = fields.Datetime(string='Timestamp', required=True, index=True)
    status = fields.Integer(string='Device Attendance State', required=True,
                            help='The state which is the unique number stored in the device to'
                            ' indicate type of attendance (e.g. 0: Checkin, 1: Checkout, etc)')
    attendance_state_id = fields.Many2one('attendance.state', string='Attendance State',
                                          help='This technical field is to map the attendance'
                                          ' status stored in the device and the attendance status in Odoo', required=True, index=True)
    activity_id = fields.Many2one('attendance.activity', related='attendance_state_id.activity_id', store=True, index=True)
    hr_attendance_id = fields.Many2one('hr.attendance', string='HR Attendance', ondelete='set null',
                                       help='The technical field to link Device Attendance Data with Odoo\' Attendance Data', index=True)

    type = fields.Selection(string='Activity Type', related='attendance_state_id.type', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related='user_id.employee_id', store=True, index=True)
    valid = fields.Boolean(string='Valid Attendance', index=True, readonly=True, default=False,
                           help="This field is to indicate if this attendance record is valid for HR Attendance Synchronization."
                           " E.g. The Attendances with Check out prior to Check in or the Attendances for users without employee"
                           " mapped will not be valid.")
    
    attendance_type = fields.Selection([('1', 'Finger'),
                                        ('15', 'Face'),
                                        ('2', 'Type_2'),
                                        ('3', 'Password'),
                                        ('4', 'Card'),
                                        ('20', 'Manual'),
                                        ('21', 'SMS'),
                                        ('22', 'App')], string='Category', default='1')
    
    process_flag = fields.Integer(string='Process Flag', default = 0) #0/1, 0=pending,1=done
    
    user_work_location_id = fields.Many2one('stock.location', string="Work/Job Location", ondelete='restrict',related='employee_id.user_work_location_id', store=True, index=True)
    
    _sql_constraints = [
        ('unique_user_id_device_id_timestamp',
         'UNIQUE(user_id, device_id, timestamp)',
         "The Timestamp and User must be unique per Device"),
    ]

    @api.constrains('status', 'attendance_state_id')
    def constrains_status_attendance_state_id(self):
        for r in self:
            if r.status != r.attendance_state_id.code:
                raise(_('Attendance Status conflict! The status number from device must match the attendance status defined in Odoo.'))

    def _update_valid(self):
        # self_sorted = self.sorted('timestamp', reverse=True)
        # all_att = self.env['user.attendance'].search([
        #     ('employee_id', 'in', self.employee_id.ids),
        #     ('timestamp', '<', self_sorted[-1:].timestamp),
        #     ('activity_id', 'in', self.activity_id.ids)])
        for r in self:
            r.valid = True
            # prev_att = all_att.filtered(
            #     lambda att: \
            #         att.employee_id == r.employee_id \
            #         and att.timestamp < r.timestamp \
            #         and att.activity_id == r.activity_id
            #         ).sorted('timestamp')[-1:]
            # if not prev_att:
            #     r.valid = True if r.type == 'checkin' else False
            # else:
            #     r.valid = True if prev_att.type != r.attendance_state_id.type else False

    @api.model_create_multi
    def create(self, vals_list):
        attendances = super(UserAttendance, self).create(vals_list)
        attendances._update_valid()
        return attendances

    # def write(self, vals):
    #     super(UserAttendance, self).write(vals)
    #     for rec in self:
    #         for x in rec.user_id:
    #             x.user_id.employee_id = x.user_id.id
    #             x.user_id.employee_id.name = rec.user_id.name

    def reset_attendance_data(self):
        att_obj = self.env["user.attendance"].sudo()
        for hr_att in self:
            hr_att.process_flag = 0

    def js_python_method(self, model_name, active_id):
        pass
