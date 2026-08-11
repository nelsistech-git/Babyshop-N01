from odoo import models, fields, api, _
import logging
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
import requests
import json
from datetime import datetime
_logger = logging.getLogger(__name__)


class EmployeeTransfer(models.Model):
    _name = 'company.api.settings'
    #_inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Company Api Settings"
    _order = "id desc"
    
    name=fields.Char(string='Name')
    company_code=fields.Char(string='Company Code')
    url=fields.Char(string='Url')
    db_name=fields.Char(string='Database Name')
    user_id=fields.Char(string='User ID')
    password=fields.Char(string='Password')
    access_token=fields.Char(string='Access Token')
    my_company = fields.Boolean(string='My Company')
    other_location_ids = fields.One2many('company.api.settings.other.location','head_id',string='Locations', readonly=True)
    other_department_ids = fields.One2many('company.api.settings.other.department','head_id',string='Department', readonly=True)
    other_designation_ids = fields.One2many('company.api.settings.other.designation','head_id',string='Designation', readonly=True)
    other_work_schedule_ids = fields.One2many('company.api.settings.other.work_schedule','head_id',string='Work Schedule', readonly=True)
    other_att_policy_ids = fields.One2many('company.api.settings.other.att_policy','head_id',string='Attendance Policy', readonly=True)
    
    last_sync_date = fields.Datetime("Last Sync Date")
    last_sync_customer_date = fields.Datetime("Last Customer Sync Date")

    def action_sync_company_data(self):
        #----------------
        transfer_url = self.url
        company_code = self.company_code
        company_name = self.name
        db_name = self.db_name
        user_id = self.user_id
        password = self.password        
        access_token = self.access_token
        #--------------------
        url_connect = transfer_url + '/web/session/authenticate'        
        params = {
            'db': db_name,
            'login': user_id,
            'password': password
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
            #'Content-Length': str(len(json.dumps(params)))
        }
        session = requests.Session()
        response = session.post(url = url_connect, data= json.dumps({'params': params}) , headers= headers)
        server_response = response.json()
        
        #session_details = server_response['result']
        if server_response['result']['uid']:
            session_id = str(response.cookies.get('session_id'))
            
            odoo_url = transfer_url + '/api/transfer/other_company_data_sync'
            session.cookies['session_id'] = session_id
            
            # headers = {
            #     'Content-Type': 'application/json',
            #     'Accept': 'application/json',
            #     'Cookies': 'session_id= %s'%session_id
            # }
            params = {
                'company_code': company_code,
                'company_name':company_name,
                'db_name':db_name,
                'user_id': user_id,
                'password': password,                
                'access_token':access_token
            }
                          
            data = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params})
            # headers = json.dumps(headers)
            
            #response = requests.post(url=odoo_url, data=data, headers=headers)
            response = session.post(url = odoo_url, data = data, headers = headers)
            server_response = response.json()
            #print(server_response)
            if server_response['result']['status'] == '1':
                location_list = server_response['result']['location_list']
                department_list = server_response['result']['department_list']
                designation_list = server_response['result']['designation_list']
                work_schedule_list = server_response['result']['work_schedule_list']
                att_policy_list = server_response['result']['att_policy_list']
                
                loc_obj = self.env['company.api.settings.other.location']
                department_obj = self.env['company.api.settings.other.department']                
                designation_obj = self.env['company.api.settings.other.designation']
                work_schedule_obj = self.env['company.api.settings.other.work_schedule']
                att_policy_obj = self.env['company.api.settings.other.att_policy']
                
                #-------------
                for i in range(len(location_list)):
                    loc_dict = location_list[i]
                    loc_id = loc_dict['rec_id']
                    loc_name = loc_dict['name']                    
                    location_row = loc_obj.search([('head_id', '=', self.id),('rec_id', '=', loc_id)], limit=1)
                    if location_row:
                        if loc_name != location_row[0].name:
                            location_row[0].write({'name':loc_name})
                    else:
                        loc_obj.create({'head_id':self.id,'rec_id': loc_id,'name': loc_name})
                
                #-----------
                for j in range(len(department_list)):
                    dept_dict = department_list[j]
                    dept_id = dept_dict['rec_id']
                    dept_name = dept_dict['name']                    
                    dept_row = department_obj.search([('head_id', '=', self.id),('rec_id', '=', dept_id)], limit=1)
                    if dept_row:
                        if dept_name != dept_row[0].name:
                            dept_row[0].write({'name':dept_name})
                    else:
                        department_obj.create({'head_id':self.id,'rec_id': dept_id,'name': dept_name})
                
                #--------------
                for k in range(len(designation_list)):
                    desig_dict = designation_list[k]
                    desig_id = desig_dict['rec_id']
                    desig_name = desig_dict['name']   
                    dept_id = desig_dict['dept_id']
                    desig_row = designation_obj.search([('head_id', '=', self.id),('rec_id', '=', desig_id)], limit=1)
                    if desig_row:
                        vals = {}
                        change_flag = False
                        if dept_id != desig_row[0].dept_id:
                            dept_row2 = department_obj.search([('head_id', '=', self.id),('rec_id', '=', dept_id)], limit=1)
                            if dept_row2:
                                dept_id = dept_row2[0].id
                                vals['dept_id'] = dept_id
                                change_flag = True
                        if desig_name != desig_row[0].name:
                            vals['name'] = desig_name
                            change_flag = True
                        
                        if change_flag:
                            desig_row[0].write(vals)                            
                    else:
                        dept_id2 = ''
                        dept_row3 = department_obj.search([('head_id', '=', self.id),('rec_id', '=', dept_id)], limit=1)
                        if dept_row3:
                            dept_id2 = dept_row3[0].id
                        designation_obj.create({'head_id':self.id,'rec_id': desig_id,'name': desig_name,'dept_id': dept_id2})
                #-----------
                for j in range(len(work_schedule_list)):
                    work_sch_dict = work_schedule_list[j]
                    work_sch_id = work_sch_dict['rec_id']
                    work_sch_name = work_sch_dict['name']                    
                    work_sch_row = work_schedule_obj.search([('head_id', '=', self.id),('rec_id', '=', work_sch_id)], limit=1)
                    if work_sch_row:
                        if work_sch_name != work_sch_row[0].name:
                            work_sch_row[0].write({'name':work_sch_name})
                    else:
                        work_schedule_obj.create({'head_id':self.id,'rec_id': work_sch_id,'name': work_sch_name})
                #-----------
                for j in range(len(att_policy_list)):
                    att_policy_dict = att_policy_list[j]
                    att_policy_id = att_policy_dict['rec_id']
                    att_policy_name = att_policy_dict['name']                    
                    att_policy_row = att_policy_obj.search([('head_id', '=', self.id),('rec_id', '=', att_policy_id)], limit=1)
                    if att_policy_row:
                        if att_policy_name != att_policy_row[0].name:
                            att_policy_row[0].write({'name':att_policy_name})
                    else:
                        att_policy_obj.create({'head_id':self.id,'rec_id': att_policy_id,'name': att_policy_name})
                #------------
                self.last_sync_date = datetime.now()
            else:
                return False                
            
        else:
            return False

    def action_sync_company_customer_data(self):
        #print('action_sync_company_customer_data',self)
        #----------------
        transfer_url = self.url
        company_code = self.company_code
        company_name = self.name
        db_name = self.db_name
        user_id = self.user_id
        password = self.password
        access_token = self.access_token
        #--------------------
        url_connect = transfer_url + '/web/session/authenticate'
        params = {
            'db': db_name,
            'login': user_id,
            'password': password
        }
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
            #'Content-Length': str(len(json.dumps(params)))
        }
        session = requests.Session()
        response = session.post(url = url_connect, data= json.dumps({'params': params}) , headers= headers)
        server_response = response.json()
        print('server_response',server_response)

        #session_details = server_response['result']
        if server_response['result']['uid']:
            session_id = str(response.cookies.get('session_id'))

            odoo_url = transfer_url + '/api/transfer/other_company_customer_data_sync'
            session.cookies['session_id'] = session_id

            # headers = {
            #     'Content-Type': 'application/json',
            #     'Accept': 'application/json',
            #     'Cookies': 'session_id= %s'%session_id
            # }
            params = {
                'company_code': company_code,
                'company_name':company_name,
                'db_name':db_name,
                'user_id': user_id,
                'password': password,
                'access_token':access_token,
                'current_api_settings_id':self.id
            }

            data = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params})
            # headers = json.dumps(headers)

            #response = requests.post(url=odoo_url, data=data, headers=headers)
            response = session.post(url = odoo_url, data = data, headers = headers)
            server_response = response.json()
            if server_response['result']['status'] == '1':
                customer_list = server_response['result']['customer_list']
                rec_obj = self.env['res.partner']
                #-------------
                for i in range(len(customer_list)):
                    rec_dict = customer_list[i]
                    print(rec_dict)
                    rec_id = rec_dict['rec_id']
                    rec_name = rec_dict['name']
                    mobile = rec_dict['mobile']
                    comp_code = rec_dict['comp_code']
                    rec_row = rec_obj.search([('name', '=', rec_name)], limit=1)
                    print(rec_row)
                    if rec_row:
                        print('got.......')
                    else:
                        self.env['res.partner'].create({
                            'name': rec_name,
                            'phone': mobile,
                            'other_company_code': comp_code,
                        })
                #------------
                self.last_sync_customer_date = datetime.now()
            else:
                return False

        else:
            return False


