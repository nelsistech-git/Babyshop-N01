from odoo import fields, models, api, tools, _
from odoo.modules.module import get_module_resource
from dateutil.relativedelta import relativedelta


class InheritedHrApplicant(models.Model):
    """ Add employee & recruitment related fields in hr.employee & hr.recruitment model """
    _inherit = 'hr.applicant'

    @api.model
    def _get_default_country(self):
        id = ''
        contry_obj = self.env['res.country'].search([('code', '=ilike', 'bd')], limit=1)
        if contry_obj:
            id = contry_obj[0].id
        return id

    @api.model
    def _default_image(self):
        image_path = get_module_resource('custom_hr_recruitment', 'static/src/img', 'default_image.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    image = fields.Binary("Photo",
                          help="This field holds the image used as photo for the employee, limited to 1024x1024px.")
    fam_father = fields.Char(string="Father's Name")
    fam_father_occupation = fields.Char("Father's Occupation")
    fam_mother = fields.Char("Mother's Name")
    fam_mother_occupation = fields.Char("Mother's Occupation")
    fam_spouse = fields.Char(string="Spouse's Name")
    fam_spouse_occupation = fields.Char(string="Spouse's Occupation")
    fam_spouse_qualification = fields.Char(string="Spouse's Qualification")
    fam_spouse_organization = fields.Char(string="Spouse's Organization")
    fam_spouse_designation = fields.Char(string="Spouse's Designation")

    present_address = fields.Text(string='Present Address')
    p_address_id = fields.Text(string='Permanent Address')

    present_address_contact_no = fields.Char(string='Present Address Contact No')
    p_address_id_contact_no = fields.Char(string='Permanent Address Contact No')

    present_address_email = fields.Char(string='Present Address Email')
    p_address_id_email = fields.Char(string='Permanent Address Email')

    contact_no = fields.Char(string="Contact Number")
    email_personal = fields.Char(string='Email(Personal)')
    birthday = fields.Date('Date of Birth', groups="hr.group_hr_user")

    e_contact_no = fields.Char(string="Emergency Contact")  # emergency contact
    r_e_contact_no = fields.Char(string="Relation w/emergency contact")  # relation with emergency contact

    place_of_birth = fields.Char('Place of Birth')
    age = fields.Char(string='Age', readonly=True, compute='_compute_age')
    country_id = fields.Many2one('res.country', string='Nationality (Country)', default=_get_default_country)

    religion = fields.Selection([
        ('islam', 'Islam'), ('sanatan', ' Sanatan'),
        ('buddhism', 'Buddhism'), ('christianity', 'Christianity'),
        ('others', 'Others')], string="Religion", default='')

    nid = fields.Char(string="National ID No.")
    passport_id = fields.Char(string='Passport No.', help='Passport No. (if any)')
    driving_license = fields.Char(string='Driving License (if any)', help='Driving License (if any)')

    blood_group = fields.Selection([
        ('o_neg', 'O-'), ('o_pos', 'O+'), ('b_neg', 'B-'), ('b_pos', 'B+'),
        ('a_neg', 'A-'), ('a_pos', 'A+',), ('ab_neg', 'AB-'), ('ab_pos', 'AB+')
    ], string="Blood Group", default='')
    height = fields.Char(string="Height (in Feet & Inches)")
    weight = fields.Integer(string="Weight (in Kilograms)")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status')
    marriage_date = fields.Date('Date of Marriage')
    no_of_male_children = fields.Integer(string="No. of Male Children")
    no_of_female_children = fields.Integer(string="No. of Female Children")

    dependent_ids = fields.One2many('hr.applicant.dependent', 'applicant_id', help='Dependents')
    sibling_ids = fields.One2many('hr.applicant.siblings', 'applicant_id',
                                  'Name, Age, Occupation & Contact Details of Siblings',
                                  help='Name, Age, Occupation & Contact Details of Siblings')
    medical_info = fields.Text(string='Medical Information')

    academic_ids = fields.One2many('hr.applicant.academic', 'applicant_id', 'Education Details',
                                   help='Please start with the most recent')
    professional_ids = fields.One2many('hr.applicant.training', 'applicant_id', string="Professional Qualifications",
                                       help='Technical, Professional or Occupational Qualifications or Training. Please start with the most recent.')
    language_ids = fields.One2many('hr.applicant.languages', 'applicant_id', string="Knowledge of language")
    experience_ids = fields.One2many('hr.applicant.experience', 'applicant_id', string="Professional Experience")
    extra_curri_ids = fields.One2many('hr.applicant.activities', 'applicant_id',
                                      string="Extra Curricular Activities & Interests")

    housing_status = fields.Selection(
        string='Housing Status',
        selection=[('own', 'Own Home'), ('rent', 'Rent'), ('dorm', 'Dormitory'), ('other', 'Others')],
        help='Type of accommodation', default='')

    is_previous_applicant = fields.Boolean('Previous Applied?',
                                           help="Have you previously applied for any employment in the company?",
                                           default=False)
    previous_applied_post = fields.Char(string="Previously Applied Position")
    previous_applied_year = fields.Char(string="Year")

    known_people_ids = fields.One2many('hr.applicant.relatives', 'applicant_id',
                                       string="Relatives, friends or known people working in the company",
                                       help="Relatives include spouse, son, daughter, step son, step daughter, full brother and sister, first line of in-laws, uncle, aunty, nephew, niece and direct grand children.")

    known_people_outside_ids = fields.One2many('hr.applicant.relatives.outside', 'applicant_id',
                                               string="Relatives, friends or known people working in other than the company",
                                               help="Relatives include spouse, son, daughter, step son, step daughter, full brother and sister, first line of in-laws, uncle, aunty, nephew, niece and direct grand children.")

    reference_1 = fields.Text(string="Reference 1")
    reference_2 = fields.Text(string="Reference 2")
    additional_info = fields.Text(string="Additional Information")

    signature = fields.Binary(string="Signature of Applicant", help="Select your signature image")
    application_date = fields.Date(string="Date")

    @api.onchange('nid')
    def _remove_space_nid(self):
        for r in self:
            if r.nid:
                r.nid = str(r.nid).strip()

    @api.onchange('passport_id')
    def _remove_space_passport_id(self):
        for r in self:
            if r.passport_id:
                r.passport_id = str(r.passport_id).strip()

    # @api.multi
    @api.depends('birthday')
    def _compute_age(self):
        for record in self:
            if record.birthday:
                t_age = relativedelta(
                    fields.Date.from_string(fields.Date.today()),
                    fields.Date.from_string(record.birthday))
                record.age = "{y} years, {m} months, {d} days".format(y=t_age.years, m=t_age.months, d=t_age.days)
            else:
                record.age = 0

    # @api.multi
    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        employee = False
        for applicant in self:
            address_id = contact_name = False
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])['contact']
                contact_name = applicant.partner_id.name_get()[0][1]
            if applicant.job_id and (applicant.partner_name or contact_name):
                applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
                resume_line_list = []
                # experience_list = []
                if applicant.experience_ids:
                    for experience_row in applicant.experience_ids:
                        row = {
                            'description': experience_row.name,
                            # 'expire': experience_row.expire,
                            'date_start': experience_row.start_date,
                            'date_end': experience_row.end_date,
                            'name': experience_row.institute_id,
                            # 'location': experience_row.location,
                            'line_type_id': 1
                            # 'serv_leng': experience_row.serv_leng
                        }
                        resume_line_list.append((0, 0, row))

                # academic_list = []
                if applicant.academic_ids:
                    for aca_row in applicant.academic_ids:
                        row = {
                            'name': aca_row.exam_name,
                            # 'expire': aca_row.expire,
                            'passing_year': aca_row.passing_year,
                            'institute_id': aca_row.institute_id,
                            'date_start': aca_row.start_date,
                            'date_end': aca_row.end_date,
                            'description': aca_row.study_field,
                            'result': aca_row.result,
                            'line_type_id': 2
                        }
                        resume_line_list.append((0, 0, row))

                # Qualification & Training Details
                # qualification_list = []
                # training_list = []
                if applicant.professional_ids:
                    for pro_row in applicant.professional_ids:
                        # Qualifications:
                        if pro_row.category == '1':
                            qualification_row = {
                                'name': pro_row.certification,
                                'date_start': pro_row.start_date,
                                'passing_year': pro_row.passing_year,
                                'result': pro_row.training_result,
                                'institute_id': pro_row.institute_id,
                                'description': pro_row.location,
                                'line_type_id': 4
                            }
                            resume_line_list.append((0, 0, qualification_row))
                        else:
                            # Trainings
                            training_row = {
                                'name': pro_row.certification,
                                # 'type_cer': pro_row.type_cer,
                                # 'training_mode': pro_row.training_mode,
                                # 't_costing': pro_row.t_costing,
                                # 'expire': pro_row.expire,
                                'date_start': pro_row.start_date,
                                'passing_year': pro_row.passing_year,
                                # 'end_date': pro_row.end_date,
                                'institute_id': pro_row.institute_id,
                                'result': pro_row.training_result,
                                # 'location': pro_row.location
                                'description': pro_row.type_cer,
                                'line_type_id': 3
                            }
                            resume_line_list.append((0, 0, training_row))

                employee = self.env['hr.employee'].create(
                    {
                        'image_1920': applicant.image,
                        'name': applicant.partner_name or contact_name,
                        'job_id': applicant.job_id.id,
                        # 'address_home_id': address_id,
                        'department_id': applicant.department_id.id or False,
                        'company_id': applicant.company_id.id or False,
                        # 'address_id': applicant.company_id and applicant.company_id.partner_id and applicant.company_id.partner_id.id or False,
                        # 'work_email': applicant.department_id and applicant.department_id.company_id and applicant.department_id.company_id.email or False,
                        # 'work_phone': applicant.department_id and applicant.department_id.company_id and applicant.department_id.company_id.phone or False,
                        'fam_father': applicant.fam_father,
                        'fam_mother': applicant.fam_mother,
                        'marital': applicant.marital,
                        'fam_spouse': applicant.fam_spouse,
                        'gender': applicant.gender,
                        'birthday': applicant.birthday,
                        'age': applicant.age,
                        'place_of_birth': applicant.place_of_birth,
                        'country_id': applicant.country_id.id,
                        'religion': applicant.religion,
                        'present_address': applicant.present_address,
                        'p_address_id': applicant.p_address_id,
                        'contact_no': applicant.contact_no,
                        'email_personal': applicant.email_personal,
                        'e_contact_no': applicant.e_contact_no,
                        'r_e_contact_no': applicant.r_e_contact_no,
                        'passport_id': applicant.passport_id,
                        'nid': applicant.nid,
                        'resume_line_ids': resume_line_list
                        # employee_skill_ids:

                        # 'experience_ids': experience_list,
                        # 'academic_ids': academic_list,
                        # 'professional_ids': qualification_list,
                        # 'certification_ids': training_list
                    }
                )

                applicant.write({'emp_id': employee.id})
                if applicant.job_id:
                    applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
                    applicant.job_id.message_post(
                        body=_(
                            'New Employee %s Hired') % applicant.partner_name if applicant.partner_name else applicant.name,
                        subtype="hr_recruitment.mt_job_applicant_hired")
                applicant.message_post_with_view(
                    'hr_recruitment.applicant_hired_template',
                    values={'applicant': applicant},
                    subtype_id=self.env.ref("hr_recruitment.mt_applicant_hired").id)

            employee_action = self.env.ref('hr.open_view_employee_list')
            dict_act_window = employee_action.read([])[0]
            dict_act_window['context'] = {'form_view_initial_mode': 'edit'}
            dict_act_window['res_id'] = employee.id
            return dict_act_window

    # @api.multi
    def action_applicant_print(self, data):

        # datas = self.action_applicant_sql(data)
        if self:
            applicant_id = self.id
            applicant_list = []

            applicant_list.append(applicant_id)
            data['ids'] = applicant_list

        return self.env['report'].get_action(self, 'custom_hr_recruitment.report_hr_applicant_qweb', data=data)

    # @api.multi
    def action_applicant_sql(self, data):
        """ Print Filled Application form """

        # raise UserError('Pew pew')

        application_sql = """
            SELECT
                *
            FROM
                hr_applicant
            WHERE
                id = %s
            LIMIT 1
        """ % (self.id)

        self.env.cr.execute(application_sql)
        result = self.env.cr.dictfetchall()
        data['ids'] = result

        # data['other'] = {
        #     'form_no': self.rec_no,
        #     'requisition_dept': self.rec_dept.name
        # }
        return data
        # return self.env['report'].get_action(self, 'custom_hr_recruitment.hr_applicant_report', data=data)
