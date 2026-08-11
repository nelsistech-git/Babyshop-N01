from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, time as dtime
import time


from odoo import fields, models, api, _


class BatchAttendanceProcessGroup(models.Model):
    _name = 'batch.attendance.process.group'
    _description = 'Batch Attendance Process Group'
    _order = 'name'

    name = fields.Char(string="Group Name", required=True)
    active = fields.Boolean(string="Is Active?", default=True)

class BatchAttendanceProcess(models.Model):
    _name = 'batch.attendance.process'
    _description = 'Batch Attendance Process'
    _rec_name = 'group_id'
    _order = 'sequence'

    sequence = fields.Integer()
    group_id = fields.Many2one(comodel_name='batch.attendance.process.group', string='Device Group', index=True, required=True, ondelete='restrict')
    device_count = fields.Integer(compute='_compute_device_count')
    process_dt = fields.Datetime(string='Last Process Time')
    missing_dt = fields.Date(string='From Manual Date (Start Process/Invalid Delete)')
    missing_dt_end = fields.Date(string='To Manual Date (Start Process/Invalid Delete)')
    process_status = fields.Selection([
        ('0', 'Ready'),
        ('1', 'Running')], default='0',
        string="Process Status")

    att_device_ids = fields.One2many('batch.attendance.process.line', 'head_id', string='Divices')
    note = fields.Text(string="Notes")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed')], default='draft')


    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('%s can be deleted in draft state.') % rec.name)
        return super(BatchAttendanceProcess, self).unlink()

    def _compute_device_count(self):
        for head in self:
            head.device_count = len(head.att_device_ids)

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        self.state = 'confirm'
    def action_refresh(self):
        return True
    def action_stop_process(self):
        self.process_status = '0'

    def action_delete_invalid_data(self):
        date = self.missing_dt
        date2 = self.missing_dt_end
        if not date:
            raise UserError("Required From Manual Date!")
        elif not date2:
            raise UserError("Required To Manual Date!")
        else:
            invalid_data = self.env['user.attendance'].sudo().search([
                ('valid', '=', False),
                ('employee_id', '=', False),
                ('process_flag', '=', 0),
                ('timestamp', '>=', datetime.combine(date, dtime(0, 0, 0))),
                ('timestamp', '<=', datetime.combine(date2, dtime(23, 59, 59)))
            ], order='timestamp ASC')
            for rec in invalid_data:
                rec.sudo().unlink()

    def action_map_employee_process(self):
        if self.process_status == '1':
            return False
        else:
            self.process_status = '1'
            for line in self.att_device_ids:
                line.line_status_map = '0'
            self.env.cr.commit()
            #--------------------- start process
            for line in self.att_device_ids:
                if line.state != 'confirmed':
                    continue
                # attendance download
                try:
                    line.device_id.action_employee_map()
                except:
                    line.line_status_map = '2'
                    continue

                line.last_mapped = datetime.now()
                line.line_status_map = '1'
                self.env.cr.commit()
                time.sleep(2)

            #-------------------- end process
            self.process_status = '0'
            self.env.cr.commit()
            return True

    def action_start_process(self, is_schedule=False):
        if self.process_status == '1':
            return False
        else:
            self.process_status = '1'
            for line in self.att_device_ids:
                line.line_status = '0'
            self.env.cr.commit()
            att_wizard_obj = self.env['attendance.wizard']
            #------------- data download
            for line in self.att_device_ids:
                if line.state != 'confirmed':
                    continue
                # attendance download
                try:
                    line.device_id.action_attendance_download()
                except:
                    line.line_status = '2'
                    continue
                line.last_process = datetime.now()
                line.line_status = '1'
                self.env.cr.commit()
                time.sleep(2)

            #------------- sync attendance
            att_wizard_obj.cron_sync_attendance()
            self.env.cr.commit()

            #------------- policy apply
            att_wizard_obj.cron_process_attendance_policy()
            self.env.cr.commit()

            #------------- missing emp in attendance details
            att_obj = self.env["hr.attendance"].sudo()
            emp_rows = self.env['hr.employee'].sudo().search([], order='id')
            start_date = self.missing_dt
            end_date = self.missing_dt_end

            current_datetime = fields.Datetime.now() + timedelta(hours=6)
            today = current_datetime.date()
            if is_schedule:
                start_date = today
                end_date = today
                self.missing_dt = today
                self.missing_dt_end = today
            else:
                if not start_date or not end_date:
                    start_date = today
                    end_date = today
                    self.missing_dt = today
                    self.missing_dt_end = today

            att_emp_list=[]
            sql = ('''
                    SELECT CONCAT(date,'_',employee_id) as emp_data from employee_attendance_sheet_line
                    WHERE date >= '%s' and date <= '%s';
                ''') % (start_date, end_date)
            self.env.cr.execute(sql)
            data_list = self.env.cr.dictfetchall()
            for res in data_list:
                att_emp_list.append(res['emp_data'])

            for emp in emp_rows:
                delta = timedelta(days=1)
                from_date = start_date
                to_date = end_date

                while from_date <= to_date:
                    c_date = from_date.strftime("%Y-%m-%d")+'_'+str(emp.id)
                    if c_date in att_emp_list:
                        from_date += delta
                        continue
                    else:
                        prcess_date = from_date
                        from_date += delta
                        if not emp.initial_employment_date or emp.initial_employment_date > prcess_date:
                            continue
                        if emp.is_separated:
                            separation_date = emp.separation_date
                            if separation_date and separation_date < prcess_date:
                                continue

                        # ----------
                        att_obj.employee_attendance_data_process(emp, prcess_date, prcess_date, hr_att=None)

                    #------------- end


            #-------------------- end process
            self.process_status = '0'
            self.process_dt = datetime.now()
            self.env.cr.commit()
            return True