class OtherCompanyLocation(models.Model):
    _name = 'company.api.settings.other.location'
    _description = "Company Api Settings Other Location"
    
    head_id = fields.Many2one('company.api.settings', ondelete="cascade",string='Company API', readonly=True)    
    rec_id = fields.Integer("Reference", readonly=True)
    name = fields.Char("Name", readonly=True)

class OtherCompanyDepartment(models.Model):
    _name = 'company.api.settings.other.department'
    _description = "Company Api Settings Other Department"
    
    head_id = fields.Many2one('company.api.settings', ondelete="cascade",string='Company API', readonly=True)    
    rec_id = fields.Integer("Reference", readonly=True)
    name = fields.Char("Name", readonly=True)

class OtherCompanyDesignation(models.Model):
    _name = 'company.api.settings.other.designation'
    _description = "Company Api Settings Other Designation"
    
    head_id = fields.Many2one('company.api.settings', ondelete="cascade",string='Company API', readonly=True)    
    rec_id = fields.Integer("Reference", readonly=True)
    name = fields.Char("Name", readonly=True)    
    dept_id = fields.Many2one('company.api.settings.other.department', ondelete="cascade",string='Department', readonly=True)
    
class OtherCompanyWorkSchedule(models.Model):
    _name = 'company.api.settings.other.work_schedule'
    _description = "Company Api Settings Other Work Schedule"
    
    head_id = fields.Many2one('company.api.settings', ondelete="cascade",string='Company API', readonly=True)    
    rec_id = fields.Integer("Reference", readonly=True)
    name = fields.Char("Name", readonly=True)
    
class OtherCompanyAttendancePolicy(models.Model):
    _name = 'company.api.settings.other.att_policy'
    _description = "Company Api Settings Other Attendance Policy"
    
    head_id = fields.Many2one('company.api.settings', ondelete="cascade",string='Company API', readonly=True)    
    rec_id = fields.Integer("Reference", readonly=True)
    name = fields.Char("Name", readonly=True)
    
    
    