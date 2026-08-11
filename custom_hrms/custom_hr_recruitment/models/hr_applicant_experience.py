from odoo import fields, models, api
from dateutil.relativedelta import relativedelta
from datetime import datetime


class HrApplicantExperience(models.Model):
    _name = 'hr.applicant.experience'
    _description = 'Applicant Experience'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant', required=True)
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    institute_id = fields.Char(string='Company', help="Name of Company")
    location = fields.Text(string="Address", help="Address of the Company")
    name = fields.Char(string='Designation')
    salary_starting = fields.Float(string='Starting Salary')
    salary_present = fields.Float(string='Present Salary')
    salary_leaving = fields.Float(string='Leaving Salary')
    supervisor_details = fields.Text(string='Immediate Supervisor',
                                     help='Name & Designation of Immediate Supervisor')
    achievements = fields.Char(string="Achievements")
    job_leave_reason = fields.Text(string="Reason of leaving", help="Reason of leaving the job")
    serv_leng = fields.Char(string='Service Length', readonly=True, compute='_compute_serv_leng')
    attachment_ids = fields.Many2many('ir.attachment', 'hr_applicant_experience_ir_attachments_rel', 'attachment_id',
                                      string="Attachments", help="Attach Multiple file")
    expire = fields.Boolean('Expire', help="Expire", default=False)

    # @api.multi
    @api.onchange('start_date', 'end_date')
    def _compute_serv_leng(self):
        for record in self:
            if record.start_date and record.end_date:
                s_leng = relativedelta(
                    fields.Date.from_string(record.end_date),
                    fields.Date.from_string(record.start_date))
            # record.write({'serv_leng': "{y} years, {m} months, {d} days".format(y=s_leng.years, m=s_leng.months,
            #                                                                     d=s_leng.days)})
            else:
                # record.write({'serv_leng': ''})
                dateTimeObj = datetime.now()
                current_date = str(dateTimeObj.year) + '-' + str(dateTimeObj.month) + '-' + str(dateTimeObj.day)
                s_leng = relativedelta(
                    fields.Date.from_string(current_date),
                    fields.Date.from_string(record.start_date))
            # record.serv_leng = 0
            record.serv_leng = "{y} years, {m} months, {d} days".format(y=s_leng.years, m=s_leng.months, d=s_leng.days)
