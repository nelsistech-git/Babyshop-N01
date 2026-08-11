import datetime
import logging

from odoo import http
from odoo.http import request
import datetime
from datetime import datetime

_logger = logging.getLogger(__name__)


class EmployeeAPI(http.Controller):
    @http.route('/api/transfer/create', type='json', auth="user", methods=['POST'], csrf=False)
    def create_inter_transfer(self, **kw):
        """
        {"jsonrpc": "2.0", "method": "call", "params": {"company_code": "TTM", "company_name": "Topten Mart", "user_id": "admin2", "password": "222", "db_name": "topten2", "access_token": "bbb222", "employee_name": "A.K.M Nurul Ashrar Khan", "from_company": "Top Ten Fabrics & Tailors Ltd.", "from_department": "Admin - TTG", "from_designation": "Admin Officer (Front Desk) (HR, Admin & Compliance (HAC)) - TTG", "from_job_location": "Banasree (TTG-002)", "transfer_reference": "EMP-TRA-00007", "to_company": "Topten Mart", "to_department": "ddd", "to_designation": "ppp", "to_job_location": "www", "requested_date": "2022-02-17 06:39:33", "effected_date": "2022-02-17"}}
        """
        """
        odoo_url---------- http://127.0.0.1:8069/api/transfer/create
headers---------
{'Content-Type': 'application/json', 'Accept': 'application/json', 'Cookie': 'session_id= 374424fecb174186b862771e0add14c23c830c90'}
data--------
{"jsonrpc": "2.0", "method": "call", "params": {"company_code": "TTM", "company_name": "Topten Mart", "user_id": "erp@nelsistech.com", "password": "admin@321#", "db_name": "topten2", "access_token": "bbb222", "employee_name": "A.K.M Nurul Ashrar Khan", "from_company": "Top Ten Fabrics & Tailors Ltd.", "from_department": "Admin - TTG", "from_designation": "Admin Officer (Front Desk) (HR, Admin & Compliance (HAC)) - TTG", "from_job_location": "Banasree (TTG-002)", "transfer_reference": "EMP-TRA-00010", "to_company": "Topten Mart", "to_department": "d", "to_designation": "s", "to_job_location": "a", "requested_date": "2022-02-17 11:55:42", "effected_date": "2022-02-17"}}

        """        
        if request.httprequest.method == 'POST':
            comp_code = kw.get('company_code')
            db_name = kw.get('db_name')
            user_id = kw.get('user_id')
            password = kw.get('password')
            #password = partner_obj.hash_password(kw.get('password'))
            access_token = kw.get('access_token')

            transfer_history_obj = request.env['inter.company.transfer.history']
            comp_obj_to = request.env['res.company'].sudo().search([('short_code', '=', comp_code)], limit=1)
            if comp_obj_to:
                comp_sett_obj_to = request.env['company.api.settings'].sudo().search([('company_code', '=', comp_code),('db_name', '=', db_name),('user_id', '=', user_id),('password', '=', password),('access_token', '=', access_token)], limit=1)
                if comp_sett_obj_to:
                    employee_name = kw.get('employee_name')
                    device_user_id = kw.get('device_user_id')
                    identification_id = kw.get('identification_id')
                    id_card_no = kw.get('id_card_no')
                    door_card_no = kw.get('door_card_no')      
                    work_email = kw.get('work_email')
                    contact_no = kw.get('contact_no')
                    #print('work_email------2---',work_email)
                    #print('contact_no-------2--',contact_no)
                    from_company = kw.get('from_company')
                    from_department = kw.get('from_department')
                    from_designation = kw.get('from_designation')
                    from_job_location = kw.get('from_job_location')
                    in_reference = kw.get('in_reference')
                    to_company = comp_sett_obj_to[0].id
                    
                    to_job_location = kw.get('to_job_location')
                    to_department = kw.get('to_department')
                    to_designation = kw.get('to_designation')
                    to_resource_calendar = kw.get('to_resource_calendar')
                    to_att_policy = kw.get('to_att_policy')
                    
                    to_job_location_id = kw.get('to_job_location_id')
                    to_department_id = kw.get('to_department_id')
                    to_designation_id = kw.get('to_designation_id')
                    to_resource_calendar_id = kw.get('to_resource_calendar_id')
                    to_att_policy_id = kw.get('to_att_policy_id')
                    
                    requested_date = kw.get('requested_date')
                    effected_date = kw.get('effected_date')
                    initial_employment_date = kw.get('initial_employment_date')
                    note = kw.get('note')
                    
                    gross_salary = kw.get('gross_salary')
                    total_residual_loan = kw.get('total_residual_loan')
                    advance_salary = kw.get('advance_salary')
                    residual_Salary = kw.get('residual_Salary')
                    
                    loan_balance = kw.get('loan_balance')
                    loan_interest_balance = kw.get('loan_interest_balance')
                    salary_adv_balance = kw.get('salary_adv_balance')
                    tds_balance = kw.get('tds_balance')
                    pf_balance = kw.get('pf_balance')
                    salary_payable_balance = kw.get('salary_payable_balance')
                    
                    leave_casual_balance = kw.get('leave_casual_balance')
                    leave_sick_balance = kw.get('leave_sick_balance')
                    leave_marriage_balance = kw.get('leave_marriage_balance')
                    
                    vals = {
                        'transfer_type': 'in',
                        'employee_name': employee_name,
                        'device_user_id':device_user_id,
                        'identification_id':identification_id,
                        'id_card_no':id_card_no,
                        'door_card_no':door_card_no,
                        'work_email': work_email,
                        'contact_no': contact_no,
                        'from_company': from_company,
                        'from_department': from_department,
                        'from_designation': from_designation,
                        'from_job_location': from_job_location,                        
                        'in_reference': in_reference,
                        'to_company': to_company,                        
                        'to_department': to_department,
                        'to_designation': to_designation,
                        'to_job_location': to_job_location,
                        'to_resource_calendar': to_resource_calendar,
                        'to_att_policy': to_att_policy,
                        
                        'to_department_id': to_department_id,
                        'to_designation_id': to_designation_id,
                        'to_job_location_id': to_job_location_id,
                        'to_resource_calendar_id': to_resource_calendar_id,
                        'to_att_policy_id': to_att_policy_id,
                        
                        'requested_date': requested_date,
                        'effected_date': effected_date,
                        'initial_employment_date': initial_employment_date,
                        'note': note,
                        'gross_salary': gross_salary,
                        'total_residual_loan': total_residual_loan,
                        'advance_salary': advance_salary,
                        'residual_Salary': residual_Salary,
                        
                        'loan_balance': loan_balance,
                        'loan_interest_balance': loan_interest_balance,
                        'salary_adv_balance': salary_adv_balance,
                        'tds_balance': tds_balance,
                        'pf_balance': pf_balance,
                        'salary_payable_balance': salary_payable_balance,
                        
                        'leave_casual_balance': leave_casual_balance,
                        'leave_sick_balance': leave_sick_balance,
                        'leave_marriage_balance': leave_marriage_balance
                    }
                    transfer_history_obj.sudo().create(vals)
                    
                    data = {
                        'status': '1',
                        'response': ['Success'],
                        'message': 'Success'
                    }                    
                else:
                    data = {
                        'status': '0',
                        'response': ['Invalid Company'],
                        'message': 'Invalid Company'
                    }
            else:
                data = {
                    'status': '0',
                    'response': ['Invalid Credential'],
                    'message': 'Invalid Credential'
                }
        else:
            data = {
                'status': '0',
                'response': ['Method Not Allowed'],
                'message': 'Method Not Allowed'
            }

        return data
        #-----------------
    
    @http.route('/api/transfer/other_company_data_sync', type='json', auth="user", methods=['POST'], csrf=False)
    def get_other_company_data(self, **kw):
        print('other_company_data_sync............')
        """
        {"jsonrpc": "2.0", "method": "call", "params": {"company_code": "TTM", "company_name": "Topten Mart", "user_id": "admin2", "password": "222", "db_name": "topten2", "access_token": "bbb222", "employee_name": "A.K.M Nurul Ashrar Khan", "from_company": "Top Ten Fabrics & Tailors Ltd.", "from_department": "Admin - TTG", "from_designation": "Admin Officer (Front Desk) (HR, Admin & Compliance (HAC)) - TTG", "from_job_location": "Banasree (TTG-002)", "transfer_reference": "EMP-TRA-00007", "to_company": "Topten Mart", "to_department": "ddd", "to_designation": "ppp", "to_job_location": "www", "requested_date": "2022-02-17 06:39:33", "effected_date": "2022-02-17"}}
        """
        """
        odoo_url---------- http://127.0.0.1:8069/api/transfer/other_company_data_sync
headers---------
{'Content-Type': 'application/json', 'Accept': 'application/json', 'Cookie': 'session_id= 374424fecb174186b862771e0add14c23c830c90'}
data--------
{"jsonrpc": "2.0", "method": "call", "params": {"company_code": "TTM", "company_name": "Topten Mart", "user_id": "erp@nelsistech.com", "password": "admin@321#", "db_name": "topten2", "access_token": "bbb222", "employee_name": "A.K.M Nurul Ashrar Khan", "from_company": "Top Ten Fabrics & Tailors Ltd.", "from_department": "Admin - TTG", "from_designation": "Admin Officer (Front Desk) (HR, Admin & Compliance (HAC)) - TTG", "from_job_location": "Banasree (TTG-002)", "transfer_reference": "EMP-TRA-00010", "to_company": "Topten Mart", "to_department": "d", "to_designation": "s", "to_job_location": "a", "requested_date": "2022-02-17 11:55:42", "effected_date": "2022-02-17"}}

        """        
        if request.httprequest.method == 'POST':
            comp_code = kw.get('company_code')
            db_name = kw.get('db_name')
            user_id = kw.get('user_id')
            password = kw.get('password')
            #password = partner_obj.hash_password(kw.get('password'))
            access_token = kw.get('access_token')
            
            comp_obj_to = request.env['res.company'].sudo().search([('short_code', '=', comp_code)], limit=1)
            if comp_obj_to:
                comp_sett_obj_to = request.env['company.api.settings'].sudo().search([('company_code', '=', comp_code),('db_name', '=', db_name),('user_id', '=', user_id),('password', '=', password),('access_token', '=', access_token)], limit=1)
                if comp_sett_obj_to:
                    
                    location_list = []
                    location_rows = request.env['stock.location'].sudo().search([('company_id','=',comp_obj_to[0].id),('is_work_loc','=',True)], order='id')
                    for loc in location_rows:
                        loc_id = loc.id
                        loc_name = loc.name
                        location_list.append({'rec_id':loc_id,'name':loc_name})
                        
                    department_list = []
                    department_rows = request.env['hr.department'].sudo().search([('company_id','=',comp_obj_to[0].id)], order='id')
                    for dept in department_rows:
                        dept_id = dept.id
                        dept_name = dept.name
                        department_list.append({'rec_id':dept_id,'name':dept_name})
                        
                    designation_list = []
                    designation_rows = request.env['hr.job'].sudo().search([('company_id','=',comp_obj_to[0].id)], order='id')
                    for desig in designation_rows:
                        desig_id = desig.id
                        desig_name = desig.name
                        desig_dept = desig.department_id.id
                        designation_list.append({'rec_id':desig_id,'name':desig_name,'dept_id':desig_dept})
                    
                    work_schedule_list = []
                    work_schedule_rows = request.env['resource.calendar'].sudo().search([], order='id')
                    for rec in work_schedule_rows:
                        rec_id = rec.id
                        rec_name = rec.name
                        work_schedule_list.append({'rec_id':rec_id,'name':rec_name})
                    
                    att_policy_list = []
                    att_policy_rows = request.env['hr.attendance.policy'].sudo().search([], order='id')
                    for rec in att_policy_rows:
                        rec_id = rec.id
                        rec_name = rec.name
                        att_policy_list.append({'rec_id':rec_id,'name':rec_name})
                        
                    data = {
                        'status': '1',
                        'response': ['Success'],
                        'message': 'Success',
                        'location_list':location_list,
                        'department_list':department_list,
                        'designation_list':designation_list,
                        'work_schedule_list':work_schedule_list,
                        'att_policy_list':att_policy_list
                    }                    
                else:
                    data = {
                        'status': '0',
                        'response': ['Invalid Company'],
                        'message': 'Invalid Company'
                    }
            else:
                data = {
                    'status': '0',
                    'response': ['Invalid Credential'],
                    'message': 'Invalid Credential'
                }
        else:
            data = {
                'status': '0',
                'response': ['Method Not Allowed'],
                'message': 'Method Not Allowed'
            }

        return data
        #-----------------

    @http.route('/api/transfer/other_company_customer_data_sync', type='json', auth="user", methods=['POST'], csrf=False)
    def get_other_customer_company_data(self, **kw):
        print('get_other_customer_company_data............')
        if request.httprequest.method == 'POST':
            comp_code = kw.get('company_code')
            db_name = kw.get('db_name')
            user_id = kw.get('user_id')
            password = kw.get('password')
            current_api_settings_id = kw.get('current_api_settings_id')
            # current_api_settings_obj = request.env['company.api.settings'].sudo().search([('id', '=', current_api_settings_id)], limit=1)
            #password = partner_obj.hash_password(kw.get('password'))
            access_token = kw.get('access_token')
            comp_obj_to = request.env['res.company'].sudo().search([('short_code', '=', comp_code)], limit=1)
            if comp_obj_to:
                comp_sett_obj_to = request.env['company.api.settings'].sudo().search([('company_code', '=', comp_code),('db_name', '=', db_name),('user_id', '=', user_id),('password', '=', password),('access_token', '=', access_token)], limit=1)
                if comp_sett_obj_to:
                    customer_list = []
                    domain = [('id','!=',False)]
                    # if comp_sett_obj_to.last_sync_customer_date:
                    #     domain.append([('create_date', '>', '2022-05-26 05:58:15')])
                    customer_rows = request.env['res.partner'].sudo().search(domain, order='id')
                    print(customer_rows)
                    for rec in customer_rows:
                        loc_id = rec.id
                        loc_name = rec.name
                        customer_list.append({'rec_id':loc_id,'name':loc_name,'mobile':rec.mobile,'comp_code':comp_code})
                    data = {
                        'status': '1',
                        'response': ['Success'],
                        'message': 'Success',
                        'customer_list':customer_list,
                    }
                else:
                    data = {
                        'status': '0',
                        'response': ['Invalid Company'],
                        'message': 'Invalid Company'
                    }
            else:
                data = {
                    'status': '0',
                    'response': ['Invalid Credential'],
                    'message': 'Invalid Credential'
                }
        else:
            data = {
                'status': '0',
                'response': ['Method Not Allowed'],
                'message': 'Method Not Allowed'
            }

        return data
        #-----------------

    # @http.route('/api/v1/customer/update', type='json', auth="user", methods=['POST'], csrf=False)
    # def customer_update(self, **kw):
    #     """
    #         {"jsonrpc": "2.0", "params":{"name": "testmob2", "email":"email@gmail.com", "address1":"sector 10", "address2":"Uttara", "post_code": "1234",  "city": "False","division": "False", "district": "False","gdl_zone": "False", "assigned_kam": "False", "customer_type": "retail", "mobile":"0232212123",  "access_token":"63d51675-58e8-4dab-bf87-124fb3c37409"}}}
    #     Returns:
    #         [type]: [description]
    #     """
    #
    #     if request.httprequest.method == 'POST':
    #
    #         partner_obj = request.env['res.partner'].sudo()
    #
    #         customer = partner_obj.search(['&', ('mobile', '=', kw.get('mobile')), ('mobile_customer', '=', True)])
    #
    #         if customer and customer.customer_access_token == kw.get('access_token'):
    #             vals = dict()
    #             if 'name' in kw:
    #                 vals['name'] = kw.get('name')
    #                 vals['display_name'] = kw.get('name')
    #             if 'email' in kw:
    #                 vals['email'] = kw.get('email')
    #             if 'address1' in kw:
    #                 vals['street'] = kw.get('address1')
    #             if 'address2' in kw:
    #                 vals['street2'] = kw.get('address2')
    #             if 'post_code' in kw:
    #                 vals['zip'] = kw.get('post_code')
    #             if 'city' in kw:
    #                 vals['city'] = kw.get('city')
    #             if 'division' in kw:
    #                 vals['division'] = kw.get('division')
    #             if 'district' in kw:
    #                 vals['district'] = kw.get('district')
    #             if 'gdl_zone' in kw:
    #                 vals['gdl_zone'] = kw.get('gdl_zone')
    #             if 'assigned_kam' in kw:
    #                 vals['assigned_kam'] = kw.get('assigned_kam')
    #             if 'customer_type' in kw:
    #                 vals['mobile_customer_type'] = kw.get('customer_type')
    #             if 'profile_image' in kw:
    #                 vals['image_1920'] = kw.get('profile_image')
    #
    #             customer.write(vals)
    #
    #             data = {
    #                 'status': 200,
    #                 'response': [
    #                     {
    #                         "id": customer.id
    #                     }
    #                 ],
    #                 'message': 'Success'
    #             }
    #         else:
    #             data = {
    #                 'status': 404,
    #                 'response': ['Not Found'],
    #                 'message': 'Customer does not exists'
    #             }
    #
    #     else:
    #         data = {
    #             'status': 405,
    #             'response': ['Method Not Allowed'],
    #             'message': 'Method Not Allowed'
    #         }
    #
    #     return data
    #
    # @http.route('/api/v1/customer/login', type='json', auth="none", methods=['POST'], csrf=False)
    # def customer_login(self, **kw):
    #     """
    #     {"jsonrpc": "2.0", "params":{"mobile":"0232212123", "password":"1212122"}}
    #
    #     Returns:
    #         [type]: [description]
    #     """
    #
    #     if request.httprequest.method == 'POST':
    #         partner_obj = request.env['res.partner'].sudo()
    #
    #         mobile = kw.get('mobile')
    #         password = partner_obj.hash_password(kw.get('password'))
    #         # password = kw.get('password')
    #
    #         customer = partner_obj.search(['&', ('mobile', '=', mobile), ('mobile_customer', '=', True)])
    #
    #         if customer.password == password:
    #
    #             customer_access_token = partner_obj.get_customer_access_token()
    #
    #             customer.write({
    #                 'customer_access_token': customer_access_token,
    #                 'last_login_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    #             })
    #
    #             if not customer.greeting_sms:
    #                 sms_obj = request.env['customer.otp'].sudo()
    #                 cus_sms = "Welcome to the world of Water Solution! Please accept heartiest wishes from the Service and Maintenance team of Green Dot Limited"
    #                 con_sms = "A new customer - {0} with the mobile no. {1} has been registered through the app.".format(
    #                     customer.name, customer.mobile)
    #                 cus_mobile = [customer.mobile]
    #                 con_mobile = [val.mobile for val in
    #                               request.env['sms.recipient'].sudo().search([('status', '=', 'True')])]
    #
    #                 cus_resp = sms_obj.send_custom_sms(cus_mobile, cus_sms)
    #                 con_resp = sms_obj.send_custom_sms(con_mobile, con_sms)
    #
    #                 if cus_resp and con_resp:
    #                     customer.write({
    #                         'greeting_sms': True,
    #                         'registration_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    #                         'last_login_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    #                     })
    #
    #             data = {
    #                 'status': 200,
    #                 'response': [
    #                     {
    #                         "id": customer.id,
    #                         "access_token": customer_access_token
    #                     }
    #                 ],
    #                 'message': 'Success'
    #             }
    #         else:
    #             data = {
    #                 'status': 401,
    #                 'response': ['Mobile or Password does not match'],
    #                 'message': 'Unauthorized'
    #             }
    #
    #     else:
    #         data = {
    #             'status': 405,
    #             'response': ['Method Not Allowed'],
    #             'message': 'Method Not Allowed'
    #         }
    #
    #     return data
    #
    # @http.route('/api/v1/customer/reset_password', type='json', auth="user", methods=['POST'], csrf=False)
    # def reset_password(self, **kw):
    #     """
    #     {"jsonrpc": "2.0", "params":{"mobile":"0232212123", "old_password":"111111", "new_password":"111111", "access_token":"63d51675-58e8-4dab-bf87-124fb3c37409"}}
    #
    #     Returns:
    #         [type]: [description]
    #     """
    #
    #     if request.httprequest.method == 'POST':
    #
    #         partner_obj = request.env['res.partner'].sudo()
    #
    #         old_password = partner_obj.hash_password(kw.get('old_password'))
    #
    #         customer = partner_obj.search(['&', '&', ('mobile', '=', kw.get('mobile')), ('password', '=', old_password),
    #                                        ('mobile_customer', '=', True)])
    #
    #         if customer and customer.customer_access_token == kw.get('access_token'):
    #             new_password = partner_obj.hash_password(kw.get('new_password'))
    #
    #             vals = {
    #                 'password': new_password
    #             }
    #
    #             customer.write(vals)
    #
    #             data = {
    #                 'status': 200,
    #                 'response': [{"id": customer.id}],
    #                 'message': 'Success'
    #             }
    #         else:
    #             data = {
    #                 'status': 404,
    #                 'response': ['Not Found'],
    #                 'message': 'Customer does not exists'
    #             }
    #     else:
    #         data = {
    #             'status': 405,
    #             'response': ['Method Not Allowed'],
    #             'message': 'Method Not Allowed'
    #         }
    #
    #     return data
    #
    # @http.route('/api/v1/customer/forget_password', type='json', auth="user", methods=['POST'], csrf=False)
    # def forget_password(self, **kw):
    #     """
    #     {"jsonrpc": "2.0", "params":{"mobile":"0232212123", "otp":"1111", "new_password":"111111"}}
    #
    #     Returns:
    #         [type]: [description]
    #     """
    #
    #     if request.httprequest.method == 'POST':
    #
    #         partner_obj = request.env['res.partner'].sudo()
    #         customer = partner_obj.search(['&', ('mobile', '=', kw.get('mobile')), ('mobile_customer', '=', True)])
    #
    #         new_password = partner_obj.hash_password(kw.get('new_password'))
    #
    #         if customer:
    #             otp_obj = request.env['customer.otp'].sudo()
    #
    #             customer_otp = otp_obj.search([('name', '=', kw.get('mobile'))])
    #
    #             if customer_otp.otp != kw.get('otp'):
    #                 data = {
    #                     'status': 401,
    #                     'response': ['OTP does not match'],
    #                     'message': 'OTP does not match'
    #                 }
    #             else:
    #
    #                 vals = {
    #                     'password': new_password
    #                 }
    #
    #                 customer.write(vals)
    #
    #                 data = {
    #                     'status': 200,
    #                     'response': [
    #                         {
    #                             'id': customer.id
    #                         }
    #                     ],
    #                     'message': 'Success'
    #                 }
    #         else:
    #             data = {
    #                 'status': 404,
    #                 'response': ['Not Found'],
    #                 'message': 'Customer does not exists'
    #             }
    #     else:
    #         data = {
    #             'status': 405,
    #             'response': ['Method Not Allowed'],
    #             'message': 'Method Not Allowed'
    #         }
    #
    #     return data
    #
    # @http.route('/api/v1/customer', type='json', auth="user", methods=['POST'], csrf=False)
    # def customer_info(self, **kw):
    #     """
    #     {"jsonrpc": "2.0","params": {"mobile": "0232212123","access_token": "63d51675-58e8-4dab-bf87-124fb3c37409"}}
    #
    #     Returns:
    #         [type]: [description]
    #     """
    #
    #     if request.httprequest.method == 'POST':
    #
    #         customer_rec = request.env['res.partner'].search(
    #             ['&', ('mobile', '=', kw.get('mobile')), ('mobile_customer', '=', True)])
    #
    #         if customer_rec and customer_rec.customer_access_token == kw.get('access_token'):
    #
    #             customer = []
    #
    #             vals = {
    #                 'id': customer_rec.id,
    #                 'name': customer_rec.name if customer_rec.name else None,
    #                 'mobile': customer_rec.mobile if customer_rec.mobile else None,
    #                 'email': customer_rec.email if customer_rec.email else None,
    #                 'address1': str(customer_rec.street) if customer_rec.street else None,
    #                 'address2': str(customer_rec.street2) if customer_rec.street2 else None,
    #                 'post_code': str(customer_rec.zip) if customer_rec.zip else None,
    #                 'city': str(customer_rec.city) if customer_rec.city else None,
    #                 'division': str(customer_rec.division) if customer_rec.division else None,
    #                 'district': str(customer_rec.district) if customer_rec.district else None,
    #                 'gdl_zone': str(customer_rec.gdl_zone) if customer_rec.gdl_zone else None,
    #                 'assigned_kam': str(customer_rec.assigned_kam) if customer_rec.assigned_kam else None,
    #                 'customer_type': str(
    #                     customer_rec.mobile_customer_type) if customer_rec.mobile_customer_type else None,
    #                 'sales_person': customer_rec.user_id.name if customer_rec.user_id else None,
    #                 'profile_image': customer_rec.image_1920 if customer_rec.image_1920 else None
    #             }
    #
    #             customer.append(vals)
    #
    #             data = {
    #                 'status': 200,
    #                 'response': customer,
    #                 'message': 'Success'
    #             }
    #         else:
    #             data = {
    #                 'status': 404,
    #                 'response': ['Not Found'],
    #                 'message': 'Customer does not exists'
    #             }
    #     else:
    #         data = {
    #             'status': 405,
    #             'response': ['Method Not Allowed'],
    #             'message': 'Method Not Allowed'
    #         }
    #
    #     return data
    #
    # @http.route('/api/v1/otp', type='json', auth="user", methods=['POST'], csrf=False)
    # def get_otp(self, **kw):
    #     """{"jsonrpc": "2.0","params": {"mobile": "0232212123"}}
    #
    #     Returns:
    #         [type]: [description]
    #     """
    #
    #     if request.httprequest.method == 'POST':
    #
    #         otp_obj = request.env['customer.otp'].sudo()
    #         partner_obj = request.env['res.partner'].sudo()
    #
    #         if 'mobile' in kw:
    #             mobile = partner_obj.sanitize_number(kw.get('mobile'))
    #             otp_obj.delete_otp(mobile)
    #             otp = otp_obj.generate_otp(mobile)
    #             otp_obj.send_otp_by_sms(mobile, otp)
    #             data = {
    #                 'status': 200,
    #                 'response': [
    #                     {
    #                         'status': 'Success'
    #                     }
    #                 ],
    #                 'message': 'Success'
    #             }
    #         else:
    #             data = {
    #                 'status': 500,
    #                 'response': [
    #                     {
    #                         'status': 'Params ERROR'
    #                     }
    #                 ],
    #                 'message': 'Params Error'
    #             }
    #
    #     else:
    #         data = {
    #             'status': 405,
    #             'response': ['Method Not Allowed'],
    #             'message': 'Method Not Allowed'
    #         }
    #
    #     return data
    #
    # # not require now
    # @http.route('/api/v1/customers', type='json', auth="user", methods=['GET'], csrf=False)
    # def customer_list(self):
    #     """
    #
    #     Returns:
    #         [type]: [description]
    #     """
    #
    #     if request.httprequest.method == 'GET':
    #
    #         customers_rec = request.env['res.partner'].search([('mobile_customer', '=', True)])
    #         customers = []
    #
    #         for rec in customers_rec:
    #             vals = {
    #                 'id': rec.id,
    #                 'name': rec.name,
    #                 'mobile': rec.mobile,
    #                 'email': rec.email,
    #                 'address': str(rec.street) + str(rec.street2) + str(rec.city) + str(rec.zip)
    #             }
    #
    #             customers.append(vals)
    #
    #         data = {
    #             'status': 200,
    #             'response': customers,
    #             'message': 'Success'
    #         }
    #     else:
    #         data = {
    #             'status': 405,
    #             'response': ['Method Not Allowed'],
    #             'message': 'Method Not Allowed'
    #         }
    #
    #     return data
