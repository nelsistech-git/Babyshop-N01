from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta
import base64
from io import BytesIO
from dateutil.relativedelta import relativedelta
import time


class ImportAttendanceDataWizard(models.TransientModel):
    _name = 'import.attendance.data.wizard'
    _description = "Import Attendance Data Wizard"

    device_id = fields.Many2one('attendance.device', string='Device')
    import_type = fields.Selection([('csv', 'CSV')], string='Import Type',
                                   default='csv')
    # , ('excel', 'Excel'), ('txt', 'Text(Copy/Paste)')
    upload_csv_file = fields.Binary(string="Upload File")
    text = fields.Text("Text")
    upload_des = fields.Text(string="Description")

    def action_import_attendance_data(self):
        if not self.upload_csv_file:
            raise UserError("Failed! Required CSV file!")
        else:
            if self.import_type == 'csv':
                user_attendance_obj = self.env['user.attendance']
                att_device_user_obj = self.env['attendance.device.user']
                att_state = self.env['attendance.state'].sudo().search([('code', '=', 255)], limit=1)

                # ---------
                #file_data = base64.decodestring(self.upload_csv_file)
                file_data = base64.b64decode(self.upload_csv_file)
                csv_data = str(file_data.decode("utf-8"))
                row_list = csv_data.split('\n')

                line_count = 0
                import_count = 0
                loop_count = 0

                error_str = ""
                if len(row_list) > 0:
                    line_count = line_count + 1
                    for i in range(len(row_list)):
                        row_no = i + 1
                        rowdata = row_list[i]
                        col_list = rowdata.split(',')
                        if len(col_list) != 2:
                            error_str += "Row-%s: Required All Columns!" % (row_no) + '\n'
                            continue
                        else:
                            att_time_csv = col_list[0]
                            device_user_id = str(col_list[1]).strip()
                            if device_user_id == '' or att_time_csv == '':
                                error_str += "Row-%s: Missing some values!" % (row_no) + '\n'
                                continue
                            else:
                                try:
                                    att_time = datetime.strptime(str(att_time_csv), '%m/%d/%Y %H:%M')
                                    att_datetime = att_time - timedelta(hours=6)
                                except:
                                    try:
                                        att_time = datetime.strptime(str(att_time_csv), '%m/%d/%Y %H:%M:%S')
                                        att_datetime = att_time - timedelta(hours=6)
                                    except:
                                        error_str += "Row-%s: Invalid Date time!" % (row_no) + '\n'
                                        continue

                                # -------------- check employee
                                user_work_location_id = None
                                emp_obj = self.env['hr.employee'].sudo().search(
                                    [('device_user_id', '=', device_user_id)], limit=1)
                                if emp_obj:
                                    emp_name = emp_obj.name
                                    emp_id = emp_obj.id
                                    user_work_location_id = emp_obj.user_work_location_id.id if emp_obj.user_work_location_id else None
                                else:
                                    emp_name = 'NN-%s' % device_user_id
                                    emp_id = None

                                # -------- Attendance device
                                device_id = self.device_id.id
                                device_user_obj = att_device_user_obj.sudo().search(
                                    [('device_id', '=', device_id), ('user_id', '=', device_user_id)], limit=1)
                                if not device_user_obj:
                                    device_user_obj = att_device_user_obj.sudo().create({
                                        'name': emp_name,
                                        'uid': device_user_id,  # device user rec/row unique id
                                        'user_id': device_user_id,
                                        'employee_id': emp_id,
                                        'device_id': device_id,
                                        'group_id': 0,
                                        'del_user': False
                                    })
                                    att_device_user_id = device_user_obj.id

                                else:
                                    att_device_user_id = device_user_obj.id
                                    # ---------
                                    write_val = {}
                                    is_write = False
                                    if device_user_obj.name != emp_name:
                                        write_val['name'] = emp_name
                                        is_write = True
                                    device_emp_id = device_user_obj.employee_id.id if device_user_obj.employee_id else None
                                    if device_emp_id != emp_id:
                                        write_val['employee_id'] = emp_id
                                        is_write = True
                                    if is_write:
                                        device_user_obj.sudo().write(write_val)

                                # ----------- user attendance
                                user_attendance_row = user_attendance_obj.sudo().search(
                                    [('timestamp', '=', att_datetime), ('user_id', '=', att_device_user_id)], limit=1)
                                if user_attendance_row:
                                    error_str += "Row-%s: Same data already exists!" % (row_no) + '\n'
                                    continue
                                else:
                                    vals = {
                                        'timestamp': att_datetime,
                                        'user_id': att_device_user_id,
                                        'status': att_state.code,
                                        'attendance_state_id': att_state.id,
                                        'attendance_type': '20',
                                        'valid': True,
                                        'employee_id': emp_id,
                                        'user_work_location_id': user_work_location_id,
                                        'device_id': device_id,
                                    }
                                    user_attendance_obj.sudo().create(vals)
                                    import_count = import_count + 1

                                    loop_count += 1
                                    if loop_count == 1000:
                                        time.sleep(1)
                                        loop_count = 0
                else:
                    raise UserError('Upload data not available!')

                upload_des = 'Total Rows: ' + str(line_count) + '\nImport Rows: ' + str(
                    import_count) + '\nError:\n' + str(
                    error_str)
                self.upload_des = upload_des

                return {
                    'name': _('Import Attendance Data'),
                    'context': self.env.context,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'import.attendance.data.wizard',
                    'res_id': self.id,
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }

    def action_sample_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/custom_zk_attendance_device/static/attendance_upload_sample.csv',
            'target': 'self',
        }

    def x_action_import_attendance_data(self):
        if not self.upload_csv_file:
            raise UserError("Failed! Required CSV file!")
        else:
            if self.import_type == 'csv':
                lines = []
                file_data = base64.decodestring(self.upload_csv_file)
                csv_data = str(file_data.decode("utf-8"))
                csv_data = csv_data.split('\n')
                for csv_line in csv_data:
                    if csv_line:
                        lines.append(csv_line.split(','))
                # lines.pop(0)
                line_count = len(lines)

                user_attendance_obj = self.env['user.attendance']

                article_count = 0
                error_str = ""
                row_no = 1
                if len(lines) > 0:
                    for i in range(len(lines)):
                        row_no = row_no + 1
                        rowdata = lines[i]
                        datetime_row = rowdata[0].split()
                        print(datetime_row[0][6:])
                        y = int(datetime_row[0][6:])
                        m = int(datetime_row[0][0:2])
                        d = int(datetime_row[0][3:5])
                        h = int(datetime_row[1][0:2])
                        min = int(datetime_row[1][3:5])
                        s = int(datetime_row[1][6:])
                        att_datetime = date(y, m, d) + relativedelta(hours=h - 6, minutes=min, seconds=s)
                        print(att_datetime)
                        # att_datetime = datetime.strptime(str(rowdata[0]), '%m/%d/%Y %H:%M:%S').strftime(
                        #     '%d-%m-%Y %H:%M:%S')
                        # rint

                        if len(rowdata) != 2:
                            raise UserError(
                                'Required All Columns')
                        else:
                            if rowdata[0] == '' or rowdata[1] == '':
                                error_str += "Row-%s: Missing some values!" % (row_no) + '\n'
                                continue
                            else:
                                # try:
                                if rowdata[1] != '':
                                    user_attendance_row = user_attendance_obj.search(
                                        ['|', ('timestamp', '=', att_datetime), ('user_id', '=', rowdata[1])],
                                        limit=1)
                                else:
                                    user_attendance_row = False
                                if user_attendance_row:
                                    error_str += "Row-%s: %s already exists!" % (row_no, rowdata[1]) + '\n'
                                    continue
                                else:
                                    device_id = self.device_id
                                    device_user = rowdata[1]
                                    att_state = self.env['attendance.state'].search([('code', '=', 255)], limit=1)
                                    emp_id = self.env['hr.employee'].search([('device_user_id', '=', rowdata[1])],
                                                                            limit=1)
                                    device_user_obj = self.env['attendance.device.user'].search(
                                        [('user_id', '=', rowdata[1]), ('device_id', '=', device_id.id)], limit=1)
                                    # create device users
                                    if not device_user_obj:
                                        if emp_id:
                                            name = emp_id.name
                                        else:
                                            name = 'NN-%s' % device_user
                                        device_user_obj = self.env['attendance.device.user'].create({
                                            'name': name,
                                            'uid': row_no - 1,
                                            'user_id': device_user,
                                            'employee_id': emp_id.id,
                                            'device_id': device_id.id,
                                            'group_id': 0,
                                            'del_user': False,
                                        })
                                    vals = {
                                        'timestamp': att_datetime,
                                        'user_id': device_user_obj.id,
                                        'status': att_state.code,
                                        'attendance_state_id': att_state.id,
                                        'attendance_type': '20',
                                        'valid': True,
                                        'employee_id': emp_id.id,
                                        'user_work_location_id': emp_id.user_work_location_id.id,
                                        'device_id': device_id.id,
                                    }
                                    user_attendance_obj = user_attendance_obj.create(vals)
                                # except:
                                #     continue
                else:
                    raise UserError('No User Attendance Data to Upload!')

                return {
                    'name': _('Import Attendance Data'),
                    'context': self.env.context,
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'import.attendance.data.wizard',
                    'res_id': self.id,
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }
