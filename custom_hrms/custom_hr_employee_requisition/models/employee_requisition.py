# coding=utf-8
from odoo import fields, models, api, exceptions, _
from odoo.addons.helper import validator


class EmployeeRequisition(models.Model):
    """ Employee requisition form model """

    _name = 'hr.employee.requisition'
    _rec_name = "rec_no"
    _description = "Employee Requisition"


    @api.model
    def _get_department(self):
        """ @:return department """
        current_user_id = self.env.user
        employee_id = self._get_employee_id(current_user_id)
        if employee_id:
            dept_ids = self.env['hr.department'].search([('parent_id', '=', employee_id.department_id.id)])
            return ['|', ('id', '=', employee_id.department_id.id), ('id', '=', dept_ids.ids)]
        elif current_user_id.id == 1 or self.env.user.has_group('hr.group_hr_manager'):
            return
        else:
            return [('id', '=', [])]

    state = fields.Selection([
        ('draft', "Draft"),
        ('requested', "Requested"),
        ('authorized', "HRBP"), #Authorized
        ('recommended', "Recommended"),
        ('approved', "Approved"),
        ('cancel', "Cancelled")
    ], default='draft', string="State")

    rec_no = fields.Char(string="Form No.", required=True, help="Requisition Form No.")
    company_id = fields.Many2one('res.company', string='Request Company', index=True,
                                 default=lambda self: self.env.company)
    rec_dept = fields.Many2one('hr.department', string="Requisition Department", required=True, ondelete="cascade",
                               help="In which department this requisition will be")  # domain=lambda self: self._get_department(),
    rec_position = fields.Many2one('hr.job', string="Requested Position", required=True, ondelete="cascade",
                                   help="In which position this requisition will be")
    position_type = fields.Selection([
        ('new', 'New'),
        ('replacement', 'Replacement')
    ], default="")
    contract_type_id = fields.Many2one('hr.contract.type', string='Employment Type', required=True)

    gender = fields.Selection([
        ('male', "Male"),
        ('female', "Female"),
        ('anyone', 'Any')
    ], default="", required=True, string="Gender")
    date = fields.Date(string="Date")
    approved_man = fields.Integer(string="Approved Manpower")
    actual_man = fields.Integer(string="Actual Manpower")
    required_man = fields.Integer(string="Required Manpower", default=0)
    request_man = fields.Integer(string="Request Manpower", default=0)
    est_salary = fields.Float(string="Estimated Salary", default=0)
    act_salary = fields.Float(string="Actual Salary")
    expertise = fields.Selection([
        ('fresh', 'Fresh'),
        ('experienced', 'Experienced')
    ], default="", required=True, string="Expertise")
    exp_year = fields.Integer(string="Experience(In Year)")
    edu_qual = fields.Text(string="Educational Qualification", help="Put your educational degree separated by comma. "
                                                                    "like MA, BA, HSC, SSC")
    requirements = fields.Text(string="Provide some details regarding the type of employee required, as well as the "
                                      "qualifications and work experience, and any other factors which need to be "
                                      "considered", required=True)
    is_parttime = fields.Boolean(string="Can the vacancy be filled by a temporary/part-time employee?")
    is_desc_exist = fields.Boolean(string="Does a job description exist for this position?")
    is_reduce_mp = fields.Boolean(string="Reduce manpower requirements in the department?")
    is_fucn_effective = fields.Boolean(string="Make the functioning of the department more effective?")
    is_cost_reduce = fields.Boolean(string="Reduce the Payroll cost to company?")
    is_internal = fields.Boolean(string="Will the position be advertised internally first?")
    prospects = fields.Text(string="What are the prospects of filling this position with a qualified candidate?")
    investigations = fields.Text(string="What investigations have been conducted to determine the availability of "
                                        "quality candidates?")
    commencement_date = fields.Date(string="Proposed date of commencement")
    proposed_salary = fields.Float(string="Proposed Salary per annum")
    have_mobile_allowance = fields.Boolean(string="Company Mobile Allowance")
    have_travel_allowance = fields.Boolean(string="Company Travel Allowance")
    need_computer = fields.Boolean(string="Desktop/Laptop")
    need_lunch = fields.Boolean(string="Company Provided Lunch")
    other_benefits = fields.Text(string="Other benefits (please specify)")
    probation_period_id = fields.Many2one('hr.probation.period', string="Probation Period (Months)")
    internal_transfer = fields.Boolean(string="Internal transfer/ promotion from within the Company?")
    required_training = fields.Boolean(string="Training/ Induction Details (Required)")
    training_duration_id = fields.Many2one('hr.probation.period', string="Duration of Training (Weeks/Months)")
    training_details = fields.Text(string="Specify the required Training details")
    requested_by = fields.Many2one('hr.employee', string='Requested by')
    requested_designation = fields.Many2one('hr.job', string="Designation")
    authorized_by = fields.Many2one('hr.employee', string='Authorized by')
    authorized_designation = fields.Many2one('hr.job', string="Designation")
    recommended_by = fields.Many2one('hr.employee', string='Recommended by')
    recommended_designation = fields.Many2one('hr.job', string="Designation")
    approved_by = fields.Many2one('hr.employee', string='Approved by')
    approved_designation = fields.Many2one('hr.job', string="Designation")
    cancelled_by = fields.Many2one('hr.employee', string='Cancelled by')
    cancelled_designation = fields.Many2one('hr.job', string="Designation")
    comments = fields.Text(string="Comments")

    @api.constrains('comments')
    def _check_comments_length(self):
        limit = 300
        record = self.comments
        field_name = "comments"
        validator._check_length(self, record, limit, field_name)

    @api.onchange('approved_man', 'actual_man')
    def _onchange_required_man(self):
        if (self.approved_man>=0 and self.actual_man>=0):
            required_man = self.approved_man-self.actual_man
            if required_man > 0:
                self.required_man = required_man
            else:
                self.required_man = 0

    @api.onchange('required_man')
    def _onchange_request_man(self):
        if (self.required_man > 0):
            self.request_man = self.required_man

    @api.onchange('rec_position')
    def _onchange_job_position(self):
        if self.rec_position:
            self.approved_man = self.rec_position.approved_man
            self.actual_man = self.rec_position.no_of_employee

    # @api.model
    # def create(self, vals):
    #     """ make form no. uppercase """
    #     for val in vals:
    #         rec_no = val.get('rec_no', False)
    #         if rec_no:
    #             val['rec_no'] = str(rec_no).strip().upper()
    #     return super(EmployeeRequisition, self).create(vals)

    # @api.multi
    # def write(self, vals):
    #     """ make form no. uppercase """
    #     rec_no = vals.get('rec_no', False)
    #     if rec_no:
    #         vals['rec_no'] = str(rec_no).strip().upper()
    #     return super(EmployeeRequisition, self).write(vals)

    # @api.multi
    @api.constrains('rec_no')
    def _check_unique_constraint_name(self):
        msg = "Form No. {0} ".format(self.rec_no)
        envObj = self.env['hr.employee.requisition']

        conditionList1 = [('rec_no', '=ilike', self.rec_no)]
        validator.check_duplicate_value(self, envObj, conditionList1, msg)

    @api.onchange('rec_dept')
    def _onchange_rec_dept(self):
        """ Set position blank on change of rec_dept """
        if self.rec_dept or not self.rec_dept:
            self.rec_position = ""

    @api.onchange('expertise')
    def _onchange_expertise(self):
        """ Set exp_year=0 if expertise=fresh """
        if self.expertise == 'fresh':
            self.exp_year = 0

    @api.model
    def _get_employee_id(self, user_id):
        """
            @:param user_id
            :return Employee Id
        """
        emp_id = self.env['hr.employee'].search([('user_id', '=', user_id.id)], limit=1)
        return emp_id

    # @api.multi
    def action_draft(self):
        """ Change state as draft of a record """
        self.state = 'draft'

    # @api.multi
    def action_requested(self):
        """ Change state as requested of a record """
        current_user_id = self.env.user
        employee_id = self._get_employee_id(current_user_id)
        if employee_id:
            self.write({'requested_by': employee_id.id})
            self.write({'requested_designation': employee_id.job_id.id})
        self.write({'state': 'requested'})

    # @api.multi
    def requested_draft(self):
        """ Send to draft state from requested state and set null value to requested_by and requested_designation"""
        self.write({'state': 'draft'})
        self.write({'requested_by': None})
        self.write({'requested_designation': None})

    # @api.multi
    def action_authorized(self):
        """ Change state as authorized of a record """
        current_user_id = self.env.user
        employee_id = self._get_employee_id(current_user_id)
        if employee_id:
            self.authorized_by = employee_id.id
            self.authorized_designation = employee_id.job_id.id
        self.state = 'authorized'

    # @api.multi
    def authorized_requested(self):
        """ Send to requested state from authorized state and set null value to authorized_by and
        authorized_designation """
        self.write({'state': 'requested'})
        self.write({'authorized_by': None})
        self.write({'authorized_designation': None})

    # @api.multi
    def action_recommended(self):
        """ Change state as recommended of a record """
        current_user_id = self.env.user
        employee_id = self._get_employee_id(current_user_id)
        if employee_id:
            self.recommended_by = employee_id.id
            self.recommended_designation = employee_id.job_id.id
        self.state = 'recommended'

    # @api.multi
    def recommended_authorized(self):
        """ Send to authorized state from recommended state and set null value to recommended_by and
                recommended_designation """
        self.write({'state': 'authorized'})
        self.write({'recommended_by': None})
        self.write({'recommended_designation': None})

    # @api.multi
    def action_approved(self):
        """ Change state as approved of a record """
        current_user_id = self.env.user
        employee_id = self._get_employee_id(current_user_id)
        if employee_id:
            self.approved_by = employee_id.id
            self.approved_designation = employee_id.job_id.id

        #-------------- recruitment create
        recruitment_auto_update = self.env['custom.common.settings'].sudo().search(
            [('key', '=', 'recruitment_auto_update'), ('value', '=', True)], limit=1)
        if recruitment_auto_update:
            #try:
            self.rec_position.no_of_recruitment = self.request_man or 1
            self.rec_position.website_published = True
            self.contract_type_id = self.contract_type_id.id
            # except:
            #     pass

        #-----------
        self.state = 'approved'

    # @api.multi
    def action_cancel(self):
        """ Change state as cancel of a record """
        current_user_id = self.env.user
        employee_id = self._get_employee_id(current_user_id)
        if employee_id:
            self.cancelled_by = employee_id.id
            self.cancelled_designation = employee_id.job_id.id
        self.state = 'cancel'

    # @api.multi
    def unlink(self):
        """ Override unlink method.  """
        for record in self:
            if record.state != 'draft':
                raise exceptions.UserError(_("Only 'Draft' record can be deleted"))
        return super(EmployeeRequisition, self).unlink()

    def action_print(self):
        """ Print Requisition form """
        data = {}
        requisition_sql = """
            SELECT
                emr.id AS id,
                emr.rec_no AS requisition_no,
                hd.name->>'en_US' AS department, 
                hj.name->>'en_US' AS designation,
                emr.position_type,
                emr.contract_type_id,
                emr.gender,
                emr.date,
                emr.approved_man,
                emr.actual_man,
                emr.request_man,
                emr.est_salary,
                emr.act_salary,
                emr.expertise,
                emr.exp_year,
                emr.edu_qual,
                emr.requirements,
                emr.is_parttime,
                emr.is_desc_exist,
                emr.is_reduce_mp,
                emr.is_fucn_effective,
                emr.is_cost_reduce,
                emr.is_internal,
                emr.prospects,
                emr.investigations,
                emr.commencement_date,
                emr.have_mobile_allowance,
                emr.need_computer,
                emr.proposed_salary,
                emr.have_travel_allowance,
                emr.need_lunch,
                emr.other_benefits,
                hpp.name AS probation_name,
                emr.internal_transfer,
                emr.required_training,
                hpp1.name AS training_name,
                emr.training_details,
                --em.name_related AS requested_by,
                hj1.name AS requested_designation,
                --em2.name_related AS authorized_by,
                hj2.name AS authorized_designation,
                --em3.name_related AS recommended_by,
                hj3.name AS recommended_designation,
                --em4.name_related AS approved_by,
                hj4.name AS approved_designation
            FROM 
                hr_employee_requisition AS emr
                LEFT JOIN hr_department As hd ON hd.id = emr.rec_dept
                LEFT JOIN hr_job AS hj ON hj.id = emr.rec_position
                LEFT JOIN hr_probation_period AS hpp ON hpp.id = emr.probation_period_id
                LEFT JOIN hr_probation_period AS hpp1 ON hpp1.id = emr.training_duration_id
                LEFT JOIN hr_employee AS em ON em.id = emr.requested_by
                LEFT JOIN hr_job AS hj1 ON hj1.id = emr.requested_designation
                LEFT JOIN hr_employee AS em2 ON em2.id = emr.authorized_by
                LEFT JOIN hr_job AS hj2 ON hj2.id = emr.authorized_designation
                LEFT JOIN hr_employee AS em3 ON em3.id = emr.recommended_by
                LEFT JOIN hr_job AS hj3 ON hj3.id = emr.recommended_designation
                LEFT JOIN hr_employee AS em4 ON em4.id = emr.approved_by
                LEFT JOIN hr_job AS hj4 ON hj4.id = emr.approved_designation
            WHERE emr.id = %s
            LIMIT 1
        """ % self.id
        self.env.cr.execute(requisition_sql)
        result = self.env.cr.dictfetchall()
        data['ids'] = result

        data['other'] = {
            'form_no': self.rec_no,
            'requisition_dept': self.rec_dept.name,
            'requisition_company': self.company_id.name
        }
        # return self.env['report'].get_action(self, 'custom_hr_employee_requisition.hr_emp_rec_print', data=data)
        # return self.env.ref('custom_hr_employee_requisition.hr_emp_rec_print_report').report_action(self, data=data)
        return self.env.ref('custom_hr_employee_requisition.hr_emp_rec_print_report').report_action(self)

    def action_print_requisition_report(self):
        return self.env.ref('custom_hr_employee_requisition.action_report_employee_requisition').report_action(self)
