from odoo import api, fields, models, exceptions, _
from dateutil.relativedelta import relativedelta


class InheritedHrResumeLine(models.Model):
    """ Add some fields in hr.resume.line model as per BEL requirements"""
    _inherit = 'hr.resume.line'

    institute_id = fields.Char(string='Institute',
                               help="School, University, Company, Certification Authority, etc.")
    result = fields.Char(string="Result")
    duration = fields.Char(string='Duration', readonly=True, compute='_compute_duration')
    passing_year = fields.Char(string="Passing year")
    exam_year = fields.Char(string="Exam year")
    subject_group = fields.Char(string="Subject/Group")
    scholarship = fields.Char(string="Scholarship or Distinction")

    # technical
    country_name = fields.Char(string="Country Name")
    qualification_gained = fields.Char(string="Qualification Gained/Achievement")

    # Job Experience
    designation = fields.Char(string="Designation And Job Summary")
    salary_starting = fields.Float(string='Starting Salary')
    salary_present = fields.Float(string='Present Salary')
    salary_leaving = fields.Float(string='Leaving Salary')
    supervisor_details = fields.Text(string='Immediate Supervisor',
                                     help='Name & Designation of Immediate Supervisor')
    achievements = fields.Char(string="Achievements")
    job_leave_reason = fields.Text(string="Reason of leaving", help="Reason of leaving the job")

    line_type_name = fields.Char(related='line_type_id.name', string='Type name')

    @api.constrains('date_start', 'date_end')
    def _check_date(self):
        """ Check if start Date is greater than end date """
        # from_date = fields.Datetime.from_string(self.date_start)
        # to_date = fields.Datetime.from_string(self.date_end)
        # if self.date_start and self.date_end and to_date < from_date:
        #     raise exceptions.UserError(
        #         _("Start Date can't be greater than or equal to End Date"))
        for record in self:
            from_date = fields.Datetime.from_string(record.date_start)
            to_date = fields.Datetime.from_string(record.date_end)
            if record.date_start and record.date_end and to_date < from_date:
                raise exceptions.UserError(
                    _("Start Date can't be greater than or equal to End Date"))

    @api.onchange('date_start', 'date_end')
    def _compute_duration(self):
        for record in self:
            if record.date_start:
                if record.date_end:
                    to_date = fields.Date.from_string(record.date_end)
                else:
                    to_date = fields.Date.from_string(fields.Date.today())
                calc_duration = relativedelta(
                    to_date,
                    fields.Date.from_string(record.date_start))
                # record.write({'serv_leng': "{y} years, {m} months, {d} days".format(y=calc_duration.years,
                #                 m=calc_duration.months, d=calc_duration.days)})
                record.duration = "{y} years, {m} months, {d} days".format(y=calc_duration.years,
                                                                           m=calc_duration.months, d=calc_duration.days)
            else:
                # record.write({'duration': ''})
                record.duration = 0


class SkillLevelInherit(models.Model):
    _inherit = 'hr.skill.level'

    level_progress_range = fields.Char(string="Progress Range")


class EmployeeSkillInherit(models.Model):
    _inherit = 'hr.employee.skill'

    level_progress_range = fields.Char(related='skill_level_id.level_progress_range')