class BatchAttendanceProcessLine(models.Model):
    _name = 'batch.attendance.process.line'
    _description = 'batch attendance process line'
    _rec_name = "device_id"
    _order = "device_id"

    head_id = fields.Many2one('batch.attendance.process', string='Batch Attendance Devices', ondelete='cascade', required=True)
    device_id = fields.Many2one('attendance.device', string='Devices', index=True, required=True)
    state = fields.Selection(related="device_id.state")
    device_users_count = fields.Integer(string='Device Users Count',related="device_id.device_users_count")
    mapped_employees_count = fields.Integer(string='Mapped Employee Count',related="device_id.mapped_employees_count")
    device_user_extra = fields.Integer(string='Device Extra Users', compute='_compute_device_user_extra')
    last_attendance_download = fields.Datetime(string='Last Sync.', related="device_id.last_attendance_download")
    map_before_dl = fields.Boolean(string='Is Map Employee Before Download?', related="device_id.map_before_dl")
    total_att_records = fields.Integer(string='Attendance Data', related="device_id.total_att_records")
    last_mapped = fields.Datetime(string='Last Mapped', help="Manually Mapped")
    last_process = fields.Datetime(string='Last Processed', help="Last Download")

    line_status_map = fields.Selection([
        ('0', 'Pending'),
        ('1', 'Done'),
        ('2', 'Failed: Connection/User Issue!')
    ], default='0',
        string="Map Process Status")
    line_status = fields.Selection([
        ('0', 'Pending'),
        ('1', 'Done'),
        ('2', 'Failed: Connection/User Issue!')
    ], default='0',
        string="Process Status")
    def _compute_device_user_extra(self):
        for r in self:
            r.device_user_extra = (r.device_users_count - r.mapped_employees_count)
    @api.constrains('device_id')
    def _check_unique_constraint_device_id(self):
        envobj = self.env['batch.attendance.process.line'].sudo()
        for rec in self:
            if rec.device_id:
                envobjs = envobj.search([('id', '!=', rec.id),('device_id', '=', rec.device_id.id)], limit=1)
                if envobjs:
                    extist_group = envobjs[0].head_id.group_id.name
                    raise ValidationError('Device "%s" already exist in Device Group "%s"' % (rec.device_id.name,extist_group))