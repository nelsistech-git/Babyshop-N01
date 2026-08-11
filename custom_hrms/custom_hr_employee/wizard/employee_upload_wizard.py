from odoo import exceptions, fields, models, _
from odoo.exceptions import UserError
import base64
import datetime, time


class EmployeeListUploadWizard(models.TransientModel):
    _name = "employee.list.upload.wizard"
    _description = "Employee List Upload Wizard"

    upload_csv_file = fields.Binary(string="Upload File")
    upload_des = fields.Text(string="Description")

    def action_employee_list_upload(self):
        if not self.upload_csv_file:
            raise exceptions.ValidationError("Failed! Required CSV file!")
        else:
            # lines = []
            #file_data = base64.decodestring(self.upload_csv_file) #decodebytes
            file_data = base64.decodebytes(self.upload_csv_file)
            csv_data = str(file_data.decode("utf-8"))
            row_list = csv_data.split('\n')

            line_count = len(row_list)

            # pos_module_obj = self.env['ir.model'].sudo().search([('model', '=', 'pos.order')], limit=1)
            # product_color_obj = self.env['product.color'].sudo()

            employee_obj = self.env['hr.employee'].sudo()
            employee_type_obj = self.env['hr.employee.type'].sudo()
            work_sch_obj = self.env['resource.calendar'].sudo()
            dept_obj = self.env['hr.department'].sudo()
            desig_obj = self.env['hr.job'].sudo()
            location_obj = self.env['stock.location'].sudo()
            hr_contract_obj = self.env['hr.contract'].sudo()

            employee_count = 0
            loop_count = 0
            error_str = ""
            row_no = 1
            if len(row_list) > 0:
                #---------- employee type
                type_list = []
                type_rows = employee_type_obj.search([])
                for trow in type_rows:
                    type_list.append(str(trow.name).strip())
                #------------work schedule
                work_sch_list = []
                work_sch_rows = work_sch_obj.search([])
                for schrow in work_sch_rows:
                    work_sch_list.append(str(schrow.name).strip())
                # ------------dept
                dept_list = []
                dept_obj_rows = dept_obj.search([])
                for deptrow in dept_obj_rows:
                    dept_list.append(str(deptrow.name).strip())
                # ------------desig
                desig_list = []
                desig_rows = desig_obj.search([])
                for desigrow in desig_rows:
                    desig_list.append(str(desigrow.name).strip())
                # ------------work loc
                location_list = []
                location_rows = location_obj.search([('state', '=', 'done')])
                for locationrow in location_rows:
                    location_list.append(str(locationrow.name).strip())

                for i in range(len(row_list)):
                    if i == 0:
                        continue  # it's for 1st row heading
                    row_no = i + 1

                    rowdata = row_list[i]
                    if rowdata == '':
                        continue

                    col_list = rowdata.split(',')

                    if len(col_list) != 23:
                        error_str += "Row-%s: Error: Required 23 column!" % row_no + '\n'
                        continue
                    else:
                        emp_name = col_list[0]
                        emp_id = col_list[1]
                        bio_id = col_list[2]
                        work_email = str(col_list[3]).strip()
                        mobile_p = col_list[4]
                        date_joining = col_list[5]
                        emp_type = col_list[6]
                        work_schedule = col_list[7]

                        dept = col_list[8]
                        designation = col_list[9]
                        emp_cat = col_list[10]
                        guardian_name = col_list[11]
                        date_birth = col_list[12]
                        blood_gr = col_list[13]
                        work_loc = col_list[14]

                        gender = col_list[15]
                        nid_no = col_list[16]
                        tin_no = col_list[17]
                        present_address = col_list[18]
                        permanent_address = col_list[19]
                        last_education = col_list[20]
                        salary_account = col_list[21]
                        gross_salary = col_list[22]
                        try:
                            gross_salary = float(gross_salary)
                            if gross_salary < 0:
                                gross_salary = 0
                        except:
                            gross_salary = 0

                        try:
                            date_joining = datetime.datetime.strptime(str(date_joining), '%Y-%m-%d').date()
                        except:
                            date_joining = None
                            #error_str += "Row-%s: Error: %s invalid joining date!" % (row_no, emp_name) + '\n'
                            #continue

                        try:
                            date_birth = datetime.datetime.strptime(str(date_birth), '%Y-%m-%d').date()
                        except:
                            date_birth = None

                        if mobile_p:
                            mobile_p = str(mobile_p)

                        if emp_name == '' or emp_id == '' or bio_id == '' or work_email == '' or mobile_p == '' or date_joining == '' or emp_type == '' or work_schedule == '':
                            error_str += "Row-%s: Error: Required! EmployeeName, EmployeeID, BiometricDeviceID, Work Email, Mobile (Personal), DateOfJoining(YYYY-MM-DD), EmployeeType, WorkingSchedule!" % row_no + '\n'
                            continue
                        else:
                            if str(mobile_p)[0:2] != '01':
                                error_str += "Row-%s: Error: Invalid Mobile '%s', required start with 01!" % (
                                row_no, emp_name) + '\n'
                                continue

                            if len(mobile_p) !=11:
                                error_str += "Row-%s: Error: Invalid Mobile '%s', required 11 digits!" % (row_no, emp_name) + '\n'
                                continue


                            #try:
                            emp_row = employee_obj.search(['|','|','|', ('id_card_no', '=', emp_id), ('device_user_id', '=', bio_id), ('work_email', '=', work_email), ('contact_no', '=', mobile_p)], limit=1)
                            if emp_row:
                                error_str += "Row-%s: Error: '%s' already exists!" % (row_no, emp_name) + '\n'
                                continue
                            else:
                                #------------emp type
                                if emp_type not in (type_list):
                                    error_str += "Row-%s: Error: invalid Employee Type '%s'!" % (row_no, emp_type) + '\n'
                                    continue
                                else:
                                    emp_type_id = employee_type_obj.search([('name', '=ilike', emp_type)], limit=1).id
                                #--------------work schedule
                                if work_schedule not in (work_sch_list):
                                    error_str += "Row-%s: Error: invalid work schedule '%s'!" % (row_no, work_schedule) + '\n'
                                    continue
                                else:
                                    work_schedule_id = work_sch_obj.search([('name', '=ilike', work_schedule)], limit=1).id
                                # --------------dept
                                dept_id = ''
                                if dept:
                                    if dept not in (dept_list):
                                        error_str += "Row-%s: Error: invalid Department '%s'!" % (row_no, dept) + '\n'
                                        continue
                                    else:
                                        dept_id = dept_obj.search([('name', '=ilike', dept)],
                                                                               limit=1).id
                                # --------------desig
                                designation_id = ''
                                if designation:
                                    if designation not in (desig_list):
                                        error_str += "Row-%s: Error: invalid Designation '%s'!" % (row_no, designation) + '\n'
                                        continue
                                    else:
                                        designation_id = desig_obj.search([('name', '=ilike', designation)], limit=1).id
                                # --------------work loc
                                work_loc_id = ''
                                if work_loc:
                                    if work_loc not in (location_list):
                                        error_str += "Row-%s: Error: invalid Work location '%s'!" % (
                                        row_no, work_loc) + '\n'
                                        continue
                                    else:
                                        work_loc_id = location_obj.search([('state', '=', 'done'), ('name', '=ilike', work_loc)],
                                                                      limit=1).id

                                #---------------
                                if emp_cat:
                                    emp_cat = str(emp_cat).strip().upper()
                                    if emp_cat == 'STAFF':
                                        emp_cat = 'staff'
                                    elif emp_cat == 'WORKER':
                                        emp_cat = 'worker'
                                    else:
                                        emp_cat = ''

                                if blood_gr:
                                    blood_gr = str(blood_gr).strip().upper()
                                    if blood_gr == 'A+':
                                        blood_gr = 'a_pos'
                                    elif blood_gr == 'A-':
                                        blood_gr = 'a_neg'
                                    elif blood_gr == 'B+':
                                        blood_gr = 'b_pos'
                                    elif blood_gr == 'B-':
                                        blood_gr = 'b_neg'
                                    elif blood_gr == 'AB+':
                                        blood_gr = 'ab_pos'
                                    elif blood_gr == 'AB-':
                                        blood_gr = 'ab_neg'
                                    else:
                                        blood_gr = ''

                                if gender:
                                    gender = str(gender).strip().upper()
                                    if gender == 'MALE':
                                        gender = 'male'
                                    elif gender == 'FEMALE':
                                        gender = 'female'
                                    elif gender == 'OTHER':
                                        gender = 'other'
                                    else:
                                        gender = ''

                                vals = {
                                    'name': emp_name,
                                    'id_card_no': emp_id,
                                    'device_user_id': bio_id,
                                    'work_email': work_email,
                                    'contact_no': mobile_p,
                                    'initial_employment_date': date_joining,
                                    'employee_type_id': emp_type_id,
                                    'resource_calendar_id': work_schedule_id,
                                    'department_id': dept_id or None,
                                    'job_id': designation_id or None,
                                    'employee_category': emp_cat,
                                    'guardian_name': guardian_name,
                                    'birthday': date_birth,
                                    'blood_group': blood_gr,
                                    'user_work_location_id': work_loc_id or None,
                                    'gender': gender,
                                    'nid': nid_no,
                                    'tax_id': tin_no,
                                    'present_address': present_address,
                                    'p_address_id': permanent_address,
                                    'education_last': last_education,
                                    's_bank_account_no': salary_account
                                }

                                created_emp = employee_obj.create(vals)
                                #print('employee_obj',created_emp)
                                if created_emp:
                                    #print('employee_obj.contract_id', created_emp.contract_id)
                                    if not created_emp.contract_id:
                                        vals2 = {
                                            'name': created_emp.name,
                                            'employee_id': created_emp.id,
                                            'department_id': created_emp.department_id.id if created_emp.department_id else None,
                                            'job_id': created_emp.job_id.id if created_emp.job_id else None,
                                            'date_start': created_emp.initial_employment_date,
                                            'resource_calendar_id': created_emp.resource_calendar_id.id if created_emp.resource_calendar_id else None,
                                            'gross_salary': gross_salary,
                                            'wage': 0,
                                            'state': 'draft',
                                            'trial_date_end': None
                                        }
                                        #print('vals2', vals2)
                                        created_contract = hr_contract_obj.create(vals2)
                                        if created_contract:
                                            created_emp.contract_id = created_contract.id
                                            #--------
                                            if gross_salary > 0:
                                                created_contract.set_gross_distribution_fnc()

                                employee_count += 1
                                loop_count += 1
                                if loop_count == 100:
                                    time.sleep(1)
                                    loop_count = 0
                            # except:
                            #     error_str += "Row-%s: Error: Possibly it already exists!" % row_no + '\n'
                            #     continue
            else:
                raise UserError('No Employee to Upload!')

            upload_des = 'Total Rows: ' + str(line_count) + '\nImport Rows: ' + str(employee_count) + '\nError:\n' + str(
                error_str)

            self.upload_des = upload_des

            return {
                'name': _('Employee Upload'),
                'context': self.env.context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'employee.list.upload.wizard',
                'res_id': self.id,
                'view_id': False,
                'type': 'ir.actions.act_window',
                'target': 'new',
            }

    def action_sample_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/custom_hr_employee/static/src/employee_upload_sample.csv',
            'target': 'self',
        }
