from odoo import fields, models, api
from odoo.addons.helper import validator
from datetime import datetime


class HREmployeeLetters(models.Model):
    """ HR Employee Letters model """
    _name = 'hr.employee.letters'
    _rec_name = 'ref_no'
    _order = 'current_date desc'

    @api.model
    def _get_current_date(self):
        """ @:return current date """
        return fields.Date.today()

    type = fields.Selection([
        ('head_office', 'Head Office'),
        ('shop', 'Branch/Shop')
    ], required=True, string="Type")

    letter_template_id = fields.Many2one('employee.letter.template', required=True,
                                         string="Letter Name")
    letter_type = fields.Selection(string='Letter Type', readonly=True, related='letter_template_id.template_type', store=True)

    ref_no = fields.Char(string="Reference", help="Reference")
    current_date = fields.Date(string="Letter Date", required=True)
    effective_date = fields.Date(string="Effective Date",
                                 help="From which date this will be effective")
    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete="set null")
    job_id = fields.Many2one('hr.job', string="Designation", ondelete="set null")
    department_id = fields.Many2one('hr.department', string="Department", ondelete="set null")
    agreement_date = fields.Date(string="Agreement Date",
                                 help="Agreement date with this employee")
    letter_template_details = fields.Html(string="Letter Details")
    address_no = fields.Text(string="Permanent Address", help="Permanent address of employee")
    take_over_from_id = fields.Many2one('hr.employee', string="Charge Takeover From",
                                        domain=[('is_shop_employee', '=', True)], help="Take charge from whom")
    take_over_to_id = fields.Many2one('hr.employee', string="Charge Takeover To",
                                      domain=[('is_shop_employee', '=', True)], help="Take charge to whom")
    present_address_no = fields.Text(string='Present Address')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('approve', 'Approved'),
        ('cancel', 'Cancelled')
    ], default='draft', required=True)

    letter_cc = fields.Text(string="Letter Cc", help="list cc name with separate line")
    up_to_date = fields.Date(string="Up to Date", help="Performance year end")
    last_business_date = fields.Date(string="Last Business Date", help="Last business date")
    emp_position_id = fields.Many2one('hr.job', string="Position", ondelete="set null")
    report_department_id = fields.Many2one('hr.department', string="Report Department",
                                           help="In which department manager will report")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company,
                                 store=True)

    # emp_company = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company, store=True)

    @api.onchange('type')
    def _onchange_type(self):
        self.employee_id = None
        self.job_id = None
        self.department_id = None
        self.ref_no = ''
        self.current_date = ''
        self.effective_date = ''
        self.agreement_date = ''
        self.letter_cc = ''
        self.letter_template_id = None
        self.letter_template_details = ''

        # if self.type == 'shop':
        #     emp_ids = self.env['hr.employee'].search([('is_shop_employee', '=', True)]).ids
        # else:
        #     emp_ids = self.env['hr.employee'].search([('is_shop_employee', '!=', True)]).ids
        emp_ids = self.env['hr.employee'].search([('active', '=', True)]).ids

        return {'domain': {'employee_id': [('id', 'in', emp_ids)]}}

    @api.constrains('ref_no')
    def _check_unique_constraint(self):
        msg = "Reference {0}".format(self.ref_no)
        envobj = self.env['hr.employee.letters']
        conditionlist = [('ref_no', '=ilike', self.ref_no)]
        validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.constrains('letter_template_details')
    def _check_letter_template_details(self):
        limit = 10000
        record = self.letter_template_details
        field_name = "Letter Details"
        validator._check_length_with_clean_htmltag(self, record, limit, field_name)

    @api.onchange('letter_template_id')
    def _onchange_letter_template_id(self):
        self.employee_id = None
        self.job_id = None
        self.department_id = None
        self.ref_no = ''
        self.current_date = ''
        self.effective_date = ''
        self.agreement_date = ''
        self.letter_cc = ''
        self.letter_template_details = ''
        if self.letter_type:
            temp_obj = self.env['employee.letter.template'].search([('id', '=', self.letter_template_id.id),
                                                                    ('active', '=', True)], order='id desc', limit=1)
            if temp_obj:
                self.letter_template_details = temp_obj.description
            else:
                self.letter_template_details = ""

    #     def _onchange_letter_type(self):
    #         """ Set letter template onchange of letter_type """
    #         self.employee_id = None
    #         self.job_id = None
    #         self.department_id = None
    #         self.ref_no = ''
    #         self.current_date = ''
    #         self.effective_date = ''
    #         self.agreement_date = ''
    #         self.letter_cc = ''
    #         self.letter_template_id = None
    #         self.letter_template_details = ''
    #         if self.letter_type:
    #             temp_obj = self.env['employee.letter.template'].search([('template_type', '=', self.letter_type),
    #                                                                     ('active', '=', True)], order='id desc', limit=1)
    #             if temp_obj:
    #                 self.letter_template_id = temp_obj.id
    #                 self.letter_template_details = temp_obj.description
    #             else:
    #                 self.letter_template_id = ""
    #                 self.letter_template_details = ""

    @api.onchange('employee_id', 'ref_no', 'current_date', 'effective_date', 'letter_cc', 'agreement_date',
                  'up_to_date',
                  'last_business_date', 'emp_position_id', 'address_no', 'take_over_from_id', 'take_over_to_id',
                  'report_department_id', 'present_address_no')
    def _onchange_all_fields(self):
        """ change job_id and department id and set corresponding value in letter details """
        if self.employee_id:
            self.job_id = self.employee_id.job_id.id
            self.department_id = self.employee_id.department_id.id
            self.address_no = self.employee_id.p_address_id
            self.company_id = self.employee_id.company_id

            # emp_name = self.employee_id.name_related
            emp_name = self.employee_id.name
            emp_department = self.employee_id.department_id.name
            emp_designation = self.employee_id.job_id.name
            emp_company = self.employee_id.company_id.name

            if self.employee_id.date_of_confirmation:
                confirm_date = str(
                    datetime.strptime(str(self.employee_id.date_of_confirmation), '%Y-%m-%d').strftime('%B %d, %Y'))
            else:
                confirm_date = "XX:XX:XXXX"

            if self.employee_id.fam_father:
                emp_father_name = self.employee_id.fam_father
            else:
                emp_father_name = 'X'

            if self.employee_id.passport_id:
                emp_passport = str(self.employee_id.passport_id)
            else:
                emp_passport = 'X'

            if self.employee_id.gender == 'male':
                emp_salutation = 'Mr'
                emp_pro_salutation = 'he'
                emp_pa_salutation = 'his'
            elif self.employee_id.gender == 'female':
                emp_salutation = 'Ms'
                emp_pro_salutation = 'she'
                emp_pa_salutation = 'her'
            else:
                emp_salutation = 'Mr/Ms'
                emp_pro_salutation = 'he/she'
                emp_pa_salutation = 'his/her'

            if self.employee_id.initial_employment_date:
                emp_join_date = str(
                    datetime.strptime(str(self.employee_id.initial_employment_date), '%Y-%m-%d').strftime('%B %d, %Y'))
            else:
                emp_join_date = "XX:XX:XXXX"

            if self.employee_id.work_location_id:
                emp_w_location = str(self.employee_id.work_location_id.name)
            else:
                emp_w_location = ''

            if self.employee_id.company_id:
                emp_company = str(self.employee_id.company_id.name)
            else:
                emp_company = ''
        else:
            self.job_id = None
            self.department_id = None
            # self.address_no = None
            emp_name = 'X'
            emp_department = 'X'
            emp_designation = 'X'
            emp_salutation = 'X'
            emp_join_date = "XX:XX:XXXX"
            emp_pro_salutation = 'X'
            emp_w_location = 'X'
            emp_pa_salutation = 'X'
            emp_father_name = 'X'
            confirm_date = "XX:XX:XXXX"
            emp_passport = 'X'
            emp_company = ''

        if self.ref_no:
            self.ref_no = str(self.ref_no).strip()
            ref_data = str(self.ref_no)
        else:
            ref_data = "X"

        if self.take_over_from_id:
            from_name = str(self.take_over_from_id.name_related)
            to_location = str(self.take_over_from_id.work_location_id)
            to_designation = str(self.take_over_from_id.job_id.name)
            to_area = str(self.take_over_from_id.work_location_id.store_zone_id.code)
        else:
            from_name = 'X'
            to_location = 'X'
            to_designation = 'X'
            to_area = 'X'
        if self.take_over_to_id:
            to_name = str(self.take_over_to_id.name_related)
        else:
            to_name = 'X'

        if self.current_date:
            current_date = str(datetime.strptime(str(self.current_date), '%Y-%m-%d').strftime('%B %d, %Y'))
        else:
            current_date = 'XX:XX:XXXX'

        if self.effective_date:
            e_date = str(datetime.strptime(str(self.effective_date), '%Y-%m-%d').strftime('%B %d, %Y'))
        else:
            e_date = 'XX:XX:XXXX'

        cc_data = ""
        if self.letter_cc:
            cc_list = str(self.letter_cc).split("\n")
            for r in cc_list:
                if cc_data == "":
                    cc_data = str(r)
                else:
                    cc_data += ", " + str(r)

            #cc_data = cc_data
        else:
            cc_data = "X"

        if self.agreement_date:
            ag_data = str(datetime.strptime(str(self.agreement_date), '%Y-%m-%d').strftime('%B %d, %Y'))
        else:
            ag_data = "XX:XX:XXXX"

        if self.up_to_date:
            upto_data = str(datetime.strptime(str(self.up_to_date), '%Y-%m-%d').strftime('%B %d, %Y'))
            next_year = str(int(str(self.up_to_date).split("-")[0]) + 1)
        else:
            upto_data = "XX:XX:XXXX"
            next_year = "X"

        if self.last_business_date:
            last_b_data = str(datetime.strptime(str(self.last_business_date), '%Y-%m-%d').strftime('%B %d, %Y'))
        else:
            last_b_data = "XX:XX:XXXX"

        if self.emp_position_id:
            emp_position = str(self.emp_position_id.name)
        else:
            emp_position = 'X'

        if self.address_no:
            emp_permanent_ads = str(self.address_no)
        else:
            emp_permanent_ads = 'X'

        if self.present_address_no:
            present_address = str(self.present_address_no)
        else:
            present_address = 'X'

        if self.report_department_id:
            report_to = str(self.report_department_id.name)
        else:
            report_to = 'X'

        disc = {
            '$emp_name': str(emp_name),
            '$emp_department': str(emp_department),
            '$emp_gender_salutation': emp_salutation,
            '$emp_designation': str(emp_designation),
            '$emp_company': emp_company,
            '$reference': ref_data,
            '$date': current_date,
            '$effective_date': e_date,
            '$cc': cc_data,
            '$agreement_date': ag_data,
            '$emp_joining_date': emp_join_date,
            '$emp_gender_pronoun': emp_pro_salutation,
            '$emp_job_location': emp_w_location,
            '$emp_pa_pronoun': emp_pa_salutation,
            '$upto_date': upto_data,
            '$next_year': next_year,
            '$last_business_date': last_b_data,
            '$emp_father_name': emp_father_name,
            '$emp_permanent_ad': emp_permanent_ads,
            '$emp_position': emp_position,
            '$confirm_date': confirm_date,
            '$handover_from': from_name,
            '$to_location': to_location,
            '$handover_to': to_name,
            '$to_designation': to_designation,
            '$area_code': to_area,
            '$emp_passport_no': emp_passport,
            '$report_department': report_to,
            '$present_address': present_address
        }
        if self.letter_template_id:
            final_data = self.replace_all(self.letter_template_id.description, disc)
            self.letter_template_details = final_data

    def replace_all(self, descriptions, dic):
        # for i, j in dic.iteritems(): #iteritems() used in python 2.7
        for i, j in dic.items():
            if j == False:
                j = str(j)
            descriptions = descriptions.replace(i, j)
        return descriptions

    def action_confirm(self):
        """ Send to confirm state """
        self.write({'state': 'confirm'})

    def action_approve(self):
        """ Send to approve state """
        self._update_pims_info()
        self.write({'state': 'approve'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        """ Send to cancel state """
        self.write({'state': 'cancel'})

    def action_print_with_head(self):
        """ Print letter with letter head """
        data = {}
        sql_data = """
            SELECT
                emp_letter.id AS letter_id,
                --emp.name_related AS emp_name,
                emp.name AS emp_name,
                job.name AS designation,
                emp_letter.letter_template_id AS template_id,
                emp_letter.ref_no AS reference,
                emp_letter.effective_date AS effective_date,
                emp_letter.state AS letter_state,
                hd.name AS department,
                emp_letter.current_date AS c_date,
                emp_letter.letter_cc AS cc,
                emp_letter.up_to_date AS upto_date,
                emp_letter.last_business_date AS business_date,
                emp_letter.letter_template_details AS details
            FROM hr_employee_letters AS emp_letter
                LEFT JOIN hr_employee AS emp ON emp.id = emp_letter.employee_id
                LEFT JOIN hr_job AS job on emp_letter.job_id = job.id
                LEFT JOIN hr_department AS hd on emp.department_id = hd.id
            WHERE emp_letter.id = %s                 
        """ % self.id

        self.env.cr.execute(sql_data)
        result = self.env.cr.dictfetchall()

        data['ids'] = result
        # return self.env['report'].get_action(self, 'custom_hr_employee_letters.emp_letter_report_qweb', data=data)
        return self.env.ref('custom_hr_employee_letters.report_employee_letter_w_head').report_action(self, data=data)

    def action_print_without_head(self):
        """ Print letter without letter head"""
        data = {}
        sql_data = """
            SELECT
                emp_letter.id AS letter_id,
                --emp.name_related AS emp_name,
                emp.name AS emp_name,
                job.name AS designation,
                emp_letter.letter_template_id AS template_id,
                emp_letter.ref_no AS reference,
                emp_letter.effective_date AS effective_date,
                emp_letter.state AS letter_state,
                hd.name AS department,
                emp_letter.current_date AS c_date,
                emp_letter.letter_cc AS cc,
                emp_letter.up_to_date AS upto_date,
                emp_letter.last_business_date AS business_date,
                emp_letter.letter_template_details AS details
            FROM hr_employee_letters AS emp_letter
                LEFT JOIN hr_employee AS emp ON emp.id = emp_letter.employee_id
                LEFT JOIN hr_job AS job on emp_letter.job_id = job.id
                LEFT JOIN hr_department AS hd on emp.department_id = hd.id
            WHERE emp_letter.id = %s                 
        """ % self.id

        self.env.cr.execute(sql_data)
        result = self.env.cr.dictfetchall()

        data['ids'] = result
        # return self.env['report'].get_action(self, 'custom_hr_employee_letters.emp_letter_wo_report_qweb', data=data)
        return self.env.ref('custom_hr_employee_letters.report_employee_letter_wo_head').report_action(self, data=data)

    def _update_pims_info(self):
        employee_id = self.employee_id
        if employee_id:
            # resource = self.env['resource.resource'].search([('user_id', '=', self.user_id.id)], limit=1)
            # employee = self.env['hr.employee'].search([('id', '=', self.employee_id.id)], limit=1)

            # create new Letters related employee
            letters_obj = self.env['hr.employee.letters.history']
            letters_obj.create({
                'employee_id': employee_id.id,
                'letter_name': self.letter_type,  # letter_template_id
                'letter_id': self.id
            })
