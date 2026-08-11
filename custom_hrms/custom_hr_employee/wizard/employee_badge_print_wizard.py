from odoo import fields, models, api, _, exceptions
from odoo.exceptions import ValidationError
from calendar import monthrange
from datetime import date
import datetime
from datetime import datetime
from itertools import groupby

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.helper import xlsxwriter

import base64
import requests
from io import BytesIO

class EmployeeBadgePrintWizard(models.TransientModel):
    _name = 'employee.badge.print.wizard'
    _description = 'Print Employee Badges'

    employee_ids = fields.Many2many('hr.employee', string='Employees')

    def print_badge(self, data={}):
        employee = self.employee_ids
        if not employee:
            raise exceptions.ValidationError("Required PO")
        else:
            employee_list = []
            for line in employee:
                id = line.id
                name = line.name
                id_card_no = line.id_card_no
                gender = line.gender
                marital = line.marital
                place_of_birth = line.place_of_birth
                country_of_birth = line.country_of_birth
                birth_date = line.birthday
                department = line.department_id.name
                job = line.job_id.name
                job_title = line.job_title
                # section = line.section_id.name
                joining_date = line.initial_employment_date
                # date_obj = datetime.strptime(str[joining_date], '%Y-%m-%d')
                # joining_date = date_obj.strftime('%d-%m-%Y')
                # logo = line.company_id.logo
                # image_url = line.image_1920
                # village = line.village
                # post_office = line.post_office
                # thana = line.thana
                district = line.home_town_id.name
                blood_group = line.blood_group
                nid = line.nid

                logo_base64 = base64.b64encode(line.company_id.logo).decode('utf-8') if line.company_id.logo else None
                image_base64 = base64.b64encode(line.image_1920).decode('utf-8') if line.image_1920 else None
                signature_base64 = line.signature
                # authority_base64 = line.company_id.authority_signature

                # Convert image URL to base64 format
                # response = requests.get(image_url)
                # if response.status_code == 200:
                #     img_base64 = base64.b64encode(BytesIO(response.content).read())
                # else:
                #     img_base64 = ""

                dict_data = {
                    'id': id,
                    'name': name,
                    'id_card_no' : id_card_no,
                    'gender': gender,
                    'marital': marital,
                    'place_of_birth': place_of_birth,
                    'country_of_birth': country_of_birth,
                    'birth_date': birth_date,
                    'department': department,
                    'job': job,
                    'job_title': job_title,
                    # 'section': section,
                    'joining_date': joining_date,
                    'logo_base64': logo_base64,
                    'image_base64': image_base64,  # Assign the base64 image here
                    'signature_base64': signature_base64,  # Assign the base64 image here
                    # 'authority_base64': authority_base64,  # Assign the base64 image here
                    # 'village': village,
                    # 'post_office': post_office,
                    # 'thana': thana,
                    'district': district,
                    'blood_group': blood_group,
                    'nid': nid,
                }
                employee_list.append(dict_data)
                #print(employee_list)

            data = {
                'model': "employee.badge.print.wizard",
                'form': self.read()[0],
                'employee_list': employee_list,
            }
            #print(data)
            return self.env.ref('custom_hr_employee.employee_badge_print_format').with_context().report_action(self, data=data)
