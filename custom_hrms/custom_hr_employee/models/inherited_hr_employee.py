from odoo import api, fields, models, exceptions, _
from odoo.addons.helper import validator
from datetime import datetime, timedelta
from odoo.osv import expression
from dateutil.relativedelta import relativedelta

GENDER_SELECTION = [('male', 'Male'),
                    ('female', 'Female'),
                    ('other', 'Other')]


class HrEmployeeFamilyInfo(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.family'
    _rec_name = 'employee_id'
    _description = 'HR Employee Family'

    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee')
    relation_id = fields.Many2one('hr.employee.relation', string="Relation", help="Relationship with the employee")
    member_name = fields.Char(string='Name')
    member_contact = fields.Char(string='Contact No')
    birth_date = fields.Date(string="DOB")


class HrEmployeeEducationInfo(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.education.info'
    _description = 'HR Employee Education'

    employee_id = fields.Many2one('hr.employee', string="Employee", help='Select corresponding Employee')
    degree = fields.Char(string='Degree')
    group = fields.Char(string='Group')
    passing_year = fields.Char(string='Passing Year')
    result = fields.Char(string='Result')
    attachment_ids = fields.Many2many('ir.attachment', 'certificate_id', string="Scan Copy", help="Attach files here")


class ResourceCalendarHREmployee(models.Model):
    _inherit = "resource.calendar"

    is_default = fields.Boolean(default=False)
    is_over_ride_day = fields.Boolean(default=False, string="Over-Ride Day/Night Shift")
    short_name = fields.Char(string='Shift Short Name', default='', help='Shift Example: A or B or C etc')
    #------- for over-ride
    check_in_start = fields.Float(string="Check-in Start (*)", default=0.00)
    check_in_end = fields.Float(string="Check-in End", default=0.00)
    check_out_start = fields.Float(string="Check-out Start", default=0.00)
    check_out_end = fields.Float(string="Check-out End", default=0.00)

    #---------------
    active = fields.Boolean(string='Active', default=True)
    hour_from_per_day_m = fields.Float(string='Morning Work From (*)',
                                       help="Start and End time of working. A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to_per_day_m = fields.Float(string='Morning Work To (*)')

    hour_from_per_day_e = fields.Float(string='Afternoon Work From (*)',
                                       help="Start and End time of working. A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to_per_day_e = fields.Float(string='Afternoon Work To (*)')

    # @api.onchange('hour_from_per_day_m', 'hour_to_per_day_m', 'hour_from_per_day_e', 'hour_to_per_day_e')
    # def _onchange_hours_from_to(self):
    #     # avoid negative or after midnight
    #     self.hour_from_per_day_m = min(self.hour_from_per_day_m, 23.99)
    #     self.hour_from_per_day_m = max(self.hour_from_per_day_m, 0.0)
    #     self.hour_from_per_day_e = min(self.hour_from_per_day_e, 23.99)
    #     self.hour_from_per_day_e = max(self.hour_from_per_day_e, 0.0)
    #
    #     # avoid wrong order
    #     self.hour_from_per_day_e = max(self.hour_from_per_day_e, self.hour_from_per_day_m)

    @api.depends('name', 'short_name')
    def _compute_display_name(self):
        for rec in self:
            name = rec.name or ''
            short_name = rec.short_name
            if short_name:
                rec.display_name = "%s [%s]" % (short_name, name)
            else:
                rec.display_name = name


class ResourceCalendarAttendanceHREmployee(models.Model):
    _inherit = "resource.calendar.attendance"

    @api.onchange('hour_from', 'hour_to')
    def _onchange_hours(self):
        pass
        # avoid negative or after midnight
        # self.hour_from = min(self.hour_from, 23.99)
        # self.hour_from = max(self.hour_from, 0.0)
        # self.hour_to = min(self.hour_to, 24)
        # self.hour_to = max(self.hour_to, 0.0)
        #
        # # avoid wrong order
        # self.hour_to = max(self.hour_to, self.hour_from)


class InheritedHrEmployee(models.Model):
    """ Add some fields in hr.employee model"""
    _inherit = 'hr.employee'

    is_engineer = fields.Boolean(string='Is Engineer?', groups="hr.group_hr_user")

    @api.model
    def _get_default_country(self):
        id = ''
        contry_obj = self.env['res.country'].search([('code', '=ilike', 'bd')], limit=1)
        if contry_obj:
            id = contry_obj[0].id
        return id

    @api.model
    def _get_default_work_location(self):
        loc_obj = self.env['stock.location'].search([('is_work_loc', '=', True), ('state', '=', 'done'), ('is_work_loc_default', '=', True)], order="id asc", limit=1)
        if loc_obj:
            return loc_obj.id
        else:
            return ''

    @api.onchange('resource_calendar_id')
    def _onchange_resource_calendar_id(self):
        if self.resource_calendar_id:
            self.tz = self.resource_calendar_id.tz

    @api.onchange('initial_employment_date', 'probation_period')
    def _get_end_date(self):
        for et in self:
            if et.initial_employment_date and et.probation_period:
                initial_employment_date = et.initial_employment_date
                if et.probation_period.unit == 'years':
                    date_of_confirmation = initial_employment_date + relativedelta(years=et.probation_period.length)
                elif et.probation_period.unit == 'months':
                    date_of_confirmation = initial_employment_date + relativedelta(months=et.probation_period.length)
                elif et.probation_period.unit == 'days':
                    date_of_confirmation = initial_employment_date + relativedelta(days=et.probation_period.length)
                elif et.probation_period.unit == 'weeks':
                    date_of_confirmation = initial_employment_date + relativedelta(weeks=et.probation_period.length)
                else:
                    date_of_confirmation = initial_employment_date + relativedelta(days=et.probation_period.length)

                et.date_of_confirmation = date_of_confirmation.strftime("%Y-%m-%d")
                et.forecasting_confirmation = date_of_confirmation.strftime("%Y-%m-%d")

            # if et.initial_employment_date and et.probation_period:
            #
            #     initial_employment_date = et.initial_employment_date
            #     date_of_confirmation = initial_employment_date + relativedelta(months=et.probation_period.length)
            #     et.date_of_confirmation = date_of_confirmation.strftime("%Y-%m-%d")
            else:
                et.date_of_confirmation = None
                et.forecasting_confirmation = None

    def cron_sync_probation_to_permanent(self):
        search_rslt = self.env['hr.employee'].search(
            [('date_of_confirmation', '<=', datetime.now().date()), ('employee_type_id.is_probation', '=', True)])
        employee_type = self.env['hr.employee.type'].search([('is_permanent', '=', True)], limit=1)

        users = self.env.ref('hr.group_hr_manager').users

        if users:
            notification_ids = [(0, 0, {
                'res_partner_id': user.partner_id.id,
                'notification_type': 'inbox'
            }) for user in users if users]
        else:
            notification_ids = []

        for rec in search_rslt:
            rec.employee_type_id = employee_type.id

            self.env['mail.message'].sudo().create({
                'message_type': "notification",
                'body': "'%s' has become a permanent employee on %s" % (rec.name, rec.date_of_confirmation),
                'subject': "Permanent Employee Notification",
                'partner_ids': [(4, rec.address_home_id.id)],
                'notification_ids': notification_ids,
                'author_id': self.env.user.partner_id and self.env.user.partner_id.id
            })

    # emp_attendance_id = fields.Char(string='Attendance ID'8, help='The ID Number of the user/employee in the device storage', tracking=True)

    # ID
    identification_id = fields.Char(string='Master ID', groups="hr.group_hr_user",
                                    help="Based on YYYY-MM-DD HH:MM")  # required=True, , unique=False; It replaced from main table
    id_card_no = fields.Char(string="Employee ID", groups="hr.group_hr_user")
    door_card_no = fields.Char(string="Door Card No", groups="hr.group_hr_user")

    # for job grade
    job_grade = fields.Many2one("hr.job.grade", string="Job Grade", ondelete='restrict', groups="hr.group_hr_user")
    grade_type = fields.Many2one("hr.job.grade.type", string="Grade Type", ondelete='restrict',
                                 groups="hr.group_hr_user")
    job_level = fields.Many2one("hr.job.level", string="Job Level", ondelete='restrict', groups="hr.group_hr_user")

    # for family
    fam_father = fields.Char(string="Father's Name", groups="hr.group_hr_user")
    fam_father_occupation = fields.Char("Father's Occupation", groups="hr.group_hr_user")
    fam_father_mobile = fields.Char("Father's Phone", groups="hr.group_hr_user")
    fam_mother = fields.Char("Mother's Name", groups="hr.group_hr_user")
    fam_mother_occupation = fields.Char("Mother's Occupation", groups="hr.group_hr_user")
    fam_mother_mobile = fields.Char("Mother's Phone", groups="hr.group_hr_user")
    fam_spouse = fields.Char(string="Spouse's Name", groups="hr.group_hr_user")
    fam_spouse_occupation = fields.Char(string="Spouse's Occupation", groups="hr.group_hr_user")
    fam_spouse_mobile = fields.Char(string="Spouse's Phone", groups="hr.group_hr_user")
    fam_spouse_qualification = fields.Char(string="Spouse's Qualification", groups="hr.group_hr_user")
    fam_spouse_organization = fields.Char(string="Spouse's Organization", groups="hr.group_hr_user")
    fam_spouse_designation = fields.Char(string="Spouse's Designation", groups="hr.group_hr_user")
    guardian_name = fields.Char(string="Guardian Name", groups="hr.group_hr_user")

    no_of_male_children = fields.Integer(string="No. of Male Children", groups="hr.group_hr_user")
    no_of_female_children = fields.Integer(string="No. of Female Children", groups="hr.group_hr_user")

    # All many2one fields
    # category_ids = fields.Many2one('hr.employee.category', string='Employee Type')
    # not_used
    # employee_type = fields.Selection(string='Undefined',
    #                                  selection=[('permanent', 'Permanent'), ('probation', 'Probation'),
    #                                             ('package', 'Package')], default='permanent', groups="hr.group_hr_user")
    employee_type_id = fields.Many2one('hr.employee.type', string='Employee Type.', groups="hr.group_hr_user")
    is_probation = fields.Boolean(string="Is Probation?", related='employee_type_id.is_probation')
    is_permanent = fields.Boolean(string="Is Permanent?", related='employee_type_id.is_permanent')
    is_contractual = fields.Boolean(string="Is Contractual?", related='employee_type_id.is_contractual')
    is_casual = fields.Boolean(string="Is Casual?", related='employee_type_id.is_casual')
    is_part_time = fields.Boolean(string="Is Part Time?", related='employee_type_id.is_part_time')
    is_deny_pf = fields.Boolean(string="Is Deny PF?", related='employee_type_id.is_deny_pf')

    passport_id = fields.Char(string='Passport No', groups='hr.group_hr_user')
    reporting_body = fields.Many2one('hr.job', string="Reporting Designation", related='parent_id.job_id',
                                     groups="hr.group_hr_user")
    parent_dept_id = fields.Many2one('hr.department', string="Parent Department", related='department_id.parent_id',
                                     groups="hr.group_hr_user")
    dependent_ids = fields.One2many('hr.employee.dependent', 'employee_id', help='Dependents')
    sibling_ids = fields.One2many('hr.employee.siblings', 'employee_id',
                                  'Name, Age, Occupation & Contact Details of Siblings',
                                  help='Name, Age, Occupation & Contact Details of Siblings')
    extra_curri_ids = fields.One2many('hr.employee.activities', 'employee_id',
                                      string="Extra Curricular Activities & Interests")

    medical_info = fields.Text(string='Medical Information', groups="hr.group_hr_user")

    housing_status = fields.Selection(
        string='Housing Status',
        selection=[('own', 'Own Home'), ('rent', 'Rent'), ('dorm', 'Dormitory'), ('other', 'Others')],
        help='Type of accommodation', default='', groups="hr.group_hr_user")

    managerial_type = fields.Selection(
        string='Employee Managerial Type',
        selection=[('management', 'Management'), ('non_management', 'Non Management'), ('third_party', 'Third Party')],
        help='Employee Managerial Type', default='', groups="hr.group_hr_user")

    is_previous_applicant = fields.Boolean('Previous Applied?',
                                           help="Have you previously applied for any employment in This Company?",
                                           default=False, groups="hr.group_hr_user")
    previous_applied_post = fields.Char(string="Previously Applied Position", groups="hr.group_hr_user")
    previous_applied_year = fields.Char(string="Year", groups="hr.group_hr_user")

    known_people_ids = fields.One2many('hr.employee.relatives', 'employee_id',
                                       string="Relatives, friends or known people working in this company.",
                                       help="Relatives include spouse, son, daughter, step son, step daughter, full brother and sister, first line of in-laws, uncle, aunty, nephew, niece and direct grand children.")

    known_people_outside_ids = fields.One2many('hr.employee.relatives.outside', 'employee_id',
                                               string="Relatives, friends or known people working in other company",
                                               help="Relatives include spouse, son, daughter, step son, step daughter, full brother and sister, first line of in-laws, uncle, aunty, nephew, niece and direct grand children.")

    application_date = fields.Date(string="Date", groups="hr.group_hr_user")

    fax_no = fields.Char(string="Fax No(Official)", groups="hr.group_hr_user")
    # concern_unit = fields.Many2one('res.company', string='Concern Unit')

    company_unit_id = fields.Many2one('company.unit', string="Company Unit", ondelete='restrict', groups="hr.group_hr_user")
    user_work_location_id = fields.Many2one('stock.location', string="Job Location", ondelete='restrict',
                                       domain=[('is_work_loc', '=', True), ('state', '=', 'done')], groups="hr.group_hr_user", default=lambda self: self._get_default_work_location())
    inter_company_id = fields.Many2one("internal.company", string="Inter Company", ondelete="restrict", groups="hr.group_hr_user", related="user_work_location_id.inter_company_id", store=True)
    sales_location_id = fields.Many2one("region.list", string="Sales Location", ondelete="restrict", groups="hr.group_hr_user")

    # shift = fields.Many2one('resource.calendar', string="Shift")

    religion = fields.Selection([('islam', 'Islam'), ('sanatan', ' Sanatan'),
                                 ('buddhism', 'Buddhism'), ('christianity', 'Christianity'), ('others', 'Others')],
                                string="Religion", default='', groups="hr.group_hr_user")
    blood_group = fields.Selection(
        [('o_neg', 'O-'), ('o_pos', 'O+'), ('b_neg', 'B-'), ('b_pos', 'B+'), ('a_neg', 'A-'), ('a_pos', 'A+',),
         ('ab_neg', 'AB-'), ('ab_pos', 'AB+')], string="Blood Group", default='', groups="hr.group_hr_user")
    height = fields.Char(string="Height (in Feet & Inches)", groups="hr.group_hr_user")
    weight = fields.Integer(string="Weight (in Kilograms)", groups="hr.group_hr_user")
    tax_id = fields.Char(string="TIN", groups="hr.group_hr_user")

    present_address = fields.Text(string='Present Address', groups="hr.group_hr_user")
    p_address_id = fields.Text(string='Permanent Address', groups="hr.group_hr_user")
    # address_home_id = fields.Text(string='Present Address')
    address_home_id = fields.Many2one('res.partner', string='Home Address')
    country_id = fields.Many2one('res.country', string='Nationality (Country)', default=_get_default_country,
                                 ondelete='restrict', groups="hr.group_hr_user")
    email_personal = fields.Char(string='Email(Personal)', groups="hr.group_hr_user")
    contact_no = fields.Char(string="Mobile (Personal)", groups="hr.group_hr_user", copy=False)
    e_contact_no = fields.Char(string="Emergency Contact", groups="hr.group_hr_user")  # not used
    r_e_contact_no = fields.Char(string="Relation", groups="hr.group_hr_user")  # not used
    nid = fields.Char(string="NID", groups="hr.group_hr_user")

    job_id = fields.Many2one('hr.job', 'Designation',
                             domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                             groups="hr.group_hr_user")
    parent_id = fields.Many2one('hr.employee',
                                'Reporting Manager')  # ,` domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]"
    coach_id = fields.Many2one('hr.employee', 'Supervisor',
                               groups="hr.group_hr_user")  # domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",

    #     p_bank_account_no = fields.Many2one('res.partner.bank', string='Bank A/C(Personal)',
    #                                         help='Employee Personal Account', groups='hr.group_hr_user')
    #     p_bank_name = fields.Char(string="Bank Name(Personal)", help="Bank Name of personal A/C")
    #     p_name_of_nominee = fields.Char(string="NomineeName(Personal)", help="Nominee of Personal A/C")
    #     bank_account_id = fields.Many2one('res.partner.bank', string='Bank A/C(Salary)',
    #                                       help='Employee salary account', groups='hr.group_hr_user')

    p_bank_name = fields.Many2one('hr.bank', string="Personal Bank Name", help="Personal A/C Bank Name", ondelete='restrict',
                                  groups="hr.group_hr_user")
    p_bank_account_no = fields.Char(string='Account No',
                                    help='Personal Account No', groups="hr.group_hr_user")
    p_account_type = fields.Selection([('normal', 'Normal'), ('salary', 'Salary')],
                                      string="Personal Account Type", default='', help="Personal A/C Type",
                                      groups="hr.group_hr_user")
    p_account_holder = fields.Char(string="Personal Account Holder", help="Personal A/C Account Holder",
                                   groups="hr.group_hr_user")
    p_name_of_nominee = fields.Char(string="Nominee Name", help="Personal A/C Nominee Name",
                                    groups="hr.group_hr_user")
    # p_relation_with_nominee = fields.Char(string="Relation(Nominee)", help="Personal A/C Relation with Nominee")
    p_relation_with_nominee = fields.Many2one('hr.employee.contact.relation', string="Relation(Nominee)",
                                              help="Personal A/C Relation with Nominee", ondelete='restrict',
                                              groups="hr.group_hr_user")

    #     bank_account_id = fields.Many2one('res.partner.bank', string='Bank A/C(Salary)',
    #                                       help='Employee salary account', groups='hr.group_hr_user')
    disbursement_type = fields.Selection([
        ('bank', 'Bank'),
        ('cash', 'Cash'),
        ('bank_cash', 'Bank & Cash')
    ], string="Payment Type", groups="hr.group_hr_user")

    s_bank_name = fields.Many2one('hr.bank', string="Salary Bank Name", help="Salary A/C Bank Name",
                                  ondelete='restrict', groups="hr.group_hr_user")
    s_bank_account_no = fields.Char(string='Salary Account No',
                                    help='Salary Account No', groups="hr.group_hr_user")
    s_account_type = fields.Selection([('normal', 'Normal'), ('salary', 'Salary')],
                                      string="Salary Account Type", default='', help="Salary A/C Type",
                                      groups="hr.group_hr_user")
    s_account_holder = fields.Char(string="Salary Account Holder", help="Salary A/C Account Holder",
                                   groups="hr.group_hr_user")
    s_name_of_nominee = fields.Char(string='Nominee Name', help="Salary A/C Nominee Name",
                                    groups="hr.group_hr_user")
    # s_relation_with_nominee = fields.Char(string="Relation(Nominee)", help="Salary A/C Relation with Nominee")
    s_relation_with_nominee = fields.Many2one('hr.employee.contact.relation', string="Relation (Nominee)",
                                              help="Salary A/C Relation with Nominee", groups="hr.group_hr_user")

    s_occupation_of_nominee = fields.Char(string="Nominee Occupation", help="Personal A/C Nominee Occupation",
                                          groups="hr.group_hr_user")
    s_contact_email_of_nominee = fields.Char(string="Nominee Contact No. & Email",
                                             help="Personal A/C Nominee Contact No. & Email",
                                             groups="hr.group_hr_user")
    s_office_address_of_nominee = fields.Char(string="Nominee office Address",
                                              help="Personal A/C Nominee Address",
                                              groups="hr.group_hr_user")
    s_nominee_image = fields.Binary(string="Nominee Image", help="Select your Nominee image", groups="hr.group_hr_user")
    # date_of_joining = fields.Date("Date of Joining")
    probation_period = fields.Many2one('hr.probation.period', string="Probation Period", ondelete='restrict',
                                       groups="hr.group_hr_user")
    forecasting_confirmation = fields.Date("Forecasting Confirmation", groups="hr.group_hr_user", help="Forecasting confirmation")
    date_of_confirmation = fields.Date("Date of Confirmation", groups="hr.group_hr_user")
    start_date_of_contract = fields.Date("Contract Start Date", groups="hr.group_hr_user")
    end_date_of_contract = fields.Date("Contract End Date", groups="hr.group_hr_user")
    job_description = fields.Text(string='Job Descriptions', help="Summery of job responsibility",
                                  groups="hr.group_hr_user")

    signature = fields.Binary(string="Signature", help="Select your signature image", groups="hr.group_hr_user")

    reference = fields.Text(string="Reference", groups="hr.group_hr_user")

    age = fields.Char(
        string='Age',
        readonly=True,
        compute='_compute_age'
        , groups="hr.group_hr_user")

    initial_employment_date = fields.Date(
        string='Date of Joining',
        help='Date of first employment if it was before the start of the '
             'first contract in the system.', groups="hr.group_hr_user")

    length_of_service = fields.Char(
        string='Length of Service',
        compute='_compute_service_length', groups="hr.group_hr_user")

    remaining_confirmation_day = fields.Char(
        string='Remaining Confirmation Day',
        compute='_compute_remaining_confirmation_days')

    remaining_confirmation_day_forecast = fields.Char(
        string='Forecasting Remaining Day',
        compute='_compute_remaining_confirmation_days_forecast', help="Forecasting confirmation")

    em_contact_ids = fields.One2many('hr.emergency.contacts', 'employee_id', string="Emergency Contacts",
                                     groups="hr.group_hr_user")
    home_town_id = fields.Many2one('district', string="District", ondelete='restrict', help="Home Town",
                                   groups="hr.group_hr_user")
    home_division_id = fields.Many2one('division', string="Division", ondelete='restrict', groups="hr.group_hr_user")
    home_upazila_id = fields.Many2one('district.thana', string="Upazila/Thana", ondelete='restrict', groups="hr.group_hr_user")
    home_postcode_id = fields.Many2one('postcode', string="Postcode", ondelete='restrict', groups="hr.group_hr_user")
    # home_town = fields.Char('Home Town')
    driving_license = fields.Char(string='Driving License', groups="hr.group_hr_user")
    document_line_ids = fields.One2many('hr.employee.document.line', 'master_id', string='Document Line Ids',
                                        groups="hr.group_hr_user")
    letter_ids = fields.One2many('hr.employee.letters.history', 'employee_id', string="Letters",
                                 groups="hr.group_hr_user")

    punishments = fields.Many2many(string="Punishments", comodel_name="hr.punishments", compute='_compute_field_name')

    device_user_id = fields.Char(string='Biometric Device ID',
                                 help='The ID Number of the user/employee in the device storage', groups="hr.group_hr_user")

    employee_category = fields.Selection([
        ('staff', 'Staff'),
        ('worker', 'Worker'),
    ], string='Employee Category', default='', groups="hr.group_hr_user")

    education_last = fields.Char(string='Education (Last)',
                                 help='Last education name', groups="hr.group_hr_user")

    is_separated = fields.Boolean(string="Is Separated?", default=False, help="If checked then employee has resigned/fired/etc", groups="hr.group_hr_user")
    separation_date = fields.Date('Separation Date', help="Date of the Separation", groups="hr.group_hr_user")
    sbu_unit_id = fields.Many2one('hr.sbu.unit', string='Business Unit', groups="hr.group_hr_user")
    is_bod = fields.Boolean(string='Is Board of Director?', default=False, groups="hr.group_hr_user")
    emp_type = fields.Selection([('management', 'Management'), ('worker', 'Worker'), ('staff', 'Staff')], default='worker', string='Employment Type',
                                groups="hr.group_hr_user")
    contract_created = fields.Boolean(default=False, groups="hr.group_hr_user")

    @api.model
    def __def_resource_calendar(self):
        resource_id = self.env['resource.calendar'].search([('is_default', '=', True)], order="id asc", limit=1)
        if resource_id:
            return resource_id.id
        else:
            return self.env.company.resource_calendar_id.id

    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours', copy=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", default=lambda self: self.__def_resource_calendar())


    @api.constrains('work_email')
    def _check_unique_constraint_work_email(self):
        if self.work_email:
            msg = 'Work Email "%s"' % self.work_email
            envobj = self.env['hr.employee']
            conditionlist = [('work_email', '=', self.work_email)]
            validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.constrains('contact_no')
    def _check_unique_constraint_contact_no(self):
        if self.contact_no:
            msg = 'Mobile (Personal) "%s"' % self.contact_no
            envobj = self.env['hr.employee']
            conditionlist = [('contact_no', '=', self.contact_no), ('active', '=', True)]
            validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.constrains('contact_no', 'mobile_phone', 'work_phone')
    def _check_contact_no_constraints(self):
        for rec in self:
            if rec.contact_no:
                if not (rec.contact_no.startswith("01") and len(rec.contact_no) == 11):
                    raise exceptions.ValidationError(
                        _('Mobile (Personal) is not valid. It should be unique, start with 01, and 11 digits. E.g. 01842647664'))
            else:
                pass
            if rec.mobile_phone:
                if not (rec.mobile_phone.startswith("01") and len(rec.mobile_phone) == 11):
                    raise exceptions.ValidationError(
                        _('Work Mobile is not valid. It should be unique, start with 01, and 11 digits. E.g. 01842647664'))
            else:
                pass
            if rec.work_phone:
                if not (rec.work_phone.startswith("01") and len(rec.work_phone) == 11):
                    raise exceptions.ValidationError(
                        _('Work Phone is not valid. It should be unique, start with 01, and 11 digits. E.g. 01842647664'))
            else:
                pass

    def _compute_field_name(self):
        for records in self:
            # import pdb; pdb.set_trace()
            records.sudo().punishments = [(6, 0, [i.id for i in self.env['hr.punishments'].sudo().search(
                [('employee_id', '=', records.id), ('state', 'in', ['confirm', 'approve'])])])]

    # custom for employee and EmployeeID
    '''def name_get(self):
        result = []
        for record in self:
            name = record.name or ''
            # device_user_id = record.device_user_id
            id_card_no = record.id_card_no
            if id_card_no:
                name = "%s [%s]" % (name, id_card_no)
                # name = "%s [%s]" % (name, record.job_id.name)
            result.append((record.id, name))
        return result'''

    # custom for employee and DeviceID
    # def name_get(self):
    #     result = []
    #     for record in self:
    #         name = record.name
    #         device_user_id = record.device_user_id
    #         if device_user_id:
    #             name = "%s [%s]" % (name, device_user_id)
    #             # name = "%s [%s]" % (name, record.job_id.name)
    #         result.append((record.id, name))
    #     return result

    """@api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None, order=None):
        args = args or []
        domain = []
        if operator == 'ilike' and not (name or '').strip():
            domain += []
        else:
            domain += ['|', '|', ('name', operator, name), ('id_card_no', operator, name), ('work_email', operator, name)]

            # domain += ['|', '|', ('device_user_id', operator, name), ('name', operator, name),
            #            ('id_card_no', operator, name)]

        rec = self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid, order=order)
        return rec"""

    # def name_get(self):
    #     show_designation_flag = self._context.get('show_designation', False)
    #     if show_designation_flag == False:
    #         return super(InheritedHrEmployee, self).name_get()
    #     else:
    #         result = []
    #         for record in self:
    #             name = record.name
    #             if show_designation_flag:
    #                 if record.job_id:
    #                     name = "%s [%s]" % (name, record.job_id.name_get()[0][1])
    #                     # name = "%s [%s]" % (name, record.job_id.name)
    #             result.append((record.id, name))
    #         return result
    #         # <field name="coach_id" context="{'show_designation': 1}" options='{"always_reload": True}'/>

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

    @api.depends('initial_employment_date')
    def _compute_service_length(self):
        for record in self:
            if record.initial_employment_date:
                date_diff = relativedelta(
                    fields.Date.from_string(fields.Date.today()),
                    fields.Date.from_string(record.initial_employment_date))
                record.length_of_service = "{y} years, {m} months, {d} days".format(y=date_diff.years,
                                                                                    m=date_diff.months, d=date_diff.days
                                                                                    )
            else:
                record.length_of_service = 0

    @api.depends('date_of_confirmation')
    def _compute_remaining_confirmation_days(self):
        for record in self:
            if record.date_of_confirmation:
                date_remain = relativedelta(
                    fields.Date.from_string(record.date_of_confirmation),
                    fields.Date.from_string(fields.Date.today())
                )
                record.remaining_confirmation_day = "{y} years, {m} months, {d} days".format(y=date_remain.years,
                                                                                             m=date_remain.months,
                                                                                             d=date_remain.days)
            else:
                record.remaining_confirmation_day = 0

    @api.depends('forecasting_confirmation')
    def _compute_remaining_confirmation_days_forecast(self):
        for record in self:
            if record.forecasting_confirmation:
                date_remain = relativedelta(
                    fields.Date.from_string(record.forecasting_confirmation),
                    fields.Date.from_string(fields.Date.today())
                )
                record.remaining_confirmation_day_forecast = "{y} years, {m} months, {d} days".format(y=date_remain.years,
                                                                                             m=date_remain.months,
                                                                                             d=date_remain.days)
            else:
                record.remaining_confirmation_day_forecast = 0

    @api.onchange('job_grade')
    def _onchange_job_grade(self):
        """ Set Grade Type and Job Level onchange of job grade """
        for record in self:
            if record.job_grade:
                record.grade_type = record.job_grade.grade_type
                record.job_level = record.job_grade.job_level
            else:
                record.grade_type = ""
                record.job_level = ""

    @api.onchange('passport_id')
    def _remove_space_passport_id(self):
        for r in self:
            if r.passport_id:
                r.passport_id = str(r.passport_id).strip()

    @api.constrains('passport_id')
    def _check_unique_constraint_passport_id(self):
        msg = "Passport ID"
        envObj = self.env['hr.employee']

        conditionList1 = [('passport_id', '=ilike', self.passport_id)]
        validator.check_duplicate_value(self, envObj, conditionList1, msg)

    #     @api.onchange('master_id')
    #     def _remove_space_master_id(self):
    #         for r in self:
    #             if r.master_id:
    #                 r.master_id = str(r.master_id).strip()

    @api.onchange('company_id')
    def _onchange_company_id(self):
        """ Set parent_dept id onchange of department_id """
        if self.company_id:
            self.department_id = ""

    # @api.onchange('department_id')
    # def _onchange_department(self):
    #     """ Set parent_dept id onchange of department_id """
    #     if self.department_id:
    #         self.job_id = ""

    @api.onchange('job_id')
    def _onchange_job_id(self):
        """ Set job_grade on change of job_id """
        if self.job_id:
            self.job_title = self.job_id.name
            grade_line_object = self.env['hr.job.grade.line'].search([('name', '=', self.job_id.id)], limit=1)
            self.job_grade = grade_line_object.job_grade

    @api.onchange('user_work_location_id')
    def _onchange_location_id(self):
        # self.mobile_phone = self.user_work_location_id.mobile
        # self.work_phone = self.user_work_location_id.phone
        # self.work_email = self.user_work_location_id.email
        # self.work_location = self.user_work_location_id.name
        pass

    @api.onchange('address_id')
    def _onchange_address(self):
        # self.work_phone = self.address_id.phone
        # self.mobile_phone = self.address_id.mobile
        pass

    #     @api.onchange('identification_id')
    #     def _remove_space_identification_id(self):
    #         for field in self:
    #             if field.identification_id:
    #                 field.identification_id = str(field.identification_id).strip()

    @api.constrains('identification_id')
    def _check_unique_constraint_identification_id(self):
        msg = "Identification ID"
        envObj = self.env['hr.employee']

        conditionList1 = [('identification_id', '=ilike', self.identification_id),('active', '=', True),
                          ('active', '=', False)]
        validator.check_duplicate_value(self, envObj, conditionList1, msg)

    @api.onchange('id_card_no')
    def _remove_space_id_card_no(self):
        for r in self:
            if r.id_card_no:
                r.id_card_no = str(r.id_card_no).strip()

    @api.onchange('door_card_no')
    def _remove_space_door_card_no(self):
        for r in self:
            if r.door_card_no:
                r.door_card_no = str(r.door_card_no).strip()

    @api.onchange('nid')
    def _remove_space_nid(self):
        for r in self:
            if r.nid:
                r.nid = str(r.nid).strip()

    # def _sync_user(self, user):
    #     vals = dict(
    #         # image_1920=user.image_1920,
    #         # work_email=user.email,
    #         user_id=user.id,
    #     )
    #     if user.tz:
    #         vals['tz'] = user.tz
    #     return vals

    @api.constrains('nid')
    def _check_unique_constraint_nid(self):
        for r in self:
            if r.nid and not str(r.nid).isdigit():
                raise exceptions.ValidationError("Please Enter number only of the NID '%s'" %(r.nid))

        if self.nid:
            msg = "NID '%s'" % (self.nid)
            envObj = self.env['hr.employee']

            conditionList1 = [('nid', '=ilike', self.nid)]
            validator.check_duplicate_value(self, envObj, conditionList1, msg)

    @api.constrains('p_bank_account_no')
    def _check_unique_constraint(self):
        # raise exceptions.UserError(_(self.p_bank_account_no))
        msg = "Bank Account"
        envObj = self.env['hr.employee']

        conditionList1 = [('p_bank_account_no', '=', self.p_bank_account_no), ('p_bank_account_no', '!=', ''),
                          ('id', '!=', self.id)]
        validator.check_duplicate_value(self, envObj, conditionList1, msg)

    @api.constrains('email_personal')
    def _check_email_validation(self):
        if self.email_personal:
            msg = "Personal "
            validator._validate_email(self, self.email_personal, msg)

    @api.constrains('work_email')
    def _check_work_email_validation(self):
        if self.work_email:
            msg = "Official "
            validator._validate_email(self, self.work_email, msg)
    @api.constrains('e_contact_no')
    def _check_e_contact_no(self):
        if self.e_contact_no:
            msg = "Emergency Contact No "
            validator._valid_phone_number(self, self.e_contact_no, msg)

    @api.constrains('mobile_phone')
    def _check_mobile_phone(self):
        if self.mobile_phone:
            msg = "Cell No(Official) "
            validator._valid_phone_number(self, self.mobile_phone, msg)

    @api.constrains('start_date_of_contract', 'end_date_of_contract')
    def _check_date(self):
        """ Check if start_date_of_contract is greater than end_date_of_contract """
        f_date = fields.Datetime.from_string(self.start_date_of_contract)
        t_date = fields.Datetime.from_string(self.end_date_of_contract)
        if self.start_date_of_contract and self.end_date_of_contract and t_date <= f_date:
            raise exceptions.UserError(
                _("Start date of contract can't be greater than or equal to End date of contract Date"))

    @api.constrains('initial_employment_date', 'date_of_confirmation')
    def _check_employment_date(self):
        """ Check if initial_employment_date is greater than date_of_confirmation """
        f_date = fields.Datetime.from_string(self.initial_employment_date)
        t_date = fields.Datetime.from_string(self.date_of_confirmation)
        if self.initial_employment_date and self.date_of_confirmation and t_date < f_date:
            raise exceptions.UserError(
                _("Date of Joining can't be greater than Date of Confirmation"))

    @api.constrains('initial_employment_date', 'birthday')
    def _check_birthday(self):
        """ Check if birthday is greater than initial_employment_date """
        f_date = fields.Datetime.from_string(self.birthday)
        t_date = fields.Datetime.from_string(self.initial_employment_date)
        if self.initial_employment_date and self.birthday and t_date < f_date:
            raise exceptions.UserError(
                _("Birth Date can't be greater than Joining Date of '%s'" %(self.name)))

    def generate_random_barcode(self):
        for employee in self:
            # employee.barcode = '041'+"".join(choice(digits) for i in range(9))

            emp_joining_dtime = self.initial_employment_date
            if not emp_joining_dtime:
                raise exceptions.UserError(_("Date of Joining required!"))
            else:
                emp_id = ''
                try:
                    year = str(emp_joining_dtime.year)
                    month = str(emp_joining_dtime.month).zfill(2)
                    day = str(emp_joining_dtime.day).zfill(2)
                    hour = str((datetime.now() + timedelta(hours=6)).hour).zfill(2)
                    minute = str(datetime.now().minute).zfill(2)
                    # second = str(datetime.now().second).zfill(2)

                    emp_id = str(year) + str(month) + str(day) + str(hour) + str(minute)
                    if len(emp_id) != 12:
                        raise exceptions.UserError(_("Failed to generate 12 digits ID!"))
                    else:
                        sql = '''SELECT barcode FROM hr_employee where barcode = '%s' limit 1;''' % (emp_id)
                        self.env.cr.execute(sql)
                        result = self.env.cr.dictfetchall()
                        if result:
                            min_add_time = datetime.now() + timedelta(minutes=1)
                            hour = str(min_add_time.hour).zfill(2)
                            minute = str(min_add_time.minute).zfill(2)
                            emp_id = str(year) + str(month) + str(day) + str(hour) + str(minute)
                            if len(emp_id) != 12:
                                raise exceptions.UserError(_("Failed to generate 12 digits ID!"))
                            else:
                                sql = '''SELECT barcode FROM hr_employee where barcode = '%s' limit 1;''' % (emp_id)
                                self.env.cr.execute(sql)
                                result = self.env.cr.dictfetchall()
                                if result:
                                    raise exceptions.UserError(_("Try again!"))

                except:
                    raise exceptions.UserError(_("Failed to generate ID!"))

                employee.identification_id = emp_id
                employee.barcode = emp_id

            # employee.barcode = '041'+"".join(choice(digits) for i in range(9))

    #     @api.onchange('p_bank_account_no', 'bank_account_id')
    #     def get_bank_name(self):
    #         """ Get bank name onchange of s_bank_account_no from res.partner.bank """
    #         if self.p_bank_account_no.bank_id:
    #             # get personal bank name from bank account
    #             self.p_bank_name = self.p_bank_account_no.bank_id.name
    #         else:
    #             self.p_bank_name = ""
    #
    #         if self.bank_account_id.bank_id:
    #             # get salary bank name from bank account
    #             self.s_bank_name = self.bank_account_id.bank_id.name
    #         else:
    #             self.s_bank_name = ""

    # def generate_emp_attendance_id(self):
    #
    #     attendance_deivce_user_obj = self.env['attendance.device.user'].search([('employee_id', '=', self.id)], limit=1)

    def mail_reminder(self):
        """Sending expiry date notification for ID and Passport"""

        now = datetime.now() + timedelta(days=1)
        date_now = now.date()
        match = self.search([])
        for i in match:
            if i.id_expiry_date:
                exp_date = fields.Date.from_string(i.id_expiry_date) - timedelta(days=14)
                if date_now >= exp_date:
                    mail_content = "  Hello  " + i.name + ",<br>Your ID " + i.identification_id + "is going to expire on " + \
                                   str(i.id_expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('ID-%s Expired On %s') % (i.identification_id, i.id_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()
        match1 = self.search([])
        for i in match1:
            if i.passport_expiry_date:
                exp_date1 = fields.Date.from_string(i.passport_expiry_date) - timedelta(days=180)
                if date_now >= exp_date1:
                    mail_content = "  Hello  " + i.name + ",<br>Your Passport " + i.passport_id + "is going to expire on " + \
                                   str(i.passport_expiry_date) + ". Please renew it before expiry date"
                    main_content = {
                        'subject': _('Passport-%s Expired On %s') % (i.passport_id, i.passport_expiry_date),
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': i.work_email,
                    }
                    self.env['mail.mail'].sudo().create(main_content).send()

    personal_mobile = fields.Char(string='Mobile', related='address_home_id.mobile', store=True,
                                  help="Personal mobile number of the employee", groups="hr.group_hr_user")
    joining_date = fields.Date(string='Joining Date',
                               help="Employee joining date computed from the contract start date", groups="hr.group_hr_user")
    id_expiry_date = fields.Date(string='ID Expiry Date', help='Expiry date of Identification ID', groups="hr.group_hr_user")
    passport_expiry_date = fields.Date(string='Passport Expiry Date', help='Expiry date of Passport ID', groups="hr.group_hr_user")
    id_attachment_id = fields.Many2many('ir.attachment', 'id_attachment_rel', 'id_ref', 'attach_ref',
                                        string="Attachment(ID)", help='You can attach the copy of your Id', groups="hr.group_hr_user")
    passport_attachment_id = fields.Many2many('ir.attachment', 'passport_attachment_rel', 'passport_ref', 'attach_ref1',
                                              string="Attachment(Passport)",
                                              help='You can attach the copy of Passport', groups="hr.group_hr_user")
    fam_ids = fields.One2many('hr.employee.family', 'employee_id', string='Family', help='Family Information', groups="hr.group_hr_user")
    education_ids = fields.One2many('hr.employee.education.info', 'employee_id', string='Education',
                                    help='Education Information', groups="hr.group_hr_user")

    # @api.depends('contract_id')
    # def compute_joining(self):
    #     if self.contract_id:
    #         date = min(self.contract_id.mapped('date_start'))
    #         self.joining_date = date
    #     else:
    #         self.joining_date = False

    @api.onchange('spouse_complete_name', 'spouse_birthdate')
    def onchange_spouse(self):
        relation = self.env.ref('custom_hr_employee.employee_relationship')
        lines_info = []
        spouse_name = self.spouse_complete_name
        date = self.spouse_birthdate
        if spouse_name and date:
            lines_info.append((0, 0, {
                'member_name': spouse_name,
                'relation_id': relation.id,
                'birth_date': date,
            })
                              )
            self.fam_ids = [(6, 0, 0)] + lines_info

    @api.constrains('device_user_id')
    def _check_unique_device_user_id(self):
        if self.device_user_id:
            msg = 'Biometric Device ID "%s"' % self.device_user_id
            envobj = self.env['hr.employee']
            conditionlist = [('device_user_id', '=', self.device_user_id), ('active', '=', True)]
            validator.check_duplicate_value(self, envobj, conditionlist, msg)

    @api.constrains('id_card_no')
    def _check_unique_id_card_no(self):
        if self.id_card_no:
            msg = 'Employee ID "%s"' % self.id_card_no
            envobj = self.env['hr.employee']
            conditionlist = [('id_card_no', '=', self.id_card_no)]
            validator.check_duplicate_value(self, envobj, conditionlist, msg)

    def action_create_contract(self):
        contract_id = self.env['hr.contract'].create({
            'name': self.name,
            'employee_id': self.id,
            'date_start': self.initial_employment_date,
            'department_id': self.department_id.id,
            'job_id': self.job_id.id,
            'state': 'open',
            'company_id': self.env.ref('base.main_company').id,
            'wage': 0,
        })
        self.contract_created = True

        action_ctx = dict(self.env.context)
        view_id = self.env.ref('hr_contract.hr_contract_view_form').id
        action_vals = {
            'name': _('Contract'),
            'res_model': 'hr.contract',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_id': contract_id.id,
            'context': action_ctx,
            'type': 'ir.actions.act_window',
        }
        return action_vals


    def action_archive(self):
        for rec in self:
            super(InheritedHrEmployee, rec).action_archive()
            contrct_obj = rec.contract_id
            if contrct_obj:
                if contrct_obj.state=='open':
                    contrct_obj.state='cancel'
                    rec.contract_created=False

    # @api.model_create_multi
    # def create(self, vals_list):
    #     employees = super().create(vals_list)
    #
    #     if employees.user_id:
    #         employees.address_home_id = employees.user_id.partner_id.id
    #         employees.user_id.partner_id.is_employee = True
    #         employees.user_id.partner_id.employee_id = employees.id_card_no
    #         employees.user_id.partner_id.mobile = employees.contact_no
    #
    #     return employees

    # @api.model_create_multi
    # def create(self, vals_list):
    #     print("vals_list----------", vals_list)
    #
    #     for vals in vals_list:
    #         if 'name' not in vals:
    #             print("MISSING NAME:", vals)
    #
    #     return super().create(vals_list)

    """@api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.pop('resource_id', None)
            vals.pop('resource_calendar_id', None)

        employees = super().create(vals_list)

        for employee in employees.filtered('user_id'):
            partner = employee.user_id.partner_id
            employee.address_home_id = partner.id
            partner.write({
                'is_employee': True,
                'employee_id': employee.id_card_no,
                'mobile': employee.contact_no,
            })

        return employees"""

class HREmergencyContacts(models.Model):
    """ Employee Emergency Contacts """
    _name = 'hr.emergency.contacts'
    _description = 'Employee Emergency Contacts'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contact_no = fields.Char(string="Contact No")
    # contact_rel = fields.Char(string="Relation")
    contact_rel = fields.Many2one('hr.employee.contact.relation', string="Relation", ondelete='restrict')
    contact_name = fields.Char(string="Name")
    contact_address = fields.Text(string='Address')


class HrEmployeeDependent(models.Model):
    _name = 'hr.employee.dependent'
    _description = 'Employee Dependent'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete="cascade")

    dependent_name = fields.Char(string="Dependent Name")
    dependent_age = fields.Integer(string="Dependent Age")
    dependent_rel = fields.Char(string="Dependent Relationship")


class HrEmployeeSiblings(models.Model):
    _name = 'hr.employee.siblings'
    _description = 'Employee Siblings'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete="cascade")

    sibling_name = fields.Char(string="Name")
    sibling_age = fields.Integer(string="Age")
    sibling_occupation = fields.Char(string="Occupation")
    sibling_organization = fields.Char(string="Organization")
    sibling_contact = fields.Char(string="Contact")


class HrEmployeeActivities(models.Model):
    _name = 'hr.employee.activities'
    _description = 'Employee Activities'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete="cascade")

    activity_name = fields.Char(string="Nature of Activity", help="Name & Nature of Activity")
    award = fields.Char(string="Honors / Awards / Prize (if any)")


class HrEmployeeRelatives(models.Model):
    _name = 'hr.employee.relatives'
    _description = 'Employee Relatives'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete="cascade")

    name = fields.Char(string="Name")
    designation = fields.Char(string="Designation")
    department = fields.Char(string="Department & Workstation")
    organization = fields.Char(string="Organization")
    relation = fields.Char(string="Relationship")


class HrEmployeeRelativesOutside(models.Model):
    _name = 'hr.employee.relatives.outside'
    _description = 'Employee Relatives Outside'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Applicant', required=True)

    name = fields.Char(string="Name")
    designation_department = fields.Char(string="Designation & Department")
    organization = fields.Char(string="Organization")
    org_contact = fields.Text(string="Contact address & Phone number")
    relation = fields.Char(string="Relationship")


class HrEmployeeLettersHistory(models.Model):
    """ Employee Emergency Contacts """
    _name = 'hr.employee.letters.history'
    _description = 'Employee Letters History'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    letter_name = fields.Char(string="Letter Name")
    # contact_rel = fields.Char(string="Relation")
    # letters = fields.Many2one('hr.employee.letters', string="Letters Reference")


class EmployeeRelationInfo(models.Model):
    """Table for keep employee family information"""

    _name = 'hr.employee.relation'
    _description = 'Employee Relation'

    name = fields.Char(string="Relationship", help="Relationship with thw employee")
